import random
import math
from typing import Optional
from backend.models import JBIItem, TrailerConfig, PlacedItem, Trip


def calculate_optimizer(initial_items: list[JBIItem], trailer: TrailerConfig) -> list[Trip]:
    """Точный порт calculateOptimizer из optimizer.ts"""
    # 1. Разворачиваем список: каждый элемент count раз
    flat_items: list[JBIItem] = []
    for group in initial_items:
        for _ in range(group.count):
            flat_items.append(JBIItem(
                id=group.id, code=group.code, name=group.name,
                width=group.width, length=group.length, height=group.height,
                weight=group.weight, count=1,
            ))

    if not flat_items:
        return []

    # 2. Начальная сортировка: тяжёлые и длинные — первыми
    current_order = flat_items[:]
    current_order.sort(key=lambda a: a.weight * a.length, reverse=True)

    best_trips = pack_items(current_order, trailer)
    best_score = calculate_score(best_trips, trailer)

    # 3. Имитация отжига (Simulated Annealing)
    temp = 1000.0
    cooling_rate = 0.94
    iterations = 600

    for _ in range(iterations):
        next_order = current_order[:]
        idx_a = random.randint(0, len(next_order) - 1)
        idx_b = random.randint(0, len(next_order) - 1)
        next_order[idx_a], next_order[idx_b] = next_order[idx_b], next_order[idx_a]

        next_trips = pack_items(next_order, trailer)
        next_score = calculate_score(next_trips, trailer)

        delta = best_score - next_score
        if next_score < best_score or random.random() < math.exp(delta / max(temp, 1e-10)):
            current_order = next_order
            if next_score < best_score:
                best_score = next_score
                best_trips = next_trips

        temp *= cooling_rate

    return best_trips


def pack_items(order: list[JBIItem], trailer: TrailerConfig) -> list[Trip]:
    trips: list[Trip] = []
    remaining = [JBIItem(**item.__dict__) for item in order]

    while remaining:
        current_trip_items: list[PlacedItem] = []
        current_weight = 0.0
        still_remaining: list[JBIItem] = []

        # Приоритет: сначала тяжёлые фундаментные элементы
        foundation = [it for it in remaining if it.code in ("ПТ", "ПШЛ-1")]
        others = [it for it in remaining if it.code not in ("ПТ", "ПШЛ-1")]

        for item in foundation + others:
            if current_weight + item.weight <= trailer.max_weight:
                # Определяем возможные повороты (ориентации)
                if item.code == "ПШЛ-1":
                    rotations = [{"l": 2830.0, "w": 2030.0}]
                else:
                    rotations = [
                        {"l": item.length, "w": item.width},
                        {"l": item.width, "w": item.length},
                    ]

                best_pos: Optional[PlacedItem] = None
                min_cg_dist = float("inf")

                for rot in rotations:
                    if rot["w"] > trailer.total_width:
                        continue
                    rotated = JBIItem(
                        id=item.id, code=item.code, name=item.name,
                        width=rot["w"], length=rot["l"],
                        height=item.height, weight=item.weight, count=1,
                    )
                    pos = find_physical_spot(current_trip_items, rotated, trailer)
                    if pos:
                        dist = abs((pos.x + pos.length / 2) - trailer.ideal_cg_from_rear)
                        if dist < min_cg_dist:
                            min_cg_dist = dist
                            best_pos = pos

                if best_pos:
                    current_trip_items.append(best_pos)
                    current_weight += item.weight
                else:
                    still_remaining.append(item)
            else:
                still_remaining.append(item)

        if current_trip_items:
            trips.append(create_trip(len(trips) + 1, current_trip_items, trailer))
        else:
            # Избегаем бесконечного цикла
            if remaining:
                still_remaining.append(remaining.pop(0))

        remaining = still_remaining
        if len(trips) > 25:
            break

    return trips


def find_physical_spot(
    placed: list[PlacedItem], item: JBIItem, trailer: TrailerConfig
) -> Optional[PlacedItem]:
    x_step = 100
    total_len = trailer.lower_length + trailer.upper_length

    y_center = (trailer.total_width - item.width) / 2
    # ПП/ПБ (1200мм) — слева, справа или по центру; широкие — только центр
    y_options = [0.0, 1200.0, y_center] if item.width <= 1200 else [y_center]

    best_spot: Optional[PlacedItem] = None
    min_score = float("inf")

    for pass_num in range(2):
        x = 0.0
        while x <= total_len - item.length:
            is_upper = x >= trailer.lower_length
            is_spanning = x < trailer.lower_length and (x + item.length) > trailer.lower_length
            if is_spanning:
                x += x_step
                continue

            h_limit = trailer.upper_max_height if is_upper else trailer.lower_max_height
            if item.code == "ПШЛ-1" and not is_upper:
                h_limit = 3000.0

            for y in y_options:
                if y < 0 or y + item.width > trailer.total_width:
                    continue

                z = 0.0
                colliding = [
                    p for p in placed
                    if p.x < x + item.length and p.x + p.length > x
                    and p.y < y + item.width and p.y + p.width > y
                ]

                # Нельзя ставить НА шахту лифта
                if any(p.item.code == "ПШЛ-1" for p in colliding):
                    continue

                # Нельзя ставить под лестницу (кроме самих лестниц)
                if any(p.item.code == "ЛМ" for p in colliding) and item.code != "ЛМ":
                    continue

                for p in colliding:
                    z = max(z, p.z + p.height)

                # Pass 0: только на пол (z=0)
                if pass_num == 0 and z > 0:
                    continue

                if z + item.height <= h_limit:
                    is_heavy = item.code in ("ПТ", "ПШЛ-1")
                    if is_heavy and z > 0:
                        if not all(p.item.code == "ПТ" for p in colliding):
                            continue

                    # Оценка позиции
                    item_cg_x = x + item.length / 2
                    cg_dist = abs(item_cg_x - trailer.ideal_cg_from_rear)
                    side_penalty = abs(y + item.width / 2 - trailer.total_width / 2) * 0.1
                    height_penalty = z * 5  # штраф за ярусы

                    # Бонус за укладку вплотную к соседу
                    is_touching = any(
                        p.z == z and p.y == y and
                        (abs(p.x + p.length - x) < 5 or abs(x + item.length - p.x) < 5)
                        for p in placed
                    )
                    sequence_bonus = -800.0 if (is_touching and pass_num == 0) else 0.0

                    score = cg_dist + side_penalty + height_penalty + sequence_bonus
                    if score < min_score:
                        min_score = score
                        best_spot = PlacedItem(
                            item=item, x=x, y=y, z=z,
                            width=item.width, length=item.length, height=item.height,
                        )

            x += x_step

        if best_spot:
            break

    return best_spot


def calculate_score(trips: list[Trip], trailer: TrailerConfig) -> float:
    trip_penalty = len(trips) * 10_000_000
    weight_penalty = sum(trailer.max_weight - t.total_weight for t in trips)
    cg_penalty = sum(abs(t.cg_mismatch) for t in trips) * 100
    return trip_penalty + weight_penalty + cg_penalty


def create_trip(id: int, items: list[PlacedItem], trailer: TrailerConfig) -> Trip:
    total_weight = sum(p.item.weight for p in items)
    total_moment = sum(p.item.weight * (p.x + p.length / 2) for p in items)
    cg_x = total_moment / total_weight if total_weight > 0 else 0.0
    cg_mismatch = cg_x - trailer.ideal_cg_from_rear
    return Trip(id=id, items=items, total_weight=total_weight, cg_x_from_rear=cg_x, cg_mismatch=cg_mismatch)
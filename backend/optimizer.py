import math
from typing import List, Optional, Tuple
from models import JBIItem, TrailerConfig, PlacedItem, Trip, enrich_item_with_rules


def get_item_footprint_width(item: JBIItem) -> float:
    if item.rules.can_rotate_yaw:
        return min(item.width, item.length)
    return item.width

def get_intersection_area(x1: float, y1: float, w1: float, l1: float, 
                          x2: float, y2: float, w2: float, l2: float) -> float:
    dx = max(0.0, min(x1 + l1, x2 + l2) - max(x1, x2))
    dy = max(0.0, min(y1 + w1, y2 + w2) - max(y1, y2))
    return dx * dy

def get_floor_z(x: float, item_length: float, trailer: TrailerConfig) -> float:
    if x + item_length <= trailer.lower_length:
        return 0.0
    if x >= trailer.lower_length:
        return trailer.height_diff
    return -1.0

def calculate_trailer_cg(placed_items: List[PlacedItem]) -> float:
    total_weight = sum(p.item.weight for p in placed_items)
    if total_weight == 0:
        return 0.0
    total_moment = sum(p.item.weight * (p.x + p.length / 2) for p in placed_items)
    return total_moment / total_weight


def calculate_cg_mismatch(placed_items: List[PlacedItem], trailer: TrailerConfig) -> float:
    return calculate_trailer_cg(placed_items) - trailer.ideal_cg_from_rear


def estimate_row_fill_bonus(item: JBIItem, future_items: List[JBIItem], trailer: TrailerConfig) -> float:
    if not future_items:
        return 0.0

    available_width = trailer.total_width - get_item_footprint_width(item)
    if available_width <= 0:
        return 0.0

    widths = [get_item_footprint_width(future_item) for future_item in future_items]

    best_fill = 0.0
    count = len(widths)
    for mask in range(1, 1 << count):
        total_width = 0.0
        for index in range(count):
            if mask & (1 << index):
                total_width += widths[index]
        if total_width <= available_width:
            best_fill = max(best_fill, total_width)

    if best_fill <= 0:
        return 0.0

    return (best_fill / available_width) * 120.0


def generate_order_variants(items: List[JBIItem]) -> List[List[JBIItem]]:
    variants: List[List[JBIItem]] = []
    count = len(items)

    def add_variant(candidate: List[JBIItem]) -> None:
        if candidate != items and candidate not in variants:
            variants.append(candidate)

    for left_index in range(count):
        for right_index in range(left_index + 1, count):
            swapped = items[:]
            swapped[left_index], swapped[right_index] = swapped[right_index], swapped[left_index]
            add_variant(swapped)

    for source_index in range(count):
        for target_index in range(count):
            if source_index == target_index:
                continue
            moved = items[:]
            element = moved.pop(source_index)
            moved.insert(target_index, element)
            add_variant(moved)

    return variants


def improve_trip_balance(placed_items: List[PlacedItem], trailer: TrailerConfig, start_seq: int) -> List[PlacedItem]:
    if len(placed_items) < 2:
        return placed_items

    best_items = placed_items
    best_mismatch = abs(calculate_cg_mismatch(placed_items, trailer))

    current_items = sorted(placed_items, key=lambda p: p.sequence_number)

    for move_index, moved_item in enumerate(current_items):
        remaining_items = current_items[:move_index] + current_items[move_index + 1:]
        spot_result = find_best_spot(moved_item.item, remaining_items, trailer, [])
        if not spot_result:
            continue

        spot, _ = spot_result
        x, y, z, l, w = spot
        moved_candidate = PlacedItem(
            item=moved_item.item,
            sequence_number=moved_item.sequence_number,
            x=x,
            y=y,
            z=z,
            width=w,
            length=l,
            height=moved_item.height,
        )
        candidate_items = remaining_items + [moved_candidate]
        candidate_mismatch = abs(calculate_cg_mismatch(candidate_items, trailer))
        if candidate_mismatch + 1e-6 < best_mismatch:
            best_mismatch = candidate_mismatch
            best_items = candidate_items

    source_items = [placed.item for placed in sorted(best_items, key=lambda p: p.sequence_number)]

    for order in generate_order_variants(source_items):
        candidate_items, unpacked, _ = pack_one_trip(order, trailer, start_seq)
        if unpacked:
            continue

        candidate_mismatch = abs(calculate_cg_mismatch(candidate_items, trailer))
        if candidate_mismatch + 1e-6 < best_mismatch:
            best_mismatch = candidate_mismatch
            best_items = candidate_items

    return best_items

def get_lowest_z(x: float, y: float, l: float, w: float, 
                 placed: List[PlacedItem], trailer: TrailerConfig) -> float:
    floor_z = get_floor_z(x, l, trailer)
    if floor_z == -1.0:
        return -1.0
        
    z_max = floor_z
    for p in placed:
        if get_intersection_area(x, y, w, l, p.x, p.y, p.width, p.length) > 0.1:
            z_max = max(z_max, p.z + p.height)
    return z_max

def check_support_and_rules(item: JBIItem, x: float, y: float, z: float, 
                            l: float, w: float, placed: List[PlacedItem], 
                            trailer: TrailerConfig) -> bool:
    floor_z = get_floor_z(x, l, trailer)
    
    # 1. Если прямо на полу - проблем нет (кроме ЛМ, для нее пол разрешен)
    if math.isclose(z, floor_z, abs_tol=0.1):
        return True

    # 2. Если деталь требует ТОЛЬКО пола
    if item.rules.must_be_on_floor:
        return False

    supported_area = 0.0
    for p in placed:
        if math.isclose(p.z + p.height, z, abs_tol=0.1):
            overlap_area = get_intersection_area(x, y, w, l, p.x, p.y, p.width, p.length)
            if overlap_area > 0.1:
                # На нижнюю деталь вообще ничего нельзя ставить
                if p.item.rules.requires_empty_top:
                    return False
                
                # На нижнюю деталь можно ставить ТОЛЬКО такую же (ЛМ -> ЛМ)
                if getattr(p.item.rules, "allow_only_same_on_top", False) and p.item.code != item.code:
                    return False
                    
                # Верхнюю деталь можно ставить ТОЛЬКО на такую же (ЛМ на ЛМ)
                if getattr(item.rules, "stack_only_on_same", False) and p.item.code != item.code:
                    return False
                
                supported_area += overlap_area

    # 75% опоры
    required_area = (l * w) * item.rules.min_support_pct
    return supported_area >= required_area

def find_best_spot(item: JBIItem, placed: List[PlacedItem], 
                   trailer: TrailerConfig, future_items: Optional[List[JBIItem]] = None) -> Optional[Tuple[Tuple[float, float, float, float, float], float]]:
    best_spot = None
    best_score = float("inf")
    future_items = future_items or []
    
    # 1. Генерируем точки X
    x_candidates = {0.0, trailer.lower_length, max(0.0, trailer.lower_length - item.length)}
    for p in placed:
        x_candidates.add(p.x + p.length)
        x_candidates.add(max(0.0, p.x - item.length))
    x_candidates = sorted(list(set(round(x, 1) for x in x_candidates if x >= 0)))

    # 2. Перебор ориентаций
    orientations = [(item.length, item.width)]
    if item.rules.can_rotate_yaw:
        orientations.append((item.width, item.length))

    for l, w in orientations:
        x_candidates = set(x_candidates)
        x_candidates.add(max(0.0, trailer.lower_length - l))
        x_candidates.add(max(0.0, trailer.total_length - l))
        for p in placed:
            x_candidates.add(max(0.0, p.x - l))
        x_candidates = sorted(list(set(round(x, 1) for x in x_candidates if x >= 0)))
        # Генерируем точки Y для ЭТОЙ ширины (Прижимаем к бортам и соседним деталям)
        y_candidates = {0.0, trailer.total_width - w}
        for p in placed:
            y_candidates.add(p.y + p.width)        # Прижаться к правой грани соседа
            y_candidates.add(max(0.0, p.y - w))    # Прижаться к левой грани соседа
        
        y_candidates = sorted(list(set(round(y, 1) for y in y_candidates if 0 <= y <= trailer.total_width - w)))

        for x in x_candidates:
            if x + l > trailer.total_length:
                continue
                
            for y in y_candidates:
                z = get_lowest_z(x, y, l, w, placed, trailer)
                if z < 0:
                    continue
                
                # Проверка высоты (ПШЛ-1 игнорирует крышу)
                if not getattr(item.rules, "ignore_height_limit", False):
                    is_upper = x >= trailer.lower_length
                    h_limit = trailer.upper_max_height if is_upper else trailer.lower_max_height
                    if z + item.height > h_limit:
                        continue

                # Проверка правил
                if not check_support_and_rules(item, x, y, z, l, w, placed, trailer):
                    continue

                # Симуляция ЦТ
                simulated_p = PlacedItem(item=item, sequence_number=0, x=x, y=y, z=z, width=w, length=l, height=item.height)
                new_cg = calculate_trailer_cg(placed + [simulated_p])
                
                # === ФИТНЕС ФУНКЦИЯ ===
                
                # 1. ПРИЖИМ К ПОЛУ: Громадный штраф за высоту. Сначала заполняем всю площадь!
                height_penalty = z * 1000.0  
                
                # 2. ЦТ: Штраф за отклонение от баланса
                cg_penalty = abs(new_cg - trailer.ideal_cg_from_rear) * 2.0
                
                # 3. ПРИЖИМ К КРАЯМ: Штрафуем, если деталь болтается в центре пустого места.
                # Если деталь стоит у борта (Y=0 или Y=2400-w), dist_to_wall будет 0 -> Штрафа нет!
                dist_to_left_wall = y
                dist_to_right_wall = trailer.total_width - (y + w)
                y_penalty = min(dist_to_left_wall, dist_to_right_wall) * 0.1

                # 4. ЗАПОЛНЕНИЕ РЯДА: бонус, если текущая деталь оставляет место под ближайшие детали
                row_fill_bonus = estimate_row_fill_bonus(item, future_items, trailer)
                
                score = height_penalty + cg_penalty + y_penalty - row_fill_bonus

                if score < best_score:
                    best_score = score
                    best_spot = (x, y, z, l, w)

    if best_spot is None:
        return None

    return best_spot, best_score

def pack_one_trip(remaining_items: List[JBIItem], trailer: TrailerConfig, start_seq: int) -> Tuple[List[PlacedItem], List[JBIItem], int]:
    placed: List[PlacedItem] = []
    unpacked: List[JBIItem] = []
    current_weight = 0.0
    seq_num = start_seq

    queue = remaining_items[:]
    while queue:
        window_end = min(3, len(queue))
        best_choice = None

        for candidate_index in range(window_end):
            candidate = queue[candidate_index]
            if current_weight + candidate.weight > trailer.max_weight:
                continue

            future_items = queue[candidate_index + 1:candidate_index + 4]
            spot_result = find_best_spot(candidate, placed, trailer, future_items)
            if not spot_result:
                continue

            spot, score = spot_result
            if best_choice is None or score < best_choice[0]:
                best_choice = (score, candidate_index, candidate, spot)

        if best_choice is None:
            unpacked.append(queue.pop(0))
            continue

        _, candidate_index, candidate, spot = best_choice
        x, y, z, l, w = spot
        placed.append(PlacedItem(
            item=candidate, sequence_number=seq_num,
            x=x, y=y, z=z, width=w, length=l, height=candidate.height
        ))
        current_weight += candidate.weight
        seq_num += 1
        del queue[candidate_index]

    return placed, unpacked, seq_num

def calculate_optimizer(initial_items: List[JBIItem], trailer: TrailerConfig) -> List[Trip]:
    flat_items: List[JBIItem] = []
    for group in initial_items:
        enriched_group = enrich_item_with_rules(group)
        for _ in range(group.count):
            flat_items.append(enriched_group)

    if not flat_items:
        return []

    # Сортировка: ПШЛ-1 -> ПТ -> ПП/ПБ -> ЛМ (Сначала самые громоздкие)
    priority_map = {"ПШЛ-1": 0, "ПТ": 1, "ПП": 2, "ПБ": 2, "ЛМ": 3}
    flat_items.sort(key=lambda it: (
        priority_map.get(it.code, 99),
        -it.weight,
        -it.area  # Сначала с самой большой площадью, чтобы занимать пол
    ))

    trips: List[Trip] = []
    remaining = flat_items[:]
    seq_num = 1

    while remaining:
        placed, unpacked, seq_num = pack_one_trip(remaining, trailer, seq_num)

        if not placed:
            print(f"WARNING: Невозможно разместить: {[i.code for i in unpacked]}")
            break

        improved_placed = improve_trip_balance(placed, trailer, placed[0].sequence_number if placed else seq_num)
        if improved_placed is not placed:
            placed = improved_placed

        final_cg = calculate_trailer_cg(placed)
        total_weight = sum(p.item.weight for p in placed)
        
        trips.append(Trip(
            id=len(trips) + 1,
            items=placed,
            total_weight=total_weight,
            cg_x_from_rear=round(final_cg, 1),
            cg_mismatch=round(final_cg - trailer.ideal_cg_from_rear, 1)
        ))
        
        remaining = unpacked

        if len(trips) > 25:
            break

    return trips

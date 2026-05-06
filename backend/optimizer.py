import math
from typing import List, Optional, Tuple
from models import JBIItem, TrailerConfig, PlacedItem, Trip, enrich_item_with_rules


def get_item_footprint_width(item: JBIItem) -> float:
    if item.rules.can_rotate_yaw:
        return min(item.width, item.length)
    return item.width

def is_ladder(item: JBIItem) -> bool:
    return item.code == "ЛМ"

def keeps_ladders_after_main_items(items: List[JBIItem]) -> bool:
    seen_ladder = False
    for item in items:
        if is_ladder(item):
            seen_ladder = True
        elif seen_ladder:
            return False
    return True

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
        if not keeps_ladders_after_main_items(order):
            continue

        candidate_items, unpacked, _ = pack_one_trip(order, trailer, start_seq)
        if unpacked:
            continue

        candidate_mismatch = abs(calculate_cg_mismatch(candidate_items, trailer))
        if candidate_mismatch + 1e-6 < best_mismatch:
            best_mismatch = candidate_mismatch
            best_items = candidate_items

    return best_items

def move_items_toward_ideal_cg(placed_items: List[PlacedItem], trailer: TrailerConfig) -> List[PlacedItem]:
    best_items = placed_items
    best_mismatch = abs(calculate_cg_mismatch(best_items, trailer))

    if best_mismatch <= 0.1:
        return best_items

    max_passes = max(1, len(best_items) * 2)
    for _ in range(max_passes):
        improved = False

        for moved_item in sorted(best_items, key=lambda p: abs(p.item.weight), reverse=True):
            remaining_items = [p for p in best_items if p is not moved_item]
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
                best_items = candidate_items
                best_mismatch = candidate_mismatch
                improved = True
                break

        if not improved:
            break

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

def is_center_supported(x: float, y: float, l: float, w: float, z: float, placed: List[PlacedItem]) -> bool:
    center_x = x + l / 2
    center_y = y + w / 2

    for p in placed:
        if not math.isclose(p.z + p.height, z, abs_tol=0.1):
            continue

        if p.x <= center_x <= p.x + p.length and p.y <= center_y <= p.y + p.width:
            return True

    return False

def has_xy_overlap(x: float, y: float, l: float, w: float, placed: List[PlacedItem]) -> bool:
    for p in placed:
        if get_intersection_area(x, y, w, l, p.x, p.y, p.width, p.length) > 0.1:
            return True

    return False

def build_x_candidates(l: float, item_length: float, placed: List[PlacedItem], trailer: TrailerConfig) -> List[float]:
    x_candidates = {0.0, trailer.lower_length, max(0.0, trailer.lower_length - l), max(0.0, trailer.total_length - l)}

    for p in placed:
        x_candidates.add(p.x)
        x_candidates.add(p.x + p.length)
        x_candidates.add(max(0.0, p.x - l))
        x_candidates.add(max(0.0, p.x + p.length - l))

    return sorted(list(set(round(x, 1) for x in x_candidates if x >= 0)))

def build_y_candidates(w: float, placed: List[PlacedItem], trailer: TrailerConfig) -> List[float]:
    y_candidates = {0.0, trailer.total_width - w}

    for p in placed:
        y_candidates.add(p.y)
        y_candidates.add(p.y + p.width)
        y_candidates.add(max(0.0, p.y - w))
        y_candidates.add(max(0.0, p.y + p.width - w))

    return sorted(list(set(round(y, 1) for y in y_candidates if 0 <= y <= trailer.total_width - w)))

def find_lower_level_spot(item: JBIItem, l: float, w: float, placed: List[PlacedItem], trailer: TrailerConfig) -> Optional[Tuple[float, float, float, float, float]]:
    best_spot = None
    best_mismatch = float("inf")

    for x in build_x_candidates(l, item.length, placed, trailer):
        if x + l > trailer.total_length:
            continue

        floor_z = get_floor_z(x, l, trailer)
        if floor_z < 0:
            continue

        for y in build_y_candidates(w, placed, trailer):
            if has_xy_overlap(x, y, l, w, placed):
                continue

            if not check_support_and_rules(item, x, y, floor_z, l, w, placed, trailer):
                continue

            simulated_p = PlacedItem(item=item, sequence_number=0, x=x, y=y, z=floor_z, width=w, length=l, height=item.height)
            mismatch = abs(calculate_cg_mismatch(placed + [simulated_p], trailer))
            if mismatch < best_mismatch:
                best_mismatch = mismatch
                best_spot = (x, y, floor_z, l, w)

    return best_spot

def check_support_and_rules(item: JBIItem, x: float, y: float, z: float, 
                            l: float, w: float, placed: List[PlacedItem], 
                            trailer: TrailerConfig) -> bool:
    floor_z = get_floor_z(x, l, trailer)

    if item.code == "ПШЛ-1" and not (math.isclose(floor_z, 0.0, abs_tol=0.1) and math.isclose(z, 0.0, abs_tol=0.1)):
        return False
    
    # 1. Если прямо на полу - проблем нет (кроме ЛМ, для нее пол разрешен)
    if math.isclose(z, floor_z, abs_tol=0.1):
        return True

    # 2. Если деталь требует ТОЛЬКО пола
    if item.rules.must_be_on_floor:
        return False

    if not is_center_supported(x, y, l, w, z, placed):
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
    x_candidates = build_x_candidates(item.length, item.length, placed, trailer)

    # 2. Перебор ориентаций
    orientations = [(item.length, item.width)]
    if item.rules.can_rotate_yaw:
        orientations.append((item.width, item.length))

    for l, w in orientations:
        x_candidates = build_x_candidates(l, item.length, placed, trailer)
        # Генерируем точки Y для ЭТОЙ ширины (Прижимаем к бортам и соседним деталям)
        y_candidates = build_y_candidates(w, placed, trailer)

        for x in x_candidates:
            if x + l > trailer.total_length:
                continue
                
            for y in y_candidates:
                z = get_lowest_z(x, y, l, w, placed, trailer)
                if z < 0:
                    continue

                floor_z = get_floor_z(x, l, trailer)
                if z > floor_z + 0.1:
                    lower_spot = find_lower_level_spot(item, l, w, placed, trailer)
                    if lower_spot:
                        x, y, z, l, w = lower_spot
                
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

def try_refill_underweight_trip(
    placed_items: List[PlacedItem],
    unpacked_items: List[JBIItem],
    trailer: TrailerConfig,
    start_seq: int,
    min_target_weight: float = 20000.0,
) -> Tuple[List[PlacedItem], List[JBIItem], int]:
    current_weight = sum(p.item.weight for p in placed_items)
    if current_weight >= min_target_weight or not unpacked_items:
        return placed_items, unpacked_items, start_seq + len(placed_items)

    best_placed = placed_items
    best_unpacked = unpacked_items
    best_seq = start_seq + len(placed_items)
    best_weight = current_weight
    best_mismatch = abs(calculate_cg_mismatch(placed_items, trailer))

    base_items = [p.item for p in sorted(placed_items, key=lambda p: p.sequence_number)]

    for candidate_index, candidate in enumerate(unpacked_items):
        if current_weight + candidate.weight > trailer.max_weight:
            continue

        rest_unpacked = unpacked_items[:candidate_index] + unpacked_items[candidate_index + 1:]
        candidate_orders = [base_items + [candidate]]
        if not is_ladder(candidate):
            candidate_orders.append([candidate] + base_items)

        for order in generate_order_variants([candidate] + base_items):
            if keeps_ladders_after_main_items(order):
                candidate_orders.append(order)

        for order in candidate_orders:
            rebuilt_placed, rebuilt_unpacked, rebuilt_seq = pack_one_trip(order, trailer, start_seq)
            if rebuilt_unpacked:
                continue

            rebuilt_weight = sum(p.item.weight for p in rebuilt_placed)
            rebuilt_mismatch = abs(calculate_cg_mismatch(rebuilt_placed, trailer))
            is_better = rebuilt_weight > best_weight + 1e-6
            is_same_weight_better_balance = math.isclose(rebuilt_weight, best_weight, abs_tol=1e-6) and rebuilt_mismatch < best_mismatch

            if is_better or is_same_weight_better_balance:
                best_placed = rebuilt_placed
                best_unpacked = rest_unpacked
                best_seq = rebuilt_seq
                best_weight = rebuilt_weight
                best_mismatch = rebuilt_mismatch

        if best_weight >= min_target_weight:
            break

    return best_placed, best_unpacked, best_seq

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
        trip_start_seq = seq_num
        placed, unpacked, seq_num = pack_one_trip(remaining, trailer, seq_num)

        if not placed:
            print(f"WARNING: Невозможно разместить: {[i.code for i in unpacked]}")
            break

        placed, unpacked, seq_num = try_refill_underweight_trip(placed, unpacked, trailer, trip_start_seq)

        improved_placed = improve_trip_balance(placed, trailer, placed[0].sequence_number if placed else seq_num)
        if improved_placed is not placed:
            placed = improved_placed

        balanced_placed = move_items_toward_ideal_cg(placed, trailer)
        if balanced_placed is not placed:
            placed = balanced_placed

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

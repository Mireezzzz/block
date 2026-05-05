from dataclasses import dataclass
from typing import Optional
from models import JBIItem, TrailerConfig, PlacedItem, Trip


ITEM_PRIORITY = {
    "ПШЛ-1": 0,
    "ПТ":    1,
    "ПП":    2,
    "ПБ":    2,
    "ЛМ":    3,
}


@dataclass
class ExpandedItem:
    item: JBIItem
    sequence_number: int


def normalize_item(group: JBIItem) -> JBIItem:
    """
    ПШЛ-1: в исходных данных width=2830, length=2030 — перепутаны.
    Поперёк прицепа (2400мм) должен идти меньший размер = 2030мм.
    Принудительно выставляем: width=2030 (поперёк), length=2830 (вдоль).
    """
    if group.code == "ПШЛ-1":
        w = min(group.width, group.length)  # 2030 — поперёк
        l = max(group.width, group.length)  # 2830 — вдоль
        return JBIItem(id=group.id, code=group.code, name=group.name,
                       width=w, length=l, height=group.height,
                       weight=group.weight, count=1)
    return JBIItem(id=group.id, code=group.code, name=group.name,
                   width=group.width, length=group.length, height=group.height,
                   weight=group.weight, count=1)


def calculate_optimizer(initial_items: list[JBIItem], trailer: TrailerConfig) -> list[Trip]:
    flat_items: list[ExpandedItem] = []
    sequence_number = 1
    for group in initial_items:
        for _ in range(group.count):
            flat_items.append(ExpandedItem(item=normalize_item(group), sequence_number=sequence_number))
            sequence_number += 1

    if not flat_items:
        return []

    flat_items.sort(key=lambda it: (
        ITEM_PRIORITY.get(it.item.code, 99),
        -it.item.weight,
        -it.item.length,
        it.sequence_number,
    ))

    trips: list[Trip] = []
    remaining = flat_items[:]

    while remaining:
        placed, used = pack_one_trip(remaining, trailer)

        if not placed:
            remaining.pop(0)
            continue

        trips.append(create_trip(len(trips) + 1, placed, trailer))
        used_ids = set(id(it) for it in used)
        remaining = [it for it in remaining if id(it) not in used_ids]

        if len(trips) > 25:
            break

    return trips


def pack_one_trip(
    items: list[ExpandedItem], trailer: TrailerConfig
) -> tuple[list[PlacedItem], list[ExpandedItem]]:
    placed: list[PlacedItem] = []
    used: list[ExpandedItem] = []
    current_weight = 0.0

    for expanded in items:
        item = expanded.item
        if current_weight + item.weight > trailer.max_weight:
            continue
        spot = find_spot(placed, expanded, trailer)
        if spot:
            placed.append(spot)
            used.append(expanded)
            current_weight += item.weight

    return placed, used


def find_spot(
    placed: list[PlacedItem], expanded: ExpandedItem, trailer: TrailerConfig
) -> Optional[PlacedItem]:
    item = expanded.item
    total_len = trailer.lower_length + trailer.upper_length

    ideal_x = trailer.ideal_cg_from_rear - item.length / 2
    x_candidates = sorted({0.0, max(0.0, ideal_x)} | {p.x + p.length for p in placed})

    y_center = (trailer.total_width - item.width) / 2
    if item.code == "ПШЛ-1":
        y_candidates = [y_center]
    elif item.width <= 1200:
        base = {0.0, trailer.total_width - item.width, y_center}
        for p in placed:
            for ye in (p.y, p.y + p.width - item.width):
                if 0 <= ye <= trailer.total_width - item.width:
                    base.add(round(ye, 1))
        y_candidates = sorted(base)
    else:
        base = {y_center}
        for p in placed:
            for ye in (p.y, p.y + p.width - item.width):
                if 0 <= ye <= trailer.total_width - item.width:
                    base.add(round(ye, 1))
        y_candidates = sorted(base)

    best_spot: Optional[PlacedItem] = None
    best_score = float("inf")

    for x in x_candidates:
        if x + item.length > total_len:
            continue
        if x < trailer.lower_length < x + item.length:
            continue

        is_upper = x >= trailer.lower_length
        h_limit = trailer.upper_max_height if is_upper else trailer.lower_max_height

        for y in y_candidates:
            if y < 0 or y + item.width > trailer.total_width:
                continue

            xy_overlap = get_xy_overlap(placed, x, y, item.length, item.width)

            if not check_placement_rules(item, xy_overlap):
                continue

            z = compute_z(xy_overlap)

            if item.code != "ПШЛ-1" and z + item.height > h_limit:
                continue

            if z > 0 and not check_stability(placed, item, x, y, z):
                continue

            score = score_position(item, x, y, z, trailer, placed)
            if score < best_score:
                best_score = score
                best_spot = PlacedItem(
                    item=item,
                    sequence_number=expanded.sequence_number,
                    x=x, y=y, z=z,
                    width=item.width, length=item.length, height=item.height,
                )

    return best_spot


def get_xy_overlap(
    placed: list[PlacedItem], x: float, y: float, length: float, width: float
) -> list[PlacedItem]:
    return [
        p for p in placed
        if p.x < x + length and p.x + p.length > x
        and p.y < y + width and p.y + p.width > y
    ]


def compute_z(overlap: list[PlacedItem]) -> float:
    if not overlap:
        return 0.0
    return max(p.z + p.height for p in overlap)


def check_placement_rules(item: JBIItem, overlap: list[PlacedItem]) -> bool:
    """
    ПШЛ-1 — только на пустой пол, ничего под/над
    На ПШЛ-1 — нельзя ничего
    ЛМ — на любой груз; на ЛМ только ЛМ
    ПТ/ПП/ПБ — не на ЛМ, не на ПШЛ-1
    """
    codes_below = {p.item.code for p in overlap}

    if item.code == "ПШЛ-1":
        return len(overlap) == 0

    if "ПШЛ-1" in codes_below:
        return False

    if item.code != "ЛМ" and "ЛМ" in codes_below:
        return False

    return True


def check_stability(
    placed: list[PlacedItem], item: JBIItem,
    x: float, y: float, z: float
) -> bool:
    """
    Центр тяжести груза должен проецироваться внутрь bbox опоры.
    Опора = грузы чей верх == z и пересекаются с нами в плане.
    """
    cx = x + item.length / 2
    cy = y + item.width / 2

    support = [
        p for p in placed
        if abs((p.z + p.height) - z) < 0.1
        and p.x < x + item.length and p.x + p.length > x
        and p.y < y + item.width and p.y + p.width > y
    ]

    if not support:
        return False

    sx_min = min(p.x for p in support)
    sx_max = max(p.x + p.length for p in support)
    sy_min = min(p.y for p in support)
    sy_max = max(p.y + p.width for p in support)

    return sx_min <= cx <= sx_max and sy_min <= cy <= sy_max


def score_position(
    item: JBIItem, x: float, y: float, z: float,
    trailer: TrailerConfig, placed: list[PlacedItem]
) -> float:
    """
    Меньше = лучше.
    1. Сначала пол (штраф за высоту)
    2. Ближе к идеальному ЦТ по X
    3. Симметрия по Y
    4. ЛМ штрафуем если есть свободный пол — пусть лучше займут место на полу
       чем лезут на ПБ/ПП когда там есть пустое место
    """
    cg_dist_x = abs((x + item.length / 2) - trailer.ideal_cg_from_rear)
    cg_dist_y = abs((y + item.width / 2) - trailer.total_width / 2)
    height_penalty = z * 10

    # Штраф для ЛМ: если z>0 и под ней не другая ЛМ — предпочитаем пол
    lm_on_plates_penalty = 0.0
    if item.code == "ЛМ" and z > 0:
        support_codes = {
            p.item.code for p in placed
            if abs((p.z + p.height) - z) < 0.1
            and p.x < x + item.length and p.x + p.length > x
            and p.y < y + item.width and p.y + p.width > y
        }
        if "ЛМ" not in support_codes:
            lm_on_plates_penalty = 5000.0  # сильный штраф — лестница на не-лестнице

    return height_penalty + cg_dist_x * 3.0 + cg_dist_y * 0.5 + lm_on_plates_penalty


def create_trip(id: int, items: list[PlacedItem], trailer: TrailerConfig) -> Trip:
    total_weight = sum(p.item.weight for p in items)
    total_moment = sum(p.item.weight * (p.x + p.length / 2) for p in items)
    cg_x = total_moment / total_weight if total_weight > 0 else 0.0
    cg_mismatch = cg_x - trailer.ideal_cg_from_rear
    return Trip(
        id=id, items=items,
        total_weight=total_weight,
        cg_x_from_rear=cg_x,
        cg_mismatch=cg_mismatch,
    )
from dataclasses import dataclass, field

@dataclass
class PlacementRules:
    """Бизнес-правила укладки для конкретного типа деталей."""
    can_rotate_yaw: bool = False
    must_be_on_floor: bool = False
    requires_empty_top: bool = False
    stack_only_on_same: bool = False
    allow_only_same_on_top: bool = False
    ignore_height_limit: bool = False
    
    min_support_pct: float = 0.75

@dataclass
class JBIItem:
    id: str
    code: str
    name: str
    width: float
    length: float
    height: float
    weight: float
    count: int
    rules: PlacementRules = field(default_factory=PlacementRules)

    @property
    def area(self) -> float:
        return self.width * self.length

# === БАЗА ЗНАНИЙ ===
RULES_REGISTRY = {
    "ПШЛ-1": PlacementRules(
        can_rotate_yaw=True,
        must_be_on_floor=True,
        requires_empty_top=True,
        ignore_height_limit=True  # <-- Шахте лифта плевать на крышу прицепа
    ),
    "ЛМ": PlacementRules(
        can_rotate_yaw=False,
        requires_empty_top=False,
        stack_only_on_same=True,
        allow_only_same_on_top=True
    ),
}

def enrich_item_with_rules(item: JBIItem) -> JBIItem:
    if item.code in RULES_REGISTRY:
        item.rules = RULES_REGISTRY[item.code]

    if item.code == "ПШЛ-1":
        width = min(item.width, item.length)
        length = max(item.width, item.length)
        item.width = width
        item.length = length

    return item

@dataclass
class TrailerConfig:
    max_weight: float
    total_width: float
    lower_length: float
    lower_max_height: float
    upper_length: float
    upper_max_height: float
    height_diff: float
    ideal_cg_from_rear: float

    @property
    def total_length(self) -> float:
        return self.lower_length + self.upper_length

@dataclass
class PlacedItem:
    item: JBIItem
    sequence_number: int
    x: float
    y: float
    z: float
    width: float
    length: float
    height: float

    def to_dict(self):
        return {
            "item": {
                "id": self.item.id,
                "code": self.item.code,
                "name": self.item.name,
                "width": self.item.width,
                "length": self.item.length,
                "height": self.item.height,
                "weight": self.item.weight,
                "count": self.item.count,
            },
            "sequenceNumber": self.sequence_number,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "width": self.width,
            "length": self.length,
            "height": self.height,
        }

@dataclass
class Trip:
    id: int
    items: list[PlacedItem]
    total_weight: float
    cg_x_from_rear: float
    cg_mismatch: float

    def to_dict(self):
        return {
            "id": self.id,
            "items": [p.to_dict() for p in self.items],
            "totalWeight": self.total_weight,
            "cgXFromRear": self.cg_x_from_rear,
            "cgMismatch": self.cg_mismatch,
        }

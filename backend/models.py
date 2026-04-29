from dataclasses import dataclass, field
from typing import Optional


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


@dataclass
class PlacedItem:
    item: JBIItem
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
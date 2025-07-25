from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

from .enums import ItemSlot, ItemClass, ItemQuality


@dataclass
class Item:
    name: str
    price: int


@dataclass
class GearItem(Item):
    slot: ItemSlot
    quality: ItemQuality
    allowed_classes: List[ItemClass]
    stats: Dict[str, float] = field(default_factory=dict)


@dataclass
class PotionItem(Item):
    heal: int = 0
    mana: int = 0

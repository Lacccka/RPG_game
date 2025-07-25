from __future__ import annotations
import random
from typing import Dict, List

from ..config import CONFIG
from .item import GearItem, PotionItem
from .enums import ItemSlot, ItemClass, ItemQuality


class Store:
    def __init__(self) -> None:
        cfg = CONFIG.get("gear", {})
        self.templates: Dict[str, dict] = cfg.get("items", {})
        self.potions_cfg: List[dict] = cfg.get("potions", [])
        self.rand_by_quality: Dict[str, int] = cfg.get("quality_random_stats", {})

    def available_gear(self) -> List[GearItem]:
        items: List[GearItem] = []
        for name, data in self.templates.items():
            items.append(self._create_gear(name, data))
        return items

    def available_potions(self) -> List[PotionItem]:
        return [
            PotionItem(
                name=p.get("name", "Potion"),
                price=p.get("price", 0),
                heal=p.get("heal", 0),
                mana=p.get("mana", 0),
            )
            for p in self.potions_cfg
        ]

    def _create_gear(self, name: str, data: dict) -> GearItem:
        quality = ItemQuality[data.get("quality", "SHABBY")]
        slot = ItemSlot[data["slot"]]
        classes = [ItemClass[c] for c in data.get("classes", [])]
        price = data.get("price", 0)
        base_stats = data.get("base_stats", {})
        possible = data.get("possible_stats", [])
        count = self.rand_by_quality.get(quality.name, 0)
        chosen = random.sample(possible, min(count, len(possible))) if possible else []
        stats = base_stats.copy()
        for st in chosen:
            for k, v in st.items():
                stats[k] = stats.get(k, 0) + v
        return GearItem(
            name=name,
            price=price,
            slot=slot,
            quality=quality,
            allowed_classes=classes,
            stats=stats,
        )

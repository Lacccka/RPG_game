from __future__ import annotations
import random
from typing import Dict, List

from ..config import CONFIG
from .item import GearItem, PotionItem
from .enums import ItemSlot, ItemClass, ItemQuality


class Store:
    def __init__(self) -> None:
        # грузим новую структуру из gear.yaml
        cfg = CONFIG.get("gear", {})
        self.templates: Dict[str, dict] = cfg.get("items", {})
        self.potions_cfg: List[dict] = cfg.get("potions", [])
        # строим маппинг качества → число случайных статов
        self.quality_tiers: Dict[str, dict] = cfg.get("quality_tiers", {})
        self.rand_by_quality = {
            name: info.get("random_stats_count", 0)
            for name, info in self.quality_tiers.items()
        }

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
        quality = ItemQuality[data.get("quality", "RUSTIC")]

        slot = ItemSlot[data["slot"]]
        classes = [ItemClass[c] for c in data.get("classes", [])]
        price = data.get("price", 0)
        # новые поля: static_stats и random_stats_pool
        static = data.get("static_stats", {})
        pool = data.get("random_stats_pool", [])
        # сколько рандомных бонусов выдавать
        count = self.rand_by_quality.get(quality.name, 0)
        picks = random.sample(pool, min(count, len(pool))) if pool else []
        # собираем итоговые статы
        stats = static.copy()
        for bonus in picks:
            for k, v in bonus.items():
                stats[k] = stats.get(k, 0) + v

        return GearItem(
            name=name,
            price=price,
            slot=slot,
            quality=quality,
            allowed_classes=classes,
            stats=stats,
        )

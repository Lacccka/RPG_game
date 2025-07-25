from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from ..base.combatant import Combatant
from ..config import CONFIG
from .character_class import CharacterClass
from ..battle.enums import Element, DamageSource, CritType
from ..battle.damage import check_hit, calc_damage
from ..battle.status import before_action
from ..items.item import GearItem, PotionItem
from ..items.enums import ItemSlot, ItemClass

if TYPE_CHECKING:
    from .player import Player


@dataclass
class PlayerCharacter(Combatant):
    """
    Игрок‑персонаж: берет базовые статы и рост из CharacterClass,
    хранит опыт, ману и умеет повышать уровень по конфигу growth.
    """

    char_class: Optional[CharacterClass] = field(default=None)
    owner: Optional[Player] = field(default=None)

    # Прогресс
    exp: int = 0  # накопленный опыт

    mana: float = field(init=False, default=0.0)
    mana_regen: float = field(init=False, default=0.0)

    # Для расчёта при повышении уровня
    _growth: dict = field(default_factory=dict, init=False)

    # экипировка по слотам
    equipment: dict[ItemSlot, GearItem] = field(default_factory=dict, init=False)

    def __post_init__(self):
        super().__post_init__()
        if self.char_class:
            self._growth = self.char_class.stat_growth.copy()
            data = self.char_class.data
            # initial mana из класса
            self.base_mana = float(data.get("base_mana", 0))
            self.mana = self.base_mana
            self.mana_regen = float(data.get("mana_regen", 0))

    @staticmethod
    def from_config(
        class_name: str,
        level: int,
        owner: Player,
        name_override: str | None = None,
    ) -> PlayerCharacter:
        cls = CharacterClass[class_name]
        growth = cls.stat_growth
        data = cls.data

        def sanitize(val) -> str:
            if isinstance(val, str):
                return val.split("#", 1)[0].strip()
            return val

        def get_num(key: str, default: float = 0.0) -> float:
            raw = data.get(key, default)
            raw = sanitize(raw)
            return float(raw)

        def get_growth(key: str, default: float = 0.0) -> float:
            raw = growth.get(key, default)
            raw = sanitize(raw)
            return float(raw)

        def calc(base: float, per: float) -> float:
            return base + per * (level - 1)

        # читаем базовые характеристики
        base_health = get_num("base_health")
        base_strength = get_num("base_strength")
        base_agility = get_num("base_agility")
        base_intelligence = get_num("base_intelligence")
        base_defense = get_num("base_defense", 0.0)
        base_accuracy = get_num("base_accuracy", 0.8)
        base_crit = get_num("base_crit_chance", 0.05)
        base_dodge = get_num("base_dodge_chance", 0.03)

        # читаем приросты
        h_growth = get_growth("health")
        s_growth = get_growth("strength")
        a_growth = get_growth("agility")
        i_growth = get_growth("intelligence")
        d_growth = get_growth("defense")
        acc_growth = get_growth("accuracy")
        crit_growth = get_growth("crit_chance")
        dodge_growth = get_growth("dodge_chance")
        mana_growth = get_growth("mana")
        mana_regen_growth = get_growth("mana_regen")

        # создаём персонажа
        pc = PlayerCharacter(
            name=name_override or cls.display_name,
            level=level,
            max_health=int(calc(base_health, h_growth)),
            strength=int(calc(base_strength, s_growth)),
            agility=int(calc(base_agility, a_growth)),
            intelligence=int(calc(base_intelligence, i_growth)),
            defense=calc(base_defense, d_growth),
            accuracy=calc(base_accuracy, acc_growth),
            crit_chance=calc(base_crit, crit_growth),
            dodge_chance=calc(base_dodge, dodge_growth),
            char_class=cls,
            owner=owner,
        )

        # ресурсы по формуле роста
        base_mana_val = calc(get_num("base_mana", 0), mana_growth)
        pc.base_mana = int(base_mana_val)
        pc.mana = pc.base_mana
        pc.mana_regen = calc(get_num("mana_regen", 0), mana_regen_growth)

        # активные и пассивные умения
        pc.skills = [
            skill
            for lvl_req, skills in cls.skills_by_level.items()
            if level >= lvl_req
            for skill in skills
        ]

        # ───── PASSIVE: Evasion Mastery ─────
        if "Evasion Mastery" in pc.skills:
            bonus = CONFIG["skills"]["Evasion Mastery"]["power"]
            # добавляем округлённо
            add = int(pc.agility * bonus + 0.5)
            pc.agility += add

        # ───── PASSIVE: Last Stand ─────
        if "Last Stand" in pc.skills:
            pc.apply_effect({"effect": "survive_one_turn"})

        return pc

    def attack(self, target: Combatant) -> None:
        """Обычная атака с учётом пассивки Cleave."""
        visible = getattr(self, "_visible_enemies", [target])
        allowed = before_action(self, visible)
        if not allowed:
            return
        if target not in allowed:
            target = allowed[0]
        if not check_hit(self, target):
            print(f"{self.name} промахивается! (шанс {self._last_hit:.1%})")
            return

        dmg = calc_damage(
            self,
            target,
            element=Element.PHYSICAL,
            source=DamageSource.NORMAL,
        )
        self._log_hit(target, dmg)
        target.take_damage(dmg)

        # PASSIVE: Cleave
        if "Cleave" in self.skills:
            splash_pct = CONFIG["skills"]["Cleave"]["power"]
            raw = dmg * splash_pct
            splash_dmg = max(1, int(raw + 0.5))
            for other in getattr(self, "_visible_enemies", []):
                if other is not target and other.is_alive:
                    print(
                        f"{self.name} (Cleave) наносит {splash_dmg} урона {other.name}."
                    )
                    other.take_damage(splash_dmg)

    def _log_hit(self, target: Combatant, dmg: int) -> None:
        msg = f"{self.display_name} ({self.char_class.display_name}) "
        if getattr(self, "_last_crit", False):
            msg += "НАНОСИТ КРИТ! "
        msg += f"наносит {dmg} урона"
        if getattr(self, "_last_weak", False):
            msg += " (слабость)"
        elif getattr(self, "_last_resist", False):
            msg += " (резист)"
        print(msg + ".")

    def exp_to_next(self) -> int:
        curve = CONFIG["growth"]["exp_curve"]
        return int(curve["base"] * (self.level ** curve["exponent"]))

    def level_up(self) -> None:
        g = self._growth
        self.level += 1
        self.max_health += int(g.get("health", 0))
        self.strength += int(g.get("strength", 0))
        self.agility += int(g.get("agility", 0))
        self.intelligence += int(g.get("intelligence", 0))
        self.defense += int(g.get("defense", 0))
        self.base_mana += int(g.get("mana", 0))
        self.mana_regen += g.get("mana_regen", 0.0)
        self.accuracy += g.get("accuracy", 0.0)
        self.crit_chance += g.get("crit_chance", 0.0)
        self.dodge_chance += g.get("dodge_chance", 0.0)
        self.health = self.max_health
        print(
            f"🔺 {self.name} достиг уровня {self.level}! "
            f"Следующий уровень за {self.exp_to_next()} XP."
        )

        # Новые умения на этом уровне
        new_skills = self.char_class.skills_by_level.get(self.level, [])
        for skill in new_skills:
            if skill not in self.skills:
                self.skills.append(skill)
                print(f"🔓 {self.name} изучил навык {skill}!")

    def add_exp(self, amount: int) -> None:
        self.exp += amount
        print(
            f"🏅 {self.name} получает {amount} XP "
            f"(итого {self.exp}/{self.exp_to_next()})."
        )
        while self.exp >= self.exp_to_next():
            self.exp -= self.exp_to_next()
            self.level_up()

    # --- Items management -------------------------------------------------
    def equip_item(self, item: GearItem) -> GearItem | None:
        """Equip a gear item and return replaced item if any."""
        if not self.char_class:
            raise ValueError("Character class undefined")
        try:
            cls = ItemClass[self.char_class.name]
        except KeyError:
            raise ValueError("Unsupported character class for items")

        if item.allowed_classes and cls not in item.allowed_classes:
            raise ValueError("Item cannot be equipped by this class")

        prev = self.equipment.get(item.slot)
        if prev:
            for stat, val in prev.stats.items():
                attr = "max_health" if stat == "health" else stat
                if hasattr(self, attr):
                    setattr(self, attr, getattr(self, attr) - val)

        for stat, val in item.stats.items():
            attr = "max_health" if stat == "health" else stat
            if hasattr(self, attr):
                setattr(self, attr, getattr(self, attr) + val)
        self.equipment[item.slot] = item
        return prev

    def consume_potion(self, potion: PotionItem) -> None:
        """Apply effects of potion to this character."""
        if potion.heal:
            self.health = min(self.max_health, self.health + potion.heal)
        if potion.mana:
            self.mana = min(self.base_mana, self.mana + potion.mana)

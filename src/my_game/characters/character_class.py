# src/my_game/characters/character_class.py

from enum import Enum, auto
from ..config import CONFIG


class CharacterClass(Enum):
    WARRIOR = auto()
    MAGE = auto()
    ROGUE = auto()

    @property
    def data(self) -> dict:
        return CONFIG["characters"][self.name]

    @property
    def display_name(self) -> str:
        return self.data["display_name"]

    # — базовые статы
    @property
    def base_health(self) -> int:
        return self.data["base_health"]

    @property
    def base_strength(self) -> int:
        return self.data["base_strength"]

    @property
    def base_agility(self) -> int:
        return self.data["base_agility"]

    @property
    def base_intelligence(self) -> int:
        return self.data["base_intelligence"]

    @property
    def base_defense(self) -> int:
        return self.data.get("base_defense", 0)

    @property
    def base_accuracy(self) -> float:
        return self.data.get("base_accuracy", 0.8)

    @property
    def base_crit_chance(self) -> float:
        return self.data.get("base_crit_chance", 0.05)

    @property
    def base_dodge_chance(self) -> float:
        return self.data.get("base_dodge_chance", 0.03)

    # — мана
    @property
    def base_mana(self) -> int:
        return self.data.get("base_mana", 0)

    @property
    def mana_regen(self) -> int:
        return self.data.get("mana_regen", 0)

    # — рост
    @property
    def stat_growth(self) -> dict:
        return CONFIG["growth"][self.name]

    # — навыки
    @property
    def skills_by_level(self) -> dict:
        return self.data.get("skills", {})

    # — коэффициенты урона
    @property
    def phys_coeff(self) -> float:
        return self.data.get("phys_coeff", 1.0)

    @property
    def mag_coeff(self) -> float:
        return self.data.get("mag_coeff", 1.0)

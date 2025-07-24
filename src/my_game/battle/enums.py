from __future__ import annotations
from enum import Enum, auto


class Element(Enum):
    PHYSICAL = auto()
    FIRE = auto()
    ICE = auto()
    LIGHTNING = auto()
    POISON = auto()
    HOLY = auto()
    DARK = auto()


class DamageSource(Enum):
    NORMAL = auto()  # базовая атака
    SKILL = auto()  # активный навык
    DOT = auto()  # урон‑по‑времени
    TRUE = auto()  # игнорирует броню/резисты


class CritType(Enum):
    NORMAL = auto()  # x1.5   (по умолчанию)
    HEAVY = auto()  # x2.0   (особые скиллы)

from enum import Enum, auto


class ItemSlot(Enum):
    HEAD = auto()
    CHEST = auto()
    LEGS = auto()
    HANDS = auto()
    BOOTS = auto()
    WEAPON = auto()


class ItemClass(Enum):
    WARRIOR = auto()
    MAGE = auto()
    ROGUE = auto()


class ItemQuality(Enum):
    SHABBY = auto()
    STURDY = auto()
    RARE = auto()
    MASTERWORK = auto()
    LEGENDARY = auto()
    RELIC = auto()
    UNIQUE = auto()

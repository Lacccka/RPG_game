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
    SUPPORT = auto()
    ARCHER = auto()
    TANK = auto()


class ItemQuality(Enum):
    RUSTIC = auto()  # «Скромное»
    FINE = auto()  # «Изящное»
    EXQUISITE = auto()  # «Изысканное»
    EPIC = auto()  # «Эпосное»
    MYTHIC = auto()  # «Мифическое»
    RELIC = auto()  # «Реликтовое»
    ETERNAL = auto()  # «Вечное»

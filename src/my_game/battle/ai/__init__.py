# src/my_game/battle/ai/__init__.py

"""
Стратегии ИИ для боевой системы.
"""

from .base_ai import BaseAI
from .warrior_ai import WarriorAI
from .mage_ai import MageAI
from .rogue_ai import RogueAI

__all__ = [
    "BaseAI",
    "WarriorAI",
    "MageAI",
    "RogueAI",
]

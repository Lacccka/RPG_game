from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

from .player_character import PlayerCharacter
from .character_class import CharacterClass

if TYPE_CHECKING:
    from .character_class import CharacterClass


@dataclass
class Player:
    id: int
    username: str
    characters: List[PlayerCharacter] = field(default_factory=list)
    gold: int = 100
    inventory: List = field(default_factory=list)

    def create_character(
        self, char_name: str, char_class: CharacterClass, level: int = 1
    ) -> PlayerCharacter:
        pc = PlayerCharacter.from_config(char_class.name, level, owner=self)
        pc.name = char_name
        self.characters.append(pc)
        return pc

    def get_character_class(self, name: str) -> CharacterClass:
        return CharacterClass[name]

    def add_gold(self, amount: int) -> None:
        self.gold += amount

    def spend_gold(self, amount: int) -> bool:
        if self.gold >= amount:
            self.gold -= amount
            return True
        return False

    def add_item(self, item) -> None:
        self.inventory.append(item)

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Sequence

from my_game.characters.player import Player
from my_game.characters.player_character import PlayerCharacter


class AbstractUsersRepo(ABC):
    @abstractmethod
    async def get_user(self, user_id: int, chat_id: int) -> Player | None: ...

    @abstractmethod
    async def add_user(self, user_id: int, chat_id: int, username: str) -> Player: ...

    @abstractmethod
    async def get_or_create(
        self, user_id: int, chat_id: int, username: str
    ) -> Player: ...

    @abstractmethod
    async def update_user(self, player: Player, chat_id: int) -> None: ...


class AbstractCharactersRepo(ABC):
    @abstractmethod
    async def get_characters(
        self, user_id: int, chat_id: int
    ) -> Sequence[PlayerCharacter]: ...

    @abstractmethod
    async def add_character(
        self, user_id: int, chat_id: int, name: str, class_name: str
    ) -> PlayerCharacter: ...

    @abstractmethod
    async def update_character(self, char: PlayerCharacter, chat_id: int) -> None: ...


class AbstractInventoryRepo(ABC):
    @abstractmethod
    async def get_items(self, user_id: int, chat_id: int): ...

    @abstractmethod
    async def add_item(self, user_id: int, chat_id: int, item) -> None: ...

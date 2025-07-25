from __future__ import annotations
import json
from dataclasses import asdict
from typing import List

import aiosqlite

from my_game.characters.player import Player
from my_game.characters.player_character import PlayerCharacter
from my_game.characters.character_class import CharacterClass
from my_game.items.item import GearItem, PotionItem
from my_game.items.enums import ItemSlot, ItemClass, ItemQuality

from .base import (
    AbstractUsersRepo,
    AbstractCharactersRepo,
    AbstractInventoryRepo,
    AbstractPartyRepo,
)


class SQLiteUsersRepo(AbstractUsersRepo):
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def get_user(self, user_id: int, chat_id: int) -> Player | None:
        cur = await self.conn.execute(
            "SELECT user_id, username, gold FROM users WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        row = await cur.fetchone()
        if row:
            return Player(id=row[0], username=row[1], gold=row[2])
        return None

    async def add_user(self, user_id: int, chat_id: int, username: str) -> Player:
        await self.conn.execute(
            "INSERT OR IGNORE INTO users(user_id, chat_id, username, gold) VALUES (?, ?, ?, ?)",
            (user_id, chat_id, username, 100),
        )
        await self.conn.commit()
        return Player(id=user_id, username=username)

    async def get_or_create(self, user_id: int, chat_id: int, username: str) -> Player:
        user = await self.get_user(user_id, chat_id)
        if user:
            return user
        return await self.add_user(user_id, chat_id, username)

    async def update_user(self, player: Player, chat_id: int) -> None:
        await self.conn.execute(
            "UPDATE users SET username=?, gold=? WHERE user_id=? AND chat_id=?",
            (player.username, player.gold, player.id, chat_id),
        )
        await self.conn.commit()


class SQLitePartyRepo(AbstractPartyRepo):
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def get_party(self, user_id: int, chat_id: int):
        cur = await self.conn.execute(
            "SELECT char_ids FROM party WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        row = await cur.fetchone()
        if row:
            return json.loads(row[0])
        return []

    async def set_party(self, user_id: int, chat_id: int, char_ids):
        await self.conn.execute(
            "INSERT INTO party(user_id, chat_id, char_ids) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, chat_id) DO UPDATE SET char_ids=excluded.char_ids",
            (user_id, chat_id, json.dumps(list(char_ids))),
        )
        await self.conn.commit()


class SQLiteCharactersRepo(AbstractCharactersRepo):
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def get_characters(self, user_id: int, chat_id: int) -> List[PlayerCharacter]:
        cur = await self.conn.execute(
            "SELECT id, name, class, level, exp, hp, mana FROM characters WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        rows = await cur.fetchall()
        chars: List[PlayerCharacter] = []
        for r in rows:
            pc = PlayerCharacter.from_config(r[2], r[3], owner=None, name_override=r[1])
            pc.exp = r[4]
            pc.health = r[5]
            pc.mana = r[6]
            pc.__dict__["db_id"] = r[0]
            chars.append(pc)
        return chars

    async def add_character(
        self, user_id: int, chat_id: int, name: str, class_name: str
    ) -> PlayerCharacter:
        pc = PlayerCharacter.from_config(class_name, 1, owner=None, name_override=name)
        cur = await self.conn.execute(
            "INSERT INTO characters(user_id, chat_id, name, class, level, exp, hp, mana) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                chat_id,
                pc.name,
                class_name,
                pc.level,
                pc.exp,
                pc.health,
                pc.mana,
            ),
        )
        await self.conn.commit()
        pc.__dict__["db_id"] = cur.lastrowid
        return pc

    async def update_character(self, char: PlayerCharacter, chat_id: int) -> None:
        char_id = getattr(char, "db_id", None)
        if not char_id:
            return
        await self.conn.execute(
            "UPDATE characters SET level=?, exp=?, hp=?, mana=? WHERE id=? AND chat_id=?",
            (char.level, char.exp, char.health, char.mana, char_id, chat_id),
        )
        await self.conn.commit()


class SQLiteInventoryRepo(AbstractInventoryRepo):
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def get_items(self, user_id: int, chat_id: int):
        cur = await self.conn.execute(
            "SELECT id, data FROM inventory WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        rows = await cur.fetchall()
        items = []
        for r in rows:
            data = json.loads(r[1])
            if data["type"] == "gear":
                item = GearItem(
                    name=data["name"],
                    price=data["price"],
                    slot=ItemSlot[data["slot"]],
                    quality=ItemQuality[data["quality"]],
                    allowed_classes=[ItemClass[c] for c in data["classes"]],
                    stats=data.get("stats", {}),
                )
            else:
                item = PotionItem(
                    name=data["name"],
                    price=data["price"],
                    heal=data.get("heal", 0),
                    mana=data.get("mana", 0),
                )
            item.__dict__["db_id"] = r[0]
            items.append(item)
        return items

    async def add_item(self, user_id: int, chat_id: int, item) -> None:
        if isinstance(item, GearItem):
            data = {
                "type": "gear",
                "name": item.name,
                "price": item.price,
                "slot": item.slot.name,
                "quality": item.quality.name,
                "classes": [c.name for c in item.allowed_classes],
                "stats": item.stats,
            }
        else:
            data = {
                "type": "potion",
                "name": item.name,
                "price": item.price,
                "heal": getattr(item, "heal", 0),
                "mana": getattr(item, "mana", 0),
            }
        await self.conn.execute(
            "INSERT INTO inventory(user_id, chat_id, data) VALUES (?, ?, ?)",
            (user_id, chat_id, json.dumps(data)),
        )
        await self.conn.commit()

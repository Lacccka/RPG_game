from __future__ import annotations

from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from aiogram.filters import CommandStart

from ..repositories.db import Database
from ..services import simulate_battle, store
from my_game.characters.character_class import CharacterClass
from my_game.items.item import GearItem, PotionItem
from my_game.config import CONFIG

router = Router()
# Отбираем только личные чаты
router.message.filter(F.chat.type == ChatType.PRIVATE)

active_shops: dict[tuple[int, int], list] = {}
active_inventories: dict[tuple[int, int], list] = {}
party_select: dict[tuple[int, int], list] = {}
pending_battles: dict[tuple[int, int], list] = {}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Персонажи")],
            [KeyboardButton(text="Магазин")],
            [KeyboardButton(text="Инвентарь")],
            [KeyboardButton(text="Отдых")],
            [KeyboardButton(text="Бой")],
        ],
        resize_keyboard=True,
    )


def chars_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать персонажа")],
            [KeyboardButton(text="Отряд")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    db: Database = message.bot.db
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.full_name
    await db.users.get_or_create(user_id, chat_id, username)
    await message.answer("Добро пожаловать в RPG!", reply_markup=main_menu())


@router.message(F.text == "Назад")
async def go_back(message: Message):
    active_shops.pop((message.from_user.id, message.chat.id), None)
    active_inventories.pop((message.from_user.id, message.chat.id), None)
    party_select.pop((message.from_user.id, message.chat.id), None)
    await message.answer("Главное меню", reply_markup=main_menu())


@router.message(F.text == "Инвентарь")
async def show_inventory(message: Message):
    db: Database = message.bot.db
    key = (message.from_user.id, message.chat.id)
    items = await db.inventory.get_items(*key)
    active_inventories[key] = items
    if not items:
        text = "Инвентарь пуст."
    else:
        lines = []
        for i, it in enumerate(items):
            if isinstance(it, GearItem):
                lines.append(f"{i+1}. {it.name} ({it.slot.name})")
            else:
                desc = []
                if it.heal:
                    desc.append(f"HP+{it.heal}")
                if it.mana:
                    desc.append(f"MP+{it.mana}")
                lines.append(f"{i+1}. {it.name} ({', '.join(desc)})")
        text = "Ваш инвентарь:\n" + "\n".join(lines)
        text += "\nВведите номер предмета (0 - выход)"
    await message.answer(
        text,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Назад")]], resize_keyboard=True
        ),
    )


@router.message(F.text == "Отдых")
async def rest_character(message: Message):
    db: Database = message.bot.db
    party_ids = await db.party.get_party(message.from_user.id, message.chat.id)
    if not party_ids:
        await message.answer("Сначала сформируйте отряд.", reply_markup=main_menu())
        return
    chars = await db.characters.get_characters(message.from_user.id, message.chat.id)
    id_map = {c.db_id: c for c in chars}
    for cid in party_ids:
        pc = id_map.get(cid)
        if not pc:
            continue
        pc.health = pc.max_health
        pc.mana = pc.base_mana
        await db.characters.update_character(pc, message.chat.id)
    await message.answer("Отряд отдохнул и восстановлен.", reply_markup=main_menu())


@router.message(F.text == "Персонажи")
async def list_characters(message: Message):
    db: Database = message.bot.db
    chars = await db.characters.get_characters(message.from_user.id, message.chat.id)
    if not chars:
        text = "У вас нет персонажей."
    else:
        lines = [
            f"{i+1}. {c.name} (lvl {c.level}, HP {c.health}/{c.max_health})"
            for i, c in enumerate(chars)
        ]
        text = "Ваши персонажи:\n" + "\n".join(lines)
    await message.answer(text, reply_markup=chars_menu())


@router.message(F.text == "Отряд")
async def manage_party(message: Message):
    db: Database = message.bot.db
    chars = await db.characters.get_characters(message.from_user.id, message.chat.id)
    if not chars:
        await message.answer("Сначала создайте персонажей.", reply_markup=chars_menu())
        return
    current = await db.party.get_party(message.from_user.id, message.chat.id)
    party_select[(message.from_user.id, message.chat.id)] = current.copy()
    await show_party_selection(message, chars, current)


async def show_party_selection(message: Message, chars, selected):
    buttons = []
    for i, c in enumerate(chars):
        mark = "✓" if c.db_id in selected else " "
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"[{mark}] {c.name}", callback_data=f"toggle:{c.db_id}"
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="Готово", callback_data="party_save")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите до 3 героев:", reply_markup=kb)


@router.message(F.text == "Создать персонажа")
async def choose_class(message: Message):
    buttons = [
        [InlineKeyboardButton(text=cls.display_name, callback_data=f"new:{cls.name}")]
        for cls in CharacterClass
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите класс:", reply_markup=kb)


@router.callback_query(F.data.startswith("new:"))
async def create_character_callback(query):
    db: Database = query.message.bot.db
    cls_name = query.data.split(":", 1)[1]
    pc = await db.characters.add_character(
        query.from_user.id, query.message.chat.id, name="Hero", class_name=cls_name
    )
    await query.message.answer(
        f"Создан персонаж {pc.name} класса {CharacterClass[cls_name].display_name}"
    )
    await query.message.answer("Главное меню", reply_markup=main_menu())
    await query.answer()


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_party_member(query: CallbackQuery):
    db: Database = query.message.bot.db
    char_id = int(query.data.split(":", 1)[1])
    chars = await db.characters.get_characters(
        query.from_user.id, query.message.chat.id
    )
    key = (query.from_user.id, query.message.chat.id)
    current = party_select.get(key, [])
    if char_id in current:
        current.remove(char_id)
    else:
        if len(current) >= 3:
            await query.answer("Максимум 3 героя", show_alert=True)
            return
        current.append(char_id)
    party_select[key] = current
    await show_party_selection(query.message, chars, current)
    await query.answer()


@router.callback_query(F.data == "party_save")
async def save_party(query: CallbackQuery):
    key = (query.from_user.id, query.message.chat.id)
    selected = party_select.get(key, [])
    await query.message.bot.db.party.set_party(key[0], key[1], selected)
    await query.message.answer("Отряд сохранён.", reply_markup=chars_menu())
    await query.answer()


@router.message(F.text == "Бой")
async def start_battle(message: Message):
    db: Database = message.bot.db
    party_ids = await db.party.get_party(message.from_user.id, message.chat.id)
    if not party_ids:
        await message.answer("Сначала сформируйте отряд.", reply_markup=main_menu())
        return
    chars = await db.characters.get_characters(message.from_user.id, message.chat.id)
    id_map = {c.db_id: c for c in chars}
    party = [id_map[cid] for cid in party_ids if cid in id_map]
    if not party:
        await message.answer("Ошибка отряда.", reply_markup=main_menu())
        return
    owner = await db.users.get_user(message.from_user.id, message.chat.id)
    for pc in party:
        pc.owner = owner

    pending_battles[(message.from_user.id, message.chat.id)] = party

    tiers = CONFIG["monsters"]["monster_tiers"]
    tier_keys = ["tier1", "tier2", "tier3", "tier4"]
    buttons = [
        [InlineKeyboardButton(text=tiers[k]["name"], callback_data=f"battle:{i+1}")]
        for i, k in enumerate(tier_keys)
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите сложность боя:", reply_markup=kb)


@router.callback_query(F.data.startswith("battle:"))
async def handle_battle_callback(query: CallbackQuery):
    tier = int(query.data.split(":", 1)[1])
    key = (query.from_user.id, query.message.chat.id)
    party = pending_battles.pop(key, None)
    if not party:
        await query.message.answer("Ошибка: отряд не найден.", reply_markup=main_menu())
        await query.answer()
        return

    log, win, xp, gold = simulate_battle(party, tier)
    db: Database = query.message.bot.db
    for pc in party:
        await db.characters.update_character(pc, query.message.chat.id)
    owner = party[0].owner
    if owner:
        await db.users.update_user(owner, query.message.chat.id)

    await query.message.answer(
        f"Результат боя:\n<pre>{log}</pre>",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
    await query.answer()


@router.message(F.text == "Магазин")
async def show_shop(message: Message):
    db: Database = message.bot.db
    user = await db.users.get_user(message.from_user.id, message.chat.id)
    goods = store.available_potions() + store.available_gear()
    active_shops[(message.from_user.id, message.chat.id)] = goods
    lines = [f"{i+1}. {g.name} — {g.price}g" for i, g in enumerate(goods)]
    text = (
        f"Ваше золото: {user.gold if user else 0}g\n"
        "Введите номер товара для покупки, 0 — выход:\n" + "\n".join(lines)
    )
    await message.answer(text)


@router.message(lambda m: m.text and m.text.isdigit())
async def handle_numeric_reply(message: Message):
    key = (message.from_user.id, message.chat.id)
    # --- Магазин ---
    goods = active_shops.get(key)
    if goods is not None:
        choice = int(message.text)
        if choice == 0:
            active_shops.pop(key, None)
            await message.answer("Вы вышли из магазина.", reply_markup=main_menu())
            return
        index = choice - 1
        if index < 0 or index >= len(goods):
            await message.answer("Неверный номер")
            return
        item = goods[index]
        db: Database = message.bot.db
        user = await db.users.get_user(message.from_user.id, message.chat.id)
        if not user or not user.spend_gold(item.price):
            await message.answer("Недостаточно золота")
            return
        await db.users.update_user(user, message.chat.id)
        await db.inventory.add_item(user.id, message.chat.id, item)
        await message.answer(f"Куплено: {item.name}")
        return

    # --- Инвентарь ---
    items = active_inventories.get(key)
    if items is None:
        return
    choice = int(message.text)
    if choice == 0:
        active_inventories.pop(key, None)
        await message.answer("Вы вышли из инвентаря.", reply_markup=main_menu())
        return
    index = choice - 1
    if index < 0 or index >= len(items):
        await message.answer("Неверный номер")
        return
    item = items[index]
    db: Database = message.bot.db
    chars = await db.characters.get_characters(message.from_user.id, message.chat.id)
    if not chars:
        await message.answer("Нет персонажей")
        return
    pc = chars[0]
    if isinstance(item, GearItem):
        pc.equip_item(item)
    else:
        pc.consume_potion(item)
    await db.characters.update_character(pc, message.chat.id)
    await db.inventory.remove_item(item.db_id, message.chat.id)
    await message.answer(f"Использовано: {item.name}")

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

router = Router()
# Отбираем только личные чаты
router.message.filter(F.chat.type == ChatType.PRIVATE)


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
    await message.answer("Главное меню", reply_markup=main_menu())


@router.message(F.text == "Инвентарь")
async def show_inventory(message: Message):
    db: Database = message.bot.db
    items = await db.inventory.get_items(message.from_user.id, message.chat.id)
    if not items:
        text = "Инвентарь пуст."
    else:
        lines = [f"{i+1}. {it.name}" for i, it in enumerate(items)]
        text = "Ваш инвентарь:\n" + "\n".join(lines)
    await message.answer(
        text,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Назад")]], resize_keyboard=True
        ),
    )


@router.message(F.text == "Отдых")
async def rest_character(message: Message):
    db: Database = message.bot.db
    chars = await db.characters.get_characters(message.from_user.id, message.chat.id)
    if not chars:
        await message.answer("Сначала создайте персонажа.", reply_markup=main_menu())
        return
    pc = chars[0]
    pc.health = pc.max_health
    pc.mana = pc.base_mana
    await db.characters.update_character(pc, message.chat.id)
    await message.answer(f"{pc.name} полностью восстановлен.", reply_markup=main_menu())


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


@router.message(F.text == "Бой")
async def start_battle(message: Message):
    db: Database = message.bot.db
    chars = await db.characters.get_characters(message.from_user.id, message.chat.id)
    if not chars:
        await message.answer("Сначала создайте персонажа.", reply_markup=main_menu())
        return
    pc = chars[0]
    pc.owner = await db.users.get_user(message.from_user.id, message.chat.id)
    log, win, xp, gold = simulate_battle(pc, tier=1)
    await db.characters.update_character(pc, message.chat.id)
    await db.users.update_user(pc.owner, message.chat.id)
    await message.answer(
        f"Результат боя:\n<pre>{log}</pre>",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.message(F.text == "Магазин")
async def show_shop(message: Message):
    db: Database = message.bot.db
    user = await db.users.get_user(message.from_user.id, message.chat.id)
    goods = store.available_potions() + store.available_gear()
    lines = [f"{i+1}. {g.name} — {g.price}g" for i, g in enumerate(goods)]
    buttons = [
        [InlineKeyboardButton(text=f"Купить {i+1}", callback_data=f"buy:{i}")]
        for i in range(len(goods))
    ]
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="shop_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = f"Ваше золото: {user.gold if user else 0}g\nДоступно:\n" + "\n".join(lines)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("buy:"))
async def buy_item(query: CallbackQuery):
    db: Database = query.message.bot.db
    index = int(query.data.split(":", 1)[1])
    goods = store.available_potions() + store.available_gear()
    if index < 0 or index >= len(goods):
        await query.answer("Ошибка", show_alert=True)
        return
    item = goods[index]
    user = await db.users.get_user(query.from_user.id, query.message.chat.id)
    if not user or not user.spend_gold(item.price):
        await query.answer("Недостаточно золота", show_alert=True)
        return
    await db.users.update_user(user, query.message.chat.id)
    await db.inventory.add_item(user.id, query.message.chat.id, item)
    await query.answer(f"Куплено: {item.name}", show_alert=True)


@router.callback_query(F.data == "shop_back")
async def shop_back(query: CallbackQuery):
    await query.message.answer("Главное меню", reply_markup=main_menu())
    await query.answer()

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from my_game.items.item import GearItem


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="🏪 Магазин")],
            [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛌 Отдых")],
            [KeyboardButton(text="⚔ Бой")],
        ],
        resize_keyboard=True,
    )


def chars_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать персонажа")],
            [KeyboardButton(text="👥 Отряд")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def shop_keyboard(goods) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{i+1}. {g.name} — {g.price}g", callback_data=f"shop:{i}"
            )
        ]
        for i, g in enumerate(goods)
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="shop_exit")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def inventory_keyboard(items) -> InlineKeyboardMarkup:
    labels = []
    for i, it in enumerate(items):
        if isinstance(it, GearItem):
            labels.append(f"{i+1}. {it.name} ({it.slot.name})")
        else:
            desc = []
            if it.heal:
                desc.append(f"HP+{it.heal}")
            if it.mana:
                desc.append(f"MP+{it.mana}")
            labels.append(f"{i+1}. {it.name} ({', '.join(desc)})")
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"inv:{i}")]
        for i, label in enumerate(labels)
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="inv_exit")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

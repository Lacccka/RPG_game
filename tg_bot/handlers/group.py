from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message

router = Router()
# Только групповые чаты
router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))


@router.message()
async def group_placeholder(message: Message):
    await message.answer("Групповой режим в разработке.")

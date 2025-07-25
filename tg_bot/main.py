import sys, os, asyncio
from pathlib import Path
from dotenv import load_dotenv

# 0) определяем корень проекта и путь к src
BASE_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = BASE_DIR / "src"

# 1) кладём src в sys.path, чтобы Python увидел пакет my_game
sys.path.insert(0, str(SRC_DIR))

# 2) теперь подгружаем .env
load_dotenv(dotenv_path=BASE_DIR / ".env")

# 3) остальные импорты идут уже после правки sys.path
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties

from tg_bot.repositories.db import Database
from tg_bot.handlers import private, group


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env variable not set")
    async with Database("bot.db") as db:
        bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        bot.db = db
        dp = Dispatcher()
        dp.include_router(private.router)
        dp.include_router(group.router)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

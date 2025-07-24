import random
import logging
from typing import List

from ..config import CONFIG
from ..monsters.monster import Monster

logger = logging.getLogger(__name__)


def generate_enemies_for_tier(tier: int) -> List[Monster]:
    """
    Генерирует группу из 1–3 врагов для заданного тира.

    1. Берёт список имён из CONFIG["monsters"]["monster_tiers"]["tier{tier}"]["monsters"].
    2. Для каждого выбирает уровень в диапазоне [1..tier].
    3. Создаёт экземпляр через Monster.from_config().
    """
    # 1) Сколько врагов выпадет
    count = random.randint(1, 3)

    # 2) Достаём информацию о тирах
    tier_key = f"tier{tier}"
    tiers_cfg = CONFIG["monsters"].get("monster_tiers", {})
    tier_info = tiers_cfg.get(tier_key)
    if not tier_info:
        logger.error("Нет секции monster_tiers['%s'] в конфиге", tier_key)
        raise ValueError(f"Не найдена конфигурация для тира '{tier_key}'")

    names = tier_info.get("monsters", [])
    if not names:
        logger.error("Список MONSTERS пуст для секции '%s'", tier_key)
        raise ValueError(f"В конфиге monster_tiers['{tier_key}']['monsters'] пуст")

    # 3) Собираем список врагов
    enemies: List[Monster] = []
    for _ in range(count):
        monster_name = random.choice(names)
        level = random.randint(1, tier)
        m = Monster.from_config(monster_name, level)
        enemies.append(m)

    return enemies


def generate_monster(pc_level: int) -> Monster:
    """
    Берёт случайный шаблон из всех CONFIG["monsters"]["templates"],
    задаёт уровень в диапазоне [pc_level-1 .. pc_level+1] (не ниже 1)
    и создаёт через Monster.from_config().
    """
    templates = list(CONFIG["monsters"]["templates"].keys())
    if not templates:
        logger.error("CONFIG['monsters']['templates'] пуст")
        raise ValueError("Нет доступных шаблонов монстров в конфиге")

    mt_name = random.choice(templates)
    lvl = random.randint(max(pc_level - 1, 1), pc_level + 1)

    return Monster.from_config(mt_name, lvl)

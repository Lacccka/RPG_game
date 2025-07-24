import sys
import random
from typing import Callable, Sequence, TypeVar, Tuple, List

from ..config import CONFIG
from ..monsters.monster import Monster
from ..characters.player_character import PlayerCharacter
from .monster_utils import generate_enemies_for_tier  # <-- импортируем

T = TypeVar("T")


def prompt_int(prompt: str, default: int | None = None) -> int:
    raw = input(f"{prompt}{f' [{default}]' if default is not None else ''}: ").strip()
    if not raw:
        if default is not None:
            return default
        raise ValueError("Пустой ввод")
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Ожидалось число, получили {raw!r}")


def prompt_str(prompt: str, allow_empty: bool = False) -> str:
    s = input(f"{prompt}: ").strip()
    if not s and not allow_empty:
        raise ValueError("Пустая строка недопустима")
    return s


def choose_from_list(
    items: Sequence[T], display_fn: Callable[[T], str], prompt: str
) -> T:
    print(prompt)
    for i, item in enumerate(items, start=1):
        print(f" {i}. {display_fn(item)}")
    raw = input(f"Выберите [1–{len(items)}] (default=1): ").strip()
    try:
        idx = int(raw)
        if 1 <= idx <= len(items):
            return items[idx - 1]
    except Exception:
        pass
    return items[0]


def exit_program():
    print("👋 До свидания!")
    sys.exit(0)


def choose_monsters_for_battle(
    player_char: PlayerCharacter,
) -> Tuple[List[Monster], int]:
    """
    Возвращает кортеж (enemies, tier), где enemies — список из 1–3 Monster,
    а tier — число от 1 до 4.
    """
    # --- Выбираем сложность (тир) ---
    tiers_conf = CONFIG["monsters"]["monster_tiers"]
    tier_keys = ["tier1", "tier2", "tier3", "tier4"]

    selected_tier = choose_from_list(
        tier_keys,
        display_fn=lambda t: f"{tiers_conf[t]['name']} — {tiers_conf[t]['description']}",
        prompt="Выберите сложность боя",
    )
    tier = tier_keys.index(selected_tier) + 1

    # --- Генерируем 1–3 врага по тиру ---
    enemies = generate_enemies_for_tier(tier)

    # --- Выводим в консоль информацию о сгенерированных врагах ---
    print(f"\n⚔️ Бой (тир {tier} — {tiers_conf[selected_tier]['name']}):")
    for e in enemies:
        print(
            f"  • {e.name.capitalize()} (ур. {e.level}) — HP {e.health}/{e.max_health}"
        )

    return enemies, tier

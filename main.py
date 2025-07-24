#!/usr/bin/env python3
import sys
import os
from random import random
from typing import Dict

# Добавляем src/ в PYTHONPATH, чтобы пакеты my_game были доступны
here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(here, "src"))

from my_game.characters.player import Player
from my_game.characters.character_class import CharacterClass
from my_game.characters.player_character import PlayerCharacter
from my_game.utils.cli_utils import (
    prompt_int,
    prompt_str,
    choose_from_list,
    exit_program,
)
from my_game.utils.monster_utils import generate_enemies_for_tier
from my_game.battle.dispatcher import take_turn as ai_take_turn
from my_game.config import CONFIG

# Хранилище игроков: id → Player
players: Dict[int, Player] = {}


def create_player():
    try:
        pid = prompt_int("Введите ID нового игрока", None)
        if pid in players:
            print(f"❌ Игрок с ID={pid} уже существует.")
            return
        name = prompt_str("Введите имя игрока")
    except ValueError as e:
        print("❌", e)
        return

    players[pid] = Player(id=pid, username=name)
    print(f"✅ Игрок {name!r} создан (ID={pid}).")


def create_character():
    try:
        pid = prompt_int("Введите ID игрока")
        player = players[pid]
        # char_name = prompt_str("Введите имя персонажа")
        char_name = "Leon"
    except (ValueError, KeyError) as e:
        print("❌", e)
        return

    cls = choose_from_list(
        list(CharacterClass),
        lambda c: (
            f"{c.name} — {c.display_name} "
            f"(HP={c.base_health}, STR={c.base_strength}, "
            f"AGI={c.base_agility}, INT={c.base_intelligence})"
        ),
        "Доступные классы:",
    )

    pc = player.create_character(char_name, cls)
    print(
        f"✅ Персонаж {pc.name!r} создан: класс {cls.display_name}, "
        f"HP={pc.health}, STR={pc.strength}, AGI={pc.agility}, INT={pc.intelligence}."
    )


def list_characters():
    try:
        pid = prompt_int("Введите ID игрока")
        player = players[pid]
    except (ValueError, KeyError) as e:
        print("❌", e)
        return

    if not player.characters:
        print("ℹ️ У этого игрока нет персонажей.")
        return

    print(f"Персонажи игрока {player.username!r} (ID={pid}):")
    for pc in player.characters:
        status = "жив" if pc.is_alive else "повержен"
        exp_next = pc.exp_to_next()
        print(
            f" • {pc.name:15s} | {pc.char_class.name:<7s} | lvl {pc.level:<2d} | "
            f"HP {pc.health:<3d}/{pc.max_health:<3d} | "
            f"STR {pc.strength:<2d} | AGI {pc.agility:<2d} | "
            f"INT {pc.intelligence:<2d} | "
            f"EXP {pc.exp}/{exp_next} | {status}"
        )


def rest():
    try:
        pid = prompt_int("Введите ID игрока")
        player = players[pid]
        if not player.characters:
            raise ValueError("У этого игрока нет персонажей.")
    except (ValueError, KeyError) as e:
        print("❌", e)
        return

    pc = choose_from_list(
        player.characters,
        lambda c: f"{c.name} (HP {c.health}/{c.max_health})",
        "Кого отправить отдыхать?",
    )
    pc.health = pc.max_health
    pc.mana = pc.base_mana
    print(f"💤 {pc.name} полностью восстановлен: HP={pc.health}/{pc.max_health}.")


def fight():
    try:
        pid = prompt_int("Введите ID игрока")
        player = players[pid]
        if not player.characters:
            raise ValueError("У игрока нет персонажей для боя.")
    except (ValueError, KeyError) as e:
        print("❌", e)
        return

    # Выбираем героя
    pc = choose_from_list(
        player.characters,
        lambda c: f"{c.name} (lvl {c.level}, HP {c.health}/{c.max_health})",
        "Доступные персонажи:",
    )

    # Выбираем тир и генерируем группу монстров
    tiers = CONFIG["monsters"]["monster_tiers"]
    tier_keys = ["tier1", "tier2", "tier3", "tier4"]
    sel = choose_from_list(
        tier_keys,
        display_fn=lambda t: f"{tiers[t]['name']} — {tiers[t]['description']}",
        prompt="Выберите сложность боя",
    )
    tier = tier_keys.index(sel) + 1
    enemies = generate_enemies_for_tier(tier)

    participants = [pc] + enemies
    print(f"\n⚔️  Начало боя (тир {tier} — {tiers[sel]['name']})")
    for e in enemies:
        print(f"   • {e.name} (ур. {e.level}) — HP {e.health}/{e.max_health}")
    print(f"🔹 {pc.name} (lvl {pc.level}) — HP {pc.health}/{pc.max_health}\n")

    round_num = 1
    while pc.is_alive and any(m.is_alive for m in enemies):
        print(f"=== Раунд {round_num} ===")
        # Сортируем по инициативе: agility + немного случайности
        order = [p for p in participants if p.is_alive]
        order.sort(key=lambda x: x.agility + random() * 0.1, reverse=True)

        for actor in order:
            if isinstance(actor, PlayerCharacter):
                ai_take_turn(actor, [m for m in enemies if m.is_alive])
            else:
                ai_take_turn(actor, pc)

            if not pc.is_alive or not any(m.is_alive for m in enemies):
                break

        round_num += 1
        print()

    # Итог
    if pc.is_alive:
        base = CONFIG["growth"]["xp_rewards"][f"tier{tier}"]
        count = len(enemies)
        reward = base * count * 1.2 if count > 1 else base
        pc.add_exp(reward)
        print(f"🎉 Победа! {pc.name!r} получает {reward} XP")
    else:
        print(f"☠️  Поражение... {pc.name!r} пал в бою.")


def main():
    actions = {
        "1": ("Создать игрока", create_player),
        "2": ("Создать персонажа", create_character),
        "3": ("Показать персонажей", list_characters),
        "4": ("Бой с монстрами", fight),
        "5": ("Отдохнуть", rest),
        "6": ("Выход", exit_program),
    }

    while True:
        print("\n=== Главное меню ===")
        for key, (desc, _) in actions.items():
            print(f"{key}. {desc}")
        choice = input("Выберите действие: ").strip()
        action = actions.get(choice)
        if action:
            action[1]()
        else:
            print("❌ Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import sys
import os
import random
import io
import contextlib
from collections import Counter, defaultdict

# Добавляем src/ в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from my_game.characters.player import Player
from my_game.characters.character_class import CharacterClass
from my_game.monsters.monster import Monster
from my_game.battle.dispatcher import take_turn
from my_game.config import CONFIG


def simulate_group_battle(pc, monsters, tier):
    """Симуляция группового боя. Возвращает (win: bool, remaining_hp: int)."""
    # Полное восстановление
    pc.health = pc.max_health
    if hasattr(pc, "mana"):
        pc.mana = pc.base_mana
    for m in monsters:
        m.health = m.max_health

    # Глушим боевой лог
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        participants = [pc] + monsters
        while pc.is_alive and any(m.is_alive for m in monsters):
            # Порядок хода: по ловкости + чуть случайности
            participants.sort(
                key=lambda x: x.agility + random.random() * 0.1, reverse=True
            )
            for actor in participants:
                if not actor.is_alive:
                    continue
                if actor == pc:
                    targets = [m for m in monsters if m.is_alive]
                    if targets:
                        take_turn(pc, targets)
                else:
                    take_turn(actor, pc)
                if not pc.is_alive or not any(m.is_alive for m in monsters):
                    break

        win = pc.is_alive
        xp = CONFIG["growth"]["xp_rewards"][f"tier{tier}"]
        pc.add_exp(xp if win else xp // 2)

    buf.close()
    return win, pc.health


def run_trials(
    hero,
    tier=3,
    trials=1000,
    group_min=1,
    group_max=3,
):
    """Запускает серию боёв и возвращает словарь со статистикой."""
    # Выбираем список монстров нужного тира
    tier_key = f"tier{tier}"
    tier_list = CONFIG["monsters"]["monster_tiers"][tier_key]["monsters"]

    results = Counter()
    hps_after = []
    wins_by_group = defaultdict(int)
    total_monsters = 0
    group_sizes = []

    current_streak = 0
    max_streak = 0
    max_streak_start = 0
    streak_start = 1
    streak_start_level = hero.level
    max_streak_level = hero.level

    for i in range(1, trials + 1):
        group_size = random.randint(group_min, group_max)
        group_types = tuple(sorted(random.choices(tier_list, k=group_size)))
        group_sizes.append(group_size)
        total_monsters += group_size

        # Можно варьировать уровень монстров относительно героя
        monsters = [Monster.from_config(t, level=hero.level + 4) for t in group_types]

        win, hp_after = simulate_group_battle(hero, monsters, tier=tier)

        results["wins" if win else "losses"] += 1
        hps_after.append(hp_after)
        if win:
            wins_by_group[group_types] += 1

        if win:
            if current_streak == 0:
                streak_start = i
                streak_start_level = hero.level
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
                max_streak_start = streak_start
                max_streak_level = streak_start_level
        else:
            current_streak = 0

    total = results["wins"] + results["losses"]
    win_rate = results["wins"] / total * 100 if total else 0
    avg_hp = sum(hps_after) / len(hps_after) if hps_after else 0
    avg_group_size = sum(group_sizes) / len(group_sizes) if group_sizes else 0

    stats = {
        "tier": tier,
        "trials": total,
        "wins": results["wins"],
        "losses": results["losses"],
        "win_rate": win_rate,
        "avg_hp_after": avg_hp,
        "hero_max_hp": hero.max_health,
        "avg_group_size": avg_group_size,
        "total_monsters": total_monsters,
        "max_streak": max_streak,
        "max_streak_start_battle": max_streak_start,
        "max_streak_start_level": max_streak_level,
        "wins_by_group": dict(wins_by_group),
    }
    return stats


def format_stats_text(stats):
    """Готовит текстовый отчёт."""
    lines = []
    lines.append(
        f"=== 📊 Общая статистика (tier {stats['tier']}, группа 1-3 монстра) ==="
    )
    lines.append(f"Всего боёв: {stats['trials']}")
    lines.append(
        f"Побед: {stats['wins']}, поражений: {stats['losses']} ({stats['win_rate']:.1f}%)"
    )
    lines.append(
        f"Среднее HP после боя: {stats['avg_hp_after']:.1f}/{stats['hero_max_hp']}"
    )
    lines.append(f"Средний размер группы врагов: {stats['avg_group_size']:.2f}")
    lines.append(f"Всего врагов встречено: {stats['total_monsters']}")
    lines.append(
        f"Самая длинная полоса побед: {stats['max_streak']} боёв "
        f"(началась с боя #{stats['max_streak_start_battle']}, уровень {stats['max_streak_start_level']})"
    )

    lines.append("\n=== 🧟 Победы по составам групп ===")
    # сортируем по количеству побед (убывание)
    for group, count in sorted(stats["wins_by_group"].items(), key=lambda x: -x[1]):
        group_str = ", ".join(group)
        lines.append(f"{group_str}: {count} побед")

    return "\n".join(lines)


def main(output_path="stats.txt", print_to_stdout=True):
    random.seed(random.randint(0, 1000))

    player = Player(id=1, username="Tester")
    hero = player.create_character("Leon", CharacterClass.ROGUE)

    stats = run_trials(hero, tier=4, trials=1000, group_min=1, group_max=3)
    text = format_stats_text(stats)

    # Запись в файл
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
        f.write("\n")

    if print_to_stdout:
        print(text)
        print(f"\nРезультаты сохранены в: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()

    # python -m src.test.test_warrior_vs_bosses
    # python -m src.test.test_warrior_vs_bosses -o tier4_stats.txt

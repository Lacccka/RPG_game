from __future__ import annotations
import io
import contextlib
from random import random
from typing import Tuple

from my_game.characters.player_character import PlayerCharacter
from my_game.utils.monster_utils import generate_enemies_for_tier
from my_game.battle.dispatcher import take_turn as ai_take_turn
from my_game.config import CONFIG
from my_game.items.store import Store


store = Store()


def simulate_battle(pc: PlayerCharacter, tier: int) -> Tuple[str, bool, int, int]:
    """Run battle and return (log, win, xp, gold)."""
    enemies = generate_enemies_for_tier(tier)
    participants = [pc] + enemies
    tiers = CONFIG["monsters"]["monster_tiers"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(f"\n⚔️  Начало боя (тир {tier} — {tiers[f'tier{tier}']['name']})")
        for e in enemies:
            print(f"   • {e.name} (ур. {e.level}) — HP {e.health}/{e.max_health}")
        print(f"🔹 {pc.name} (lvl {pc.level}) — HP {pc.health}/{pc.max_health}\n")
        round_num = 1
        while pc.is_alive and any(m.is_alive for m in enemies):
            print(f"=== Раунд {round_num} ===")
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
        if pc.is_alive:
            base = CONFIG["growth"]["xp_rewards"][f"tier{tier}"]
            count = len(enemies)
            reward = base * count * 1.2 if count > 1 else base
            pc.add_exp(reward)
            gold = int(reward // 10)
            if pc.owner:
                pc.owner.add_gold(gold)
            print(f"🎉 Победа! {pc.name!r} получает {reward} XP и {gold} золота")
            win = True
        else:
            win = False
            reward = gold = 0
            print(f"☠️  Поражение... {pc.name!r} пал в бою.")
    log = buf.getvalue()
    buf.close()
    return log, win, reward, gold

from __future__ import annotations
import io
import contextlib
import random
from typing import Tuple
from typing import Sequence

from my_game.characters.player_character import PlayerCharacter
from my_game.utils.monster_utils import generate_enemies_for_tier
from my_game.battle.dispatcher import take_turn as ai_take_turn
from my_game.config import CONFIG
from my_game.items.store import Store


store = Store()


def simulate_battle(
    party: Sequence[PlayerCharacter], tier: int
) -> Tuple[str, bool, int, int]:
    """Run battle for a party and return (log, win, xp, gold)."""
    if not party:
        raise ValueError("Party cannot be empty")
    enemies = generate_enemies_for_tier(tier)
    participants = list(party) + enemies

    for pc in party:
        pc.team = party
    for m in enemies:
        m.team = enemies

    tiers = CONFIG["monsters"]["monster_tiers"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(f"\n⚔️  Начало боя (тир {tier} — {tiers[f'tier{tier}']['name']})")
        for e in enemies:
            print(f"   • {e.name} (ур. {e.level}) — HP {e.health}/{e.max_health}")
        for hero in party:
            print(
                f"🔹 {hero.name} (lvl {hero.level}) — HP {hero.health}/{hero.max_health}"
            )
        print()
        round_num = 1
        while any(h.is_alive for h in party) and any(m.is_alive for m in enemies):
            print(f"=== Раунд {round_num} ===")
            order = [p for p in participants if p.is_alive]
            order.sort(key=lambda x: x.agility + random.random() * 0.1, reverse=True)
            for actor in order:
                if actor in party:
                    ai_take_turn(actor, [m for m in enemies if m.is_alive])
                else:
                    targets = [h for h in party if h.is_alive]
                    if not targets:
                        break
                    target = random.choice(targets)
                    ai_take_turn(actor, target)

                if not any(h.is_alive for h in party) or not any(
                    m.is_alive for m in enemies
                ):
                    break
            round_num += 1
            print()
        win = any(h.is_alive for h in party)
        if win:
            base = CONFIG["growth"]["xp_rewards"][f"tier{tier}"]
            count = len(enemies)
            reward = base * count * 1.2 if count > 1 else base
            for hero in party:
                hero.add_exp(reward)
            gold = int(reward // 10)
            owner = party[0].owner
            if owner:
                owner.add_gold(gold)
            print(f"🎉 Победа! Отряд получает {reward} XP и {gold} золота")
        else:
            reward = gold = 0
            print("☠️  Отряд пал в бою.")
    log = buf.getvalue()
    buf.close()
    return log, win, reward, gold

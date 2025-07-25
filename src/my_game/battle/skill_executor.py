# src/my_game/battle/skill_executor.py

import random
from typing import List, Union, Sequence, Optional
from my_game.battle.enums import Element, DamageSource, CritType
from my_game.battle.damage import calc_damage, check_hit
from my_game.battle.status import before_action
from my_game.config import CONFIG
from my_game.base.combatant import Combatant


class TargetSelector:
    def __init__(
        self,
        user: Combatant,
        enemies: Sequence[Combatant],
        allies: Optional[Sequence[Combatant]] = None,
    ):
        self.user = user
        self.enemies = list(enemies)
        self.allies = list(allies) if allies is not None else user.get_allies()

    def collect(
        self,
        mode: str,
        chosen: Union[Combatant, Sequence[Combatant], None],
        fallback: Combatant,
    ) -> List[Combatant]:
        if isinstance(chosen, Combatant):
            chosen_list = [chosen]
        elif isinstance(chosen, Sequence):
            chosen_list = [c for c in chosen if isinstance(c, Combatant)]
        else:
            chosen_list = []

        if mode in ("enemy", "single_target"):
            return chosen_list or [fallback]
        if mode == "all_enemies":
            return self.enemies
        if mode == "two_random_enemies":
            cnt = min(2, len(self.enemies))
            return random.sample(self.enemies, cnt)
        if mode == "team":
            return self.allies
        if mode == "ally":
            return chosen_list or [self.user]
        if mode == "self":
            return [self.user]

        # fallback
        return chosen_list or [fallback]


def execute_skill(
    user: Combatant,
    targets: Union[Combatant, Sequence[Combatant]],
    skill_name: str,
) -> None:
    # normalize targets to list
    if isinstance(targets, Combatant):
        targets = [targets]
    else:
        targets = [t for t in targets if isinstance(t, Combatant)]

    visible = getattr(user, "_visible_enemies", targets)
    allowed = before_action(user, visible)
    if not allowed:
        return
    targets = [t for t in targets if t in allowed] or allowed

    cfg = CONFIG["skills"][skill_name]
    mana_cost = cfg.get("mana_cost", cfg.get("cost", {}).get("mana", 0))
    # 1) тратим ману
    if mana_cost and hasattr(user, "mana"):
        user.mana = max(user.mana - mana_cost, 0)
        print(f"{user.name} тратит {mana_cost} маны (осталось {user.mana}).")

    kind = cfg["type"]
    if kind == "damage":
        _exec_damage(user, targets, skill_name, cfg)
    elif kind in ("buff", "debuff"):
        _exec_buff_debuff(user, targets, skill_name, cfg)
    elif kind == "utility":
        _exec_utility(user, targets, skill_name, cfg)
    else:
        raise ValueError(f"Unknown skill type {kind!r} for {skill_name!r}")

    # 3) ставим кулдаун
    cd = cfg.get("cooldown", 0)
    if cd:
        user.cooldowns[skill_name] = cd


def _apply_effect(tgt: Combatant, cfg: dict) -> None:
    payload = {"effect": cfg["effect"]}
    if "duration" in cfg:
        payload["duration"] = cfg["duration"]
    if "power" in cfg:
        payload["power"] = cfg["power"]
    tgt.apply_effect(payload)


def _exec_damage(user, targets, skill_name, cfg):
    success_chance = cfg.get("success_chance", 1.0)
    power = cfg.get("power", 1.0)
    elem = Element[cfg.get("element", "PHYSICAL")]

    for tgt in targets:
        if random.random() > success_chance:
            print(
                f"{user.name} пытается {skill_name}, но не удаётся! (шанс {success_chance:.0%})"
            )
            continue
        if not check_hit(user, tgt):
            print(
                f"{user.name} использует {skill_name}, но промахивается! (шанс {user._last_hit:.1%})"
            )
            continue

        # Heavy‑крит только для навыков с триггером if_first / if_enemy_low_hp
        trig = cfg.get("trigger", "")
        if trig in ("if_first", "if_enemy_low_hp"):
            crit = CritType.HEAVY
        else:
            crit = CritType.NORMAL

        base = calc_damage(
            user,
            tgt,
            element=elem,
            source=DamageSource.NORMAL,
            crit_type=crit,
            power=power,
        )
        dmg = int(base)
        print(f"{user.name} использует {skill_name}! Наносит {dmg} урона.")
        tgt.take_damage(dmg)

        if cfg.get("effect") and tgt.is_alive:
            _apply_effect(tgt, cfg)


def _exec_buff_debuff(user, targets, skill_name, cfg):
    print(f"{user.name} использует {skill_name}!")
    for tgt in targets:
        _apply_effect(tgt, cfg)
    if cfg.get("effect") == "steal_intelligence":
        recover = int(
            user.base_mana
            * CONFIG["battle_rules"]["status_effects"]["steal_intelligence"][
                "mana_recover"
            ]
        )
        user.mana = min(user.base_mana, user.mana + recover)
        print(
            f"{user.name} восстанавливает {recover} маны от {skill_name}! (теперь {user.mana})"
        )


def _exec_utility(user, targets, skill_name, cfg):
    print(f"{user.name} использует {skill_name}!")
    eff = cfg.get("effect")
    if eff == "extra_turn":
        user.apply_effect({"effect": "extra_turn", "duration": cfg.get("duration", 1)})
    else:
        _apply_effect(user if cfg.get("target") == "self" else targets[0], cfg)

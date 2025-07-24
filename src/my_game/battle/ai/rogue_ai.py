# src/my_game/battle/ai/rogue_ai.py

import logging
from typing import Tuple, Union, List, Optional
from random import sample

from my_game.battle.ai.base_ai import BaseAI
from my_game.base.combatant import Combatant
from my_game.config import CONFIG

logger = logging.getLogger(__name__)


def base_dps(enemy: Combatant) -> float:
    """Приблизительный DPS врага по конфигу."""
    return CONFIG["monsters"]["base_damage"].get(enemy.name, 0.0)


def pick_target(
    skill: str,
    enemies: List[Combatant],
    user: Combatant,
    primary: Combatant,
) -> Combatant:
    """Выбор цели для конкретного навыка."""
    if not enemies:
        return primary

    poisoned = getattr(user, "_poison_mark", None)

    if skill == "Assassinate":
        power = CONFIG["skills"]["Assassinate"]["power"]
        est = user.strength * power
        low = [e for e in enemies if e.health < est * 0.9]
        if low:
            return min(low, key=lambda e: e.health)
        if poisoned in enemies:
            return poisoned
        return min(enemies, key=lambda e: e.health)

    if skill == "Backstab":
        if poisoned in enemies:
            return poisoned
        return max(enemies, key=base_dps)

    if skill == "Poisoned Blade":
        return max(enemies, key=lambda e: e.max_health)

    # По умолчанию — primary
    return primary


def need_shadowstep(user: Combatant, enemies: List[Combatant]) -> bool:
    """True, если кто-то из врагов может снести ≥20% HP за удар."""
    thresh = 0.2 * user.max_health
    return any(base_dps(e) >= thresh for e in enemies)


class RogueAI(BaseAI):
    SKILLS = [
        "Smoke Bomb",
        "Poisoned Blade",
        "Assassinate",
        "Shadowstep",
        "Backstab",
    ]

    def __init__(self, actor: Combatant, cfg: dict):
        """
        actor — Combatant, от имени которого играет ИИ.
        cfg — секция CONFIG["ai"]["rogue"] из ai_rogue.yaml.
        """
        super().__init__(actor, cfg)

    def choose_action(
        self,
        primary: Combatant,
        enemies: List[Combatant],
    ) -> Tuple[Optional[str], Union[Combatant, List[Combatant]]]:
        user = self.actor
        cfg_ai = self.cfg
        skills_cfg = cfg_ai["skills"]

        hp_pct = user.health / user.max_health if user.max_health else 0.0

        # 1) Assassinate — финишер
        asc = "Assassinate"
        asc_cfg = skills_cfg[asc]
        if asc_cfg["enabled"] and user.can_use(asc, primary):
            tgt = pick_target(asc, enemies, user, primary)
            if tgt.health / tgt.max_health < asc_cfg["hp_pct"]:
                logger.debug(f"{user.name}: Assassinate → {tgt.name}")
                return asc, tgt

        # 2) Shadowstep — спасение если опасно или мало HP
        ss = "Shadowstep"
        ss_cfg = skills_cfg[ss]
        if ss_cfg["enabled"] and user.can_use(ss, primary):
            if hp_pct < ss_cfg.get("hp_pct", 0.5) or need_shadowstep(user, enemies):
                logger.debug(f"{user.name}: Shadowstep (HP {hp_pct:.0%})")
                return ss, user

        # Подготовка утилит: factor по кулдауну и вес
        cdf = lambda name: self.cd_factor(name) * skills_cfg[name].get("cd_weight", 1.0)
        mana_future = user.mana + (
            user.mana_regen if cfg_ai["resource"]["consider_mana_regen"] else 0.0
        )

        utils: dict[str, float] = {}

        # 3) Smoke Bomb — массовый бафф уклонения
        sb = "Smoke Bomb"
        sb_cfg = skills_cfg[sb]
        if sb_cfg["enabled"] and user.can_use(sb, primary):
            if len(enemies) >= sb_cfg.get("min_enemies", 0):
                allies = user.get_allies()
                # ценность — power × число союзников
                val = CONFIG["skills"][sb]["power"] * len(allies)
                utils[sb] = val * cdf(sb)
            else:
                utils[sb] = 0.0
        else:
            utils[sb] = 0.0

        # 4) Poisoned Blade — ставим яд
        pb = "Poisoned Blade"
        pb_cfg = skills_cfg[pb]
        if pb_cfg["enabled"] and user.can_use(pb, primary):
            tgt = pick_target(pb, enemies, user, primary)
            if not tgt.has_effect("poison"):
                power = CONFIG["skills"][pb]["power"]
                utils[pb] = tgt.max_health * power * cdf(pb)
            else:
                utils[pb] = 0.0
        else:
            utils[pb] = 0.0

        # 5) Backstab — сильный удар по самой опасной цели
        bs = "Backstab"
        bs_cfg = skills_cfg[bs]
        if bs_cfg["enabled"] and user.can_use(bs, primary):
            power = CONFIG["skills"][bs]["power"]
            utils[bs] = user.strength * power * cdf(bs)
        else:
            utils[bs] = 0.0

        # Выбираем лучшую «полезность»
        best_skill, best_score = max(utils.items(), key=lambda kv: kv[1])
        logger.debug(f"RogueAI utils: {utils}, best={best_skill} ({best_score:.2f})")

        # Если нет полезных умений — автоатака или автофинишер
        if best_score <= 0.0:
            # финиш auto‑attack
            fin = [e for e in enemies if e.health <= user.strength]
            if fin:
                return None, min(fin, key=lambda e: e.health)
            return None, primary

        # Целеполагание
        if best_skill == sb:
            return sb, user.get_allies()
        if best_skill == ss:
            return ss, user

        target = pick_target(best_skill, enemies, user, primary)
        if best_skill == pb:
            user._poison_mark = target  # запомним для следующего хода
        return best_skill, target

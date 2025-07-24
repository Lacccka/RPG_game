# src/my_game/battle/ai/warrior_ai.py

import logging
from typing import Tuple, Union, List, Optional

from my_game.battle.ai.base_ai import BaseAI
from my_game.base.combatant import Combatant
from my_game.config import CONFIG

logger = logging.getLogger(__name__)


class WarriorAI(BaseAI):
    SKILLS = [
        "Battle Roar",
        "Iron Will",
        "Shield Bash",
        "Taunt",
        "Whirlwind Slash",
    ]

    def __init__(self, actor: Combatant, cfg: dict):
        """
        actor — Combatant, от имени которого играет ИИ.
        cfg — содержимое секции CONFIG["ai"]["warrior"], загруженное из ai_warrior.yaml.
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
        # секция threat и глобальные веса тегов
        tag_weights = cfg_ai.get("tag_weights", {})

        # утилити-функции
        cdf = lambda name: self.cd_factor(name)
        mana_future = user.mana + (
            user.mana_regen if cfg_ai["resource"]["consider_mana_regen"] else 0.0
        )

        utils: dict[str, float] = {}

        # 1) Battle Roar
        name = "Battle Roar"
        scfg = skills_cfg[name]
        if (
            scfg["enabled"]
            and user.can_use(name, primary)
            and not user.has_effect("increase_strength")
        ):
            min_enemies = scfg.get("min_enemies", 0)
            boss_pct = scfg.get("boss_hp_pct", float("inf"))
            is_boss = any(e.max_health > user.max_health * boss_pct for e in enemies)
            if len(enemies) >= min_enemies or is_boss:
                allies = user.get_allies()
                utils[name] = (
                    user.strength * scfg["strength_pct"] * len(allies) * cdf(name)
                )
            else:
                utils[name] = 0.0
        else:
            utils[name] = 0.0

        # 2) Iron Will
        name = "Iron Will"
        scfg = skills_cfg[name]
        if scfg["enabled"] and user.can_use(name, primary):
            hp_pct = user.health / user.max_health if user.max_health else 0.0
            last_dmg = user._last_incoming_damage
            big_hit = last_dmg >= scfg["big_hit_pct"] * user.max_health
            if hp_pct < scfg["hp_pct"] or big_hit:
                utils[name] = user.max_health * scfg["shield_pct"] * cdf(name)
            else:
                utils[name] = 0.0
        else:
            utils[name] = 0.0

        # 3) Shield Bash
        name = "Shield Bash"
        scfg = skills_cfg[name]
        if scfg["enabled"] and user.can_use(name, primary):
            danger = any(
                self.compute_threat(e) >= scfg["danger_dps_thresh"] for e in enemies
            )
            base = user.strength * scfg["base_str_pct"]
            mult = scfg["danger_mult"] if danger else 1.0
            utils[name] = base * mult * cdf(name)
        else:
            utils[name] = 0.0

        # 4) Taunt
        name = "Taunt"
        scfg = skills_cfg[name]
        if scfg["enabled"] and user.can_use(name, primary):
            viable = [
                e
                for e in enemies
                if not e.has_effect(scfg["provoke_effect"])
                and getattr(e, "accuracy", 0.0) > scfg["acc_threshold"]
            ]
            if viable:
                avg = sum(self.compute_threat(e) for e in viable) / len(viable)
                utils[name] = avg * len(viable) * cdf(name)
            else:
                utils[name] = 0.0
        else:
            utils[name] = 0.0

        # 5) Whirlwind Slash
        name = "Whirlwind Slash"
        scfg = skills_cfg[name]
        if scfg["enabled"] and user.can_use(name, primary):
            if len(enemies) >= scfg.get("min_enemies", 0):
                mana_cost = CONFIG["skills"][name].get("mana_cost", 0)
                if mana_future >= mana_cost:
                    aoe = user.strength * scfg["whirl_str_pct"] * len(enemies)
                    bash_base = (
                        user.strength * skills_cfg["Shield Bash"]["base_str_pct"]
                    )
                    utils[name] = max(0.0, aoe - bash_base) * cdf(name)
                else:
                    utils[name] = 0.0
            else:
                utils[name] = 0.0
        else:
            utils[name] = 0.0

        # Выбираем лучший навык
        best_skill, best_score = max(utils.items(), key=lambda kv: kv[1])
        logger.debug(f"WarriorAI utils: {utils}, best={best_skill} ({best_score:.2f})")

        # Фолл‑бек: если никого не выбрали и бой с одним противником — пытаться Shield Bash
        if best_score <= 0.0:
            if len(enemies) == 1 and user.can_use("Shield Bash", primary):
                return "Shield Bash", primary
            # Добивание слабого или фокус по угрозе
            killable = [e for e in enemies if e.health <= user.strength]
            if killable:
                return None, min(killable, key=lambda e: e.health)
            return None, self.select_primary(enemies)

        # Возвращаем «сырые» цели, dispatcher сам соберёт список
        if best_skill == "Shield Bash":
            return best_skill, self.select_primary(enemies)
        if best_skill in {"Battle Roar", "Iron Will"}:
            return best_skill, user
        # Taunt и Whirlwind Slash — по primary
        return best_skill, primary

# src/my_game/battle/ai/mage_ai.py

import logging
from typing import Tuple, Union, List, Optional
from random import sample

from my_game.battle.ai.base_ai import BaseAI
from my_game.base.combatant import Combatant
from my_game.config import CONFIG

logger = logging.getLogger(__name__)


class MageAI(BaseAI):
    SKILLS = [
        "Fireball",
        "Magic Barrier",
        "Chain Lightning",
        "Mana Drain",
        "Meteor",
        "Time Warp",
    ]

    def __init__(self, actor: Combatant, cfg: dict):
        """
        actor — Combatant, за которого играет ИИ.
        cfg — секция CONFIG['ai']['mage'] из ai_mage.yaml.
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

        # 0) Если нам пора поставить щит — делаем это сразу
        mb_cfg = skills_cfg["Magic Barrier"]
        if mb_cfg["enabled"] and user.can_use("Magic Barrier", primary):
            hp_pct = user.health / user.max_health if user.max_health else 0.0
            if hp_pct < mb_cfg["hp_pct"]:
                logger.debug(
                    f"{user.name}: HP={user.health}/{user.max_health} < {mb_cfg['hp_pct']*100}% — ставим Magic Barrier"
                )
                return "Magic Barrier", user

        # вспомогательные функции
        cdf = lambda name: self.cd_factor(name) * skills_cfg[name].get("cd_weight", 1.0)
        mana_future = user.mana + (
            user.mana_regen if cfg_ai["resource"]["consider_mana_regen"] else 0.0
        )

        utils: dict[str, float] = {}

        # 1) Fireball — прямой урон
        name = "Fireball"
        scfg = skills_cfg[name]
        if scfg["enabled"] and user.can_use(name, primary):
            power = CONFIG["skills"][name]["power"]
            est = user.intelligence * power
            utils[name] = est * cdf(name)
        else:
            utils[name] = 0.0

        # 2) Chain Lightning — удар по двум целям
        name = "Chain Lightning"
        scfg = skills_cfg[name]
        if (
            scfg["enabled"]
            and user.can_use(name, primary)
            and len(enemies) >= scfg["min_enemies"]
        ):
            main_p = CONFIG["skills"][name]["power"] * user.intelligence
            sec_p = (
                CONFIG["skills"][name].get("secondary_power", 0.0) * user.intelligence
            )
            utils[name] = (main_p + sec_p) * cdf(name)
        else:
            utils[name] = 0.0

        # 3) Meteor — AoE по всем врагам
        name = "Meteor"
        scfg = skills_cfg[name]
        if (
            scfg["enabled"]
            and user.can_use(name, primary)
            and len(enemies) >= scfg["min_enemies"]
        ):
            power = CONFIG["skills"][name]["power"]
            utils[name] = user.intelligence * power * len(enemies) * cdf(name)
        else:
            utils[name] = 0.0

        # 4) Mana Drain — восстанавливаем ману, если мало
        name = "Mana Drain"
        scfg = skills_cfg[name]
        if scfg["enabled"] and user.can_use(name, primary):
            if user.mana < user.base_mana * scfg["mana_threshold"]:
                power = CONFIG["skills"][name]["power"]
                recovered = user.intelligence * power
                utils[name] = recovered * cdf(name)
            else:
                utils[name] = 0.0
        else:
            utils[name] = 0.0

        # 5) Time Warp — utility: extra turn
        name = "Time Warp"
        scfg = skills_cfg[name]
        if scfg["enabled"] and user.can_use(name, primary):
            uw = scfg.get("utility_weight", 1.0)
            utils[name] = user.intelligence * uw * cdf(name)
        else:
            utils[name] = 0.0

        # выбираем максимальную полезность
        best_skill, best_score = max(utils.items(), key=lambda kv: kv[1])
        logger.debug(f"MageAI utils: {utils}, best={best_skill} ({best_score:.2f})")

        # если ничто не полезнее — автоатака
        if best_score <= 0.0:
            return None, primary

        # формируем цели по таргет-моде
        mode = CONFIG["skills"][best_skill].get("target", "enemy")
        if mode == "all_enemies":
            return best_skill, enemies
        if mode == "two_random_enemies":
            cnt = min(2, len(enemies))
            return best_skill, sample(enemies, cnt)
        if mode == "team":
            return best_skill, user.get_allies()
        if mode == "ally":
            return best_skill, user

        # единичная цель
        return best_skill, primary

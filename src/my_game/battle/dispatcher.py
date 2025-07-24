# src/my_game/battle/dispatcher.py

import logging
from typing import Union, Sequence, List

from my_game.base.combatant import Combatant
from my_game.config import CONFIG
from my_game.battle.skill_executor import execute_skill, TargetSelector
from my_game.battle.ai import warrior_ai, mage_ai, rogue_ai
from my_game.battle.ai.base_ai import BaseAI
from my_game.battle.status import start_of_turn, end_of_turn

logger = logging.getLogger(__name__)

# Сопоставление display_name → (AI‑класс, ключ в CONFIG["ai"])
AI_MAP = {
    "Воин": (warrior_ai.WarriorAI, "warrior"),
    "Маг": (mage_ai.MageAI, "mage"),
    "Разбойник": (rogue_ai.RogueAI, "rogue"),
}


def take_turn(
    user: Combatant,
    opponents: Union[Combatant, Sequence[Combatant]],
) -> None:
    # 1) Список живых врагов
    pool = [opponents] if isinstance(opponents, Combatant) else list(opponents)
    pool = [o for o in pool if o.is_alive]
    if not pool:
        return

    # 2) Сохраняем visible для пассивок (Cleave)
    user._visible_enemies = pool

    # 3) PASSIVE: Last Stand — накладываем эффект survive_one_turn один раз
    if "Last Stand" in getattr(user, "skills", []):
        if not user.has_effect("survive_one_turn"):
            user.apply_effect({"effect": "survive_one_turn"})

    # ── Подготовка хода: тики эффектов, кулдаунов, маны, и периодические уроны ──
    user.tick_effects()
    user.tick_cooldowns()
    user.tick_mana()
    start_of_turn(user)

    try:
        # 4) Если это простой монстр без char_class — автоатака
        if not hasattr(user, "char_class"):
            target = pool[0]
            logger.debug(f"{user.name} (monster) auto-attacks {target.name}")
            user.attack(target)
            return

        # 5) Инстанцируем нужный AI с его конфигом
        display = user.char_class.display_name
        try:
            ai_cls, role_key = AI_MAP[display]
        except KeyError:
            raise ValueError(f"Нет AI для класса {display!r}")

        try:
            cfg = CONFIG["ai"][role_key]
        except KeyError:
            raise ValueError(f"Нет AI‑конфига для роли {role_key!r}")

        ai: BaseAI = ai_cls(user, cfg)

        # 6) Primary & выбор действия AI
        primary = ai.select_primary(pool)
        skill_name, chosen = ai.choose_action(primary, pool)
        logger.debug(f"{user.name} decided: skill={skill_name!r}, chosen={chosen}")

        # 7) Auto‑attack / finisher
        if skill_name is None:
            selector = TargetSelector(user, pool, getattr(user, "team", [user]))
            targets = selector.collect("enemy", chosen, primary)
            tgt = targets[0]
            logger.debug(f"{user.name} auto-attacks {tgt.name}")
            user.attack(tgt)
            return

        # 8) Собираем цели и исполняем навык
        skill_cfg = CONFIG["skills"][skill_name]
        mode = skill_cfg.get("target", "enemy")
        selector = TargetSelector(user, pool, getattr(user, "team", [user]))
        targets = selector.collect(mode, chosen, primary)
        logger.debug(f"{user.name} uses {skill_name} on {[t.name for t in targets]}")
        execute_skill(user, targets, skill_name)

        # 9) Если utility с extra_turn — сразу даём дополнительный ход
        if (
            skill_cfg.get("type") == "utility"
            and skill_cfg.get("effect") == "extra_turn"
        ):
            logger.debug(
                f"{user.name} получает немедленный дополнительный ход от {skill_name!r}"
            )
            return take_turn(user, opponents)

    finally:
        # ── Конец хода: периодический урон и снятие duration ──
        end_of_turn(user)

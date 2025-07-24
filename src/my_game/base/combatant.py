# src/my_game/base/combatant.py

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List

from ..config import CONFIG
from ..battle.status import (
    start_of_turn,
    modify_incoming_damage,
    apply_extra_turn,
    end_of_turn,
)


@dataclass
class Combatant(ABC):
    """Базовый класс для всех боевых сущностей."""

    # Обязательные параметры
    name: str
    level: int
    max_health: int
    strength: int
    agility: int
    intelligence: int
    defense: float

    # Опциональные параметры
    accuracy: float = 0.8
    crit_chance: float = 0.05
    dodge_chance: float = 0.03

    # Ресурсы
    base_mana: int = 0  # максимальный запас маны
    mana_regen: int = 0  # восстановление маны за ход
    mana: int = field(init=False, default=0)

    # Состояния, кулдауны и умения
    status_effects: List[Dict] = field(default_factory=list)
    cooldowns: Dict[str, int] = field(default_factory=dict)
    passives: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)

    # Системные поля
    health: int = field(init=False)
    _has_acted: bool = field(default=False, init=False)
    _last_incoming_damage: int = field(default=0, init=False)
    _last_stand_used: bool = field(
        default=False, init=False
    )  # трек, был ли уже Last Stand

    def __post_init__(self):
        # стартовое здоровье и мана
        self.health = self.max_health
        self.mana = self.base_mana

    @abstractmethod
    def attack(self, target: Combatant) -> None:
        """
        Обычная атака — должна быть реализована в подклассах.
        """
        ...

    def get_allies(self, include_self: bool = True) -> List[Combatant]:
        """
        Список союзников. В 1×1 просто [self], в групповом — по owner.characters.
        """
        if (
            hasattr(self, "owner")
            and self.owner
            and getattr(self.owner, "characters", None)
        ):
            team = [c for c in self.owner.characters if c.is_alive]
            return team if include_self else [c for c in team if c is not self]
        return [self]

    def get_enemies(self, opponent: Combatant) -> List[Combatant]:
        """
        Список врагов. В 1×1 просто [opponent].
        """
        return [opponent]

    def take_damage(self, amount: int) -> None:
        """Применить урон и сохранить _last_incoming_damage, срабатывание Last Stand."""
        # 1) статусные модификации
        amount = modify_incoming_damage(self, amount)

        # 2) сохраняем для триггеров
        self._last_incoming_damage = amount

        # Passive: Last Stand — если он у нас есть, ещё не потрачен и удар смертелен
        if (
            not self._last_stand_used
            and any(e.get("effect") == "survive_one_turn" for e in self.status_effects)
            and amount >= self.health
        ):
            # убираем эффект и отмечаем, что использовали
            self.status_effects = [
                e for e in self.status_effects if e.get("effect") != "survive_one_turn"
            ]
            self._last_stand_used = True
            self.health = 1
            print(f"{self.name} активирует Last Stand и остаётся с 1 HP!")
            return

        # 3) обычное вычитание
        self.health = max(self.health - amount, 0)
        print(
            f"{self.name} получает {amount} урона, осталось {self.health}/{self.max_health} HP."
        )

    def apply_effect(self, effect: Dict) -> None:
        """Наложить статус‑эффект."""
        self.status_effects.append(effect)
        print(
            f"{self.name} получает эффект: {effect['effect']} "
            f"на {effect.get('duration', '?')} ходов."
        )

    def has_effect(self, effect_name: str) -> bool:
        """Проверить наличие эффекта по имени."""
        return any(e["effect"] == effect_name for e in self.status_effects)

    def tick_effects(self) -> None:
        """Декрементировать duration и убирать истёкшие эффекты."""
        remaining: List[Dict] = []
        for effect in self.status_effects:
            if "duration" in effect:
                effect["duration"] -= 1
                if effect["duration"] > 0:
                    remaining.append(effect)
                else:
                    print(f"{self.name} теряет эффект: {effect['effect']}")
            else:
                remaining.append(effect)
        self.status_effects = remaining

    def tick_cooldowns(self) -> None:
        """Декрементировать кулдауны навыков."""
        new_cd: Dict[str, int] = {}
        for skill, cd in self.cooldowns.items():
            if cd > 1:
                new_cd[skill] = cd - 1
        self.cooldowns = new_cd

    def tick_mana(self) -> None:
        """Восстановление маны за ход."""
        if self.base_mana > 0:
            self.mana = min(self.base_mana, self.mana + self.mana_regen)

    def check_trigger(self, skill_name: str, target: Combatant) -> bool:
        """
        Проверяет условие применения навыка по его триггеру.
        """
        trig_cfgs = CONFIG["battle_rules"]["skill_triggers"]
        skill_cfg = CONFIG["skills"][skill_name]
        trig_name = skill_cfg.get("trigger", "always")

        hp_ratio = self.health / self.max_health
        enemy_hp_ratio = target.health / target.max_health

        if trig_name == "always":
            return True
        if trig_name == "on_low_hp":
            return hp_ratio < trig_cfgs["on_low_hp"]["threshold"]
        if trig_name == "if_enemy_low_hp":
            return enemy_hp_ratio < trig_cfgs["if_enemy_low_hp"]["threshold"]
        if trig_name == "on_fatal_hit":
            return self._last_incoming_damage >= self.health
        if trig_name == "if_first":
            return not self._has_acted
        return False

    def can_use(self, skill_name: str, target: Combatant) -> bool:
        """Проверить, доступен ли навык (есть ли, не на CD, хватает маны, триггер)."""
        if skill_name not in self.skills:
            return False
        cfg = CONFIG["skills"][skill_name]
        if self.cooldowns.get(skill_name, 0) > 0:
            return False
        cost = cfg.get("mana_cost", 0)
        if cost and self.mana < cost:
            return False
        return self.check_trigger(skill_name, target)

    def take_turn(self, opponent: Combatant) -> None:
        """
        Выполнить ход:
          1. tick_effects, tick_cooldowns, tick_mana
          2. start_of_turn
          3. ai_take_turn
          4. apply_extra_turn
          5. end_of_turn
          6. отметить _has_acted
        """
        self.tick_effects()
        self.tick_cooldowns()
        self.tick_mana()

        # стартовые эффекты (яд, горение и т.п.)
        start_of_turn(self)

        # ход ИИ
        from ..battle.dispatcher import take_turn as ai_take_turn

        ai_take_turn(self, opponent)

        # дополнительный ход
        if apply_extra_turn(self):
            self.take_turn(opponent)

        # концевые эффекты
        end_of_turn(self)

        self._has_acted = True

    @property
    def is_alive(self) -> bool:
        return self.health > 0

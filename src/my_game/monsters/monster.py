# src/my_game/monsters/monster.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Tuple

from ..base.combatant import Combatant
from ..config import CONFIG
from .monster_type import MonsterType
from ..battle.damage import check_hit, calc_damage
from ..battle.enums import Element
from ..battle.status import before_action

# ──────────────────────────────────────────────────────────────────────────────
#  Константы из YAML
# ──────────────────────────────────────────────────────────────────────────────
_MON_TEMPLATES = CONFIG["monsters"]["templates"]

_BASE_DAMAGE: Dict[MonsterType, int] = {
    MonsterType[key]: val for key, val in CONFIG["monsters"]["base_damage"].items()
}

_COEFFS: Dict[MonsterType, Tuple[float, float]] = {
    MonsterType[key]: (c["phys_coeff"], c["mag_coeff"])
    for key, c in CONFIG["monsters"]["coeffs"].items()
}


# ──────────────────────────────────────────────────────────────────────────────
#  Класс Monster
# ──────────────────────────────────────────────────────────────────────────────
@dataclass(kw_only=True)
class Monster(Combatant):
    """
    Игровой монстр.

    • `monster_type` — enum‑идентификатор из MonsterType
    • `base_damage`  — параметр из YAML, прибавляется к урону
    """

    monster_type: MonsterType
    base_damage: int = 0

    resistances: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    loot_table: Dict[str, float] = field(default_factory=dict)

    # Классовые справочники
    BASE_DAMAGE: ClassVar[Dict[MonsterType, int]] = _BASE_DAMAGE
    COEFFS: ClassVar[Dict[MonsterType, Tuple[float, float]]] = _COEFFS

    # ───────────────────────
    #  Dunder‑hooks
    # ───────────────────────
    def __post_init__(self):
        super().__post_init__()  # установит health = max_health
        self.species = self.monster_type.name  # для damage.calc_damage

        # Кэшируем коэффициенты (может пригодиться для логов/AI)
        self.phys_coeff, self.mag_coeff = self.COEFFS.get(self.monster_type, (1.0, 1.0))

    # ───────────────────────
    #  Боевое API
    # ───────────────────────
    def attack(self, target: Combatant) -> None:
        visible = getattr(self, "_visible_enemies", [target])
        allowed = before_action(self, visible)
        if not allowed:
            return
        if target not in allowed:
            target = allowed[0]

        if not check_hit(self, target):
            print(f"{self.name} промахивается! (шанс {self._last_hit:.1%})")
            return

        dmg = calc_damage(self, target, element=Element.PHYSICAL)
        self._log_hit(target, dmg)
        target.take_damage(dmg)

    # ───────────────────────
    #  Служебное
    # ───────────────────────
    def _log_hit(self, target: Combatant, dmg: int) -> None:
        msg = f"{self.display_name} ({self.monster_type.name}) "
        if getattr(self, "_last_crit", False):
            msg += "НАНОСИТ КРИТ! "
        msg += f"наносит {dmg} урона"

        if getattr(self, "_last_weak", False):
            msg += " (слабость)"
        elif getattr(self, "_last_resist", False):
            msg += " (резист)"

        print(msg + ".")

    # ───────────────────────
    #  Фабрика из YAML
    # ───────────────────────
    @staticmethod
    def from_config(monster_type: str, level: int) -> "Monster":
        data = _MON_TEMPLATES[monster_type]
        mtype = MonsterType[monster_type]

        return Monster(
            name=monster_type.capitalize(),
            level=level,
            max_health=data["base_health"],
            strength=data["base_strength"],
            agility=data["base_agility"],
            intelligence=data["base_intelligence"],
            defense=data.get("defense", 0),
            monster_type=mtype,
            base_damage=_BASE_DAMAGE.get(mtype, 0),
            resistances=data.get("resistances", []),
            weaknesses=data.get("weaknesses", []),
        )

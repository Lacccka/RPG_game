# src/my_game/battle/damage.py
"""
Профессиональная система расчёта попаданий и урона по battle_rules.yaml,
с учётом phys_coeff/mag_coeff у CharacterClass.
"""

import math
import random
from typing import TYPE_CHECKING

from .enums import Element, DamageSource, CritType
from ..config import CONFIG

if TYPE_CHECKING:
    from ..base.combatant import Combatant

# — кешируем нужные конфиги
_cfg = CONFIG["battle_rules"]
_hit_cfg = _cfg["hit_chance"]
_dmg_cfg = _cfg["damage_rules"]
_def_cfg = _cfg["defense"]
_elem_cfg = _cfg["elements"]
_level_coeff = _dmg_cfg["level_coeff"]
_variance = _dmg_cfg["variance"]
_crit_mul = _dmg_cfg["crit"]["multiplier"]
_min_floor = _dmg_cfg["min_damage"]
_MON_COEFFS = CONFIG["monsters"]["coeffs"]


def _logistic(x: float, x0: float, k: float) -> float:
    return 1.0 / (1.0 + math.exp(-(x - x0) / k))


def hit_chance(attacker: "Combatant", defender: "Combatant") -> float:
    """
    Расчёт шанса попадания:
      - логистическая кривая по ΔAgility
      - умножение на accuracy и (1 − dodge_chance)
      - ограничение [min, max]
    """
    delta = (attacker.agility - defender.agility) / _hit_cfg["scale"]
    p = _logistic(delta, _hit_cfg["logistic"]["x0"], _hit_cfg["logistic"]["k"])
    p *= attacker.accuracy * (1.0 - defender.dodge_chance)
    return max(_hit_cfg["clamp"]["min"], min(p, _hit_cfg["clamp"]["max"]))


def check_hit(attacker: "Combatant", defender: "Combatant") -> bool:
    """
    Функция-обёртка: сохраняет последний шанс в attacker._last_hit
    и возвращает True/False по случайному броску.
    """
    chance = hit_chance(attacker, defender)
    attacker._last_hit = chance
    return random.random() < chance


def calc_damage(
    attacker: "Combatant",
    defender: "Combatant",
    *,
    element: Element = Element.PHYSICAL,
    source: DamageSource = DamageSource.NORMAL,
    crit_type: CritType = CritType.NORMAL,
    power: float = 1.0,
) -> int:
    """
    Основная функция расчёта урона:
      1) Смотрим класс или монстра → phys_coeff/mag_coeff
      2) Считаем offense = STR*phys + INT*mag + base_damage*power
      3) Масштабируем на уровне: ×(1 + lvl*level_coeff)
      4) Mitigation: raw = off * (off / (off + DEF))
      5) Вносим variance (усечённый норм. шум)
      6) Проверяем криты
      7) Учитываем элементальные резисты/слабости
      8) PASSIVE: Arcane Mastery — усиливаем магический урон
      9) Обрезаем до min_damage
    """
    # 1) Определяем коэффициенты
    species = getattr(attacker, "species", None)
    if species:
        mc = _MON_COEFFS.get(species, {})
        phys_cm = mc.get("phys_coeff", 1.0)
        mag_cm = mc.get("mag_coeff", 1.0)
    else:
        cc = getattr(attacker, "char_class", None)
        phys_cm = cc.phys_coeff if cc else 1.0
        mag_cm = cc.mag_coeff if cc else 1.0

    # 2) Offensive rating
    phys = attacker.strength * _dmg_cfg["coeffs"]["phys"] * phys_cm
    mag = attacker.intelligence * _dmg_cfg["coeffs"]["mag"] * mag_cm
    base = getattr(attacker, "base_damage", 0) * power
    offense = phys + mag + base

    # 3) Level scaling
    kind = "monster" if species else "player"
    offense *= 1.0 + attacker.level * _level_coeff[kind]

    # 4) Mitigation (ELO-style)
    def_val = defender.defense * _def_cfg["reduction_per_point"]
    if offense + def_val > 0:
        factor = offense / (offense + def_val)
    else:
        factor = 0.0
    raw = offense * factor

    # 5) Variance (truncated Gaussian)
    μ, σ = 1.0, (_variance["max"] - 1.0) / 3.0
    v = random.gauss(μ, σ)
    v = max(_variance["min"], min(_variance["max"], v))
    raw *= v

    # 6) Critical
    if random.random() < attacker.crit_chance:
        raw *= _crit_mul[crit_type.name.lower()]
        attacker._last_crit = True
    else:
        attacker._last_crit = False

    # 7) Elemental resist/weak
    attacker._last_weak = attacker._last_resist = False
    if source is not DamageSource.TRUE:
        nm = element.name.lower()
        if nm in getattr(defender, "weaknesses", []):
            raw *= _elem_cfg["weak_multiplier"]
            attacker._last_weak = True
        elif nm in getattr(defender, "resistances", []):
            raw *= _elem_cfg["resist_multiplier"]
            attacker._last_resist = True

    # 8) PASSIVE: Arcane Mastery — усиливаем магический урон
    if (
        element is not Element.PHYSICAL
        and hasattr(attacker, "skills")
        and "Arcane Mastery" in attacker.skills
    ):
        bonus = CONFIG["skills"]["Arcane Mastery"]["power"]
        raw *= 1.0 + bonus

    # 9) Floor & round
    dmg = int(round(raw))
    return max(dmg, _min_floor)

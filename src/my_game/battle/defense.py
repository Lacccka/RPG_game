# src/my_game/battle/defense.py
"""
Плоская формула подавления урона (flat reduction) согласно конфигу:
  dmg_out = raw − defense × reduction_per_point, не ниже min_damage.
"""


def mitigated(
    raw: float, defense: int, *, reduction_per_point: float, min_damage: int
) -> float:
    """
    Flat‑reduction:
      − defense * reduction_per_point
    Нижний порог — min_damage.
    """
    out = raw - defense * reduction_per_point
    return max(out, min_damage)

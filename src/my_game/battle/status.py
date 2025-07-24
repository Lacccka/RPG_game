# src/my_game/battle/status.py

from typing import List, TYPE_CHECKING

from my_game.config import CONFIG

if TYPE_CHECKING:
    from my_game.base.combatant import Combatant  # только для аннотаций

# Конфиг статус‑эффектов
_STATUS_CFG = CONFIG["battle_rules"]["status_effects"]


def start_of_turn(combatant: "Combatant") -> None:
    """
    FIX: для backward compatibility.
    Теперь весь периодический урон и уменьшение duration
    выполняются в end_of_turn, так что здесь просто перенаправляем.
    """
    end_of_turn(combatant)


def _apply_periodic_damage(combatant: "Combatant") -> None:
    """
    Наносит урон за ход от эффектов типа burn, poison и т.п.
    Уменьшает duration, если оно задано под end_of_turn.
    """
    for eff in list(combatant.status_effects):
        cfg = _STATUS_CFG.get(eff["effect"], {})
        if "periodic_damage" not in cfg:
            continue

        dmg = int(combatant.max_health * cfg["periodic_damage"])
        if dmg <= 0:
            continue

        print(f"{combatant.name} страдает от {eff['effect']}: –{dmg} HP.")
        # уменьшаем напрямую, чтобы Last Stand не срабатывал повторно
        combatant.health = max(combatant.health - dmg, 0)
        print(f"{combatant.name}: {combatant.health}/{combatant.max_health} HP.")

        # по окончании хода убираем duration
        if (
            eff.get("duration") is not None
            and cfg.get("duration_decrement") == "end_of_turn"
        ):
            eff["duration"] -= 1
            if eff["duration"] <= 0:
                combatant.status_effects.remove(eff)
                print(f"{combatant.name} излечивается от {eff['effect']}.")


def before_action(
    attacker: "Combatant", targets: List["Combatant"]
) -> List["Combatant"]:
    """
    Блокирует ход stun, перенаправляет цель по provoke.
    """
    # 1) stun отбирает весь ход
    if any(e["effect"] == "stun" for e in attacker.status_effects):
        print(f"{attacker.name} не может действовать — оглушён!")
        return []

    # 2) если есть provoke на ком-то из целей, бить только их
    provoked = [
        t for t in targets if any(e["effect"] == "provoke" for e in t.status_effects)
    ]
    return provoked or targets


def modify_incoming_damage(defender: "Combatant", damage: int) -> int:
    """
    1) Evade — если есть, пропускаем весь урон и убираем эффект.
    2) reduce_damage
    3) magic_shield
    """
    # 1) Evade: 100% уклонение от одного удара
    for eff in list(defender.status_effects):
        if eff["effect"] == "evade":
            print(f"{defender.name} уклоняется от атаки!")
            defender.status_effects.remove(eff)
            return 0

    # 2) reduce_damage — уменьшение входящего урона
    for eff in defender.status_effects:
        if eff["effect"] == "reduce_damage":
            raw = eff.get("power", _STATUS_CFG["reduce_damage"]["damage_multiplier"])
            mult = 1.0 - raw if raw <= 1.0 else raw
            print(f"{defender.name} снижает урон ×{mult:.2f}.")
            damage = int(damage * mult)
            break

    # 3) magic_shield — поглощение щитом
    for eff in list(defender.status_effects):
        if eff["effect"] != "magic_shield":
            continue
        frac = eff.get("power", _STATUS_CFG["magic_shield"]["absorb_amount"])
        max_absorb = int(defender.max_health * frac)
        used = eff.get("used", 0)
        to_absorb = min(max_absorb - used, damage)
        damage -= to_absorb
        eff["used"] = used + to_absorb
        print(
            f"{defender.name} щит поглотил {to_absorb} урона "
            f"(осталось {max_absorb - eff['used']})."
        )
        if eff["used"] >= max_absorb:
            defender.status_effects.remove(eff)
            print(f"{defender.name} теряет эффект magic_shield.")
        break

    return damage


def apply_extra_turn(combatant: "Combatant") -> bool:
    """
    Проверяет эффект extra_turn и даёт дополнительный ход.
    """
    for eff in list(combatant.status_effects):
        if eff["effect"] == "extra_turn":
            combatant.status_effects.remove(eff)
            print(f"{combatant.name} получает дополнительный ход!")
            return True
    return False


def end_of_turn(combatant: "Combatant") -> None:
    """
    В конце хода наносим периодический урон и снимаем duration.
    """
    _apply_periodic_damage(combatant)

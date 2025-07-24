from typing import List, TYPE_CHECKING, Optional, Tuple, Union

from my_game.config import CONFIG

if TYPE_CHECKING:
    from my_game.base.combatant import Combatant


class BaseAI:
    """Базовый интерфейс для всех AI‑классов."""

    def __init__(self, actor: "Combatant", cfg: dict):
        # actor — это тот самый Combatant, от имени которого играет AI
        # cfg — это содержимое секции CONFIG["ai"][<класс>], загруженное из ai_warrior.yaml
        self.actor = actor
        self.cfg = cfg

    def cd(self, skill_name: str) -> float:
        """Оставшееся время восстановления навыкa."""
        return float(self.actor.cooldowns.get(skill_name, 0.0))

    def cd_factor(self, skill_name: str) -> float:
        """
        Учитывает готовность + вес из YAML:
          weight = cfg["skills"][skill_name]["cd_weight"]
          factor = weight * (1 / (cd + 1))
        """
        scfg = self.cfg["skills"].get(skill_name, {})
        weight = scfg.get("cd_weight", 1.0)
        cd_time = self.cd(skill_name)
        return weight * (1.0 / (cd_time + 1.0))

    def resource_penalty(self, cost: float, regen_amount: float) -> float:
        """
        Штраф за дороговизну:
        cost — манакост,
        regen_amount — сколько маны вернётся за время CD.
        """
        avail = self.actor.mana + regen_amount
        return max(0.0, (cost - avail) / avail)

    def compute_threat(self, enemy: "Combatant") -> float:
        """
        Threat = DPS (base_damage × accuracy / attack_interval),
        скорректированное по resistances/weaknesses и tag_weights из cfg.
        """
        t = self.cfg["threat"]
        key = enemy.name.upper()
        tpl = CONFIG["monsters"]["templates"].get(key, {})
        base = CONFIG["monsters"]["base_damage"].get(key, 0)

        # если включено, читаем accuracy, иначе 1.0
        acc = getattr(enemy, "accuracy", 1.0) if t.get("use_accuracy", False) else 1.0
        # если включено, читаем attack_interval, иначе 1.0
        interval = (
            getattr(enemy, "attack_interval", 1.0)
            if t.get("use_interval", False)
            else 1.0
        )
        dps = base * acc / interval

        # резисты/уязвимости к физическому
        if "physical" in tpl.get("resistances", []):
            dps *= t.get("resist_modifier", 1.0)
        if "physical" in tpl.get("weaknesses", []):
            dps *= t.get("weak_modifier", 1.0)

        # тэги
        for tag in tpl.get("tags", []):
            dps *= t.get("tag_weights", {}).get(
                tag, t.get("tag_weights", {}).get("default", 1.0)
            )

        return dps

    def select_primary(self, enemies: List["Combatant"]) -> "Combatant":
        """Выбирает врага с максимальной угрозой."""
        return max(enemies, key=self.compute_threat)

    def choose_action(
        self,
        primary: "Combatant",
        enemies: List["Combatant"],
    ) -> Tuple[Optional[str], Union["Combatant", List["Combatant"]]]:
        raise NotImplementedError

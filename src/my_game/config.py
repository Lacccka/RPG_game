# src/my_game/config.py

import yaml
from pathlib import Path

# Путь к папке src/ — две папки выше текущего файла, затем в config/
_CONFIG_DIR = Path(__file__).parent.parent / "config"

# Статические конфиги
_STATIC_FILES = {
    "characters": "characters.yaml",
    "monsters": "monsters.yaml",
    "skills": "skills.yaml",
    "growth": "growth.yaml",
    "battle_rules": "battle_rules.yaml",
    "gear": "gear.yaml",
}

CONFIG: dict[str, dict] = {}

# 1) Загружаем статические файлы
for key, fname in _STATIC_FILES.items():
    path = _CONFIG_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Cannot find config file: {path}")
    if key == "skills":
        # skills.yaml может содержать несколько документов
        merged: dict = {}
        with open(path, encoding="utf-8") as f:
            for doc in yaml.safe_load_all(f):
                if isinstance(doc, dict):
                    merged.update(doc)
        data = merged
    else:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    # Распаковываем {key: {...}} → {...}
    if isinstance(data, dict) and key in data and len(data) == 1:
        CONFIG[key] = data[key]
    else:
        CONFIG[key] = data

# 2) Загружаем все AI‑конфиги ai_*.yaml
ai_configs: dict[str, dict] = {}
for ai_file in _CONFIG_DIR.glob("ai_*.yaml"):
    with open(ai_file, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    # Ожидаем структуру {role: {...}}
    if isinstance(doc, dict) and len(doc) == 1:
        role, cfg = next(iter(doc.items()))
        ai_configs[role] = cfg
    else:
        # На случай если в файле список документов
        for sub in doc if isinstance(doc, list) else [doc]:
            if isinstance(sub, dict) and len(sub) == 1:
                role, cfg = next(iter(sub.items()))
                ai_configs[role] = cfg

CONFIG["ai"] = ai_configs

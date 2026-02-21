# --- START OF FILE core/config.py ---
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = str(_PROJECT_ROOT / "config.json")
SECRETS_PATH = str(_PROJECT_ROOT / "secrets.json")

class ConfigManager:
    @staticmethod
    def _load_json(path: str = CONFIG_PATH) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except Exception as e:
                    logging.warning("Failed to parse JSON from %s: %s", path, e)
                    return {}
        return {}

    @staticmethod
    def _save_json(data: Dict[str, Any], path: str = CONFIG_PATH) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def get_language() -> str:
        data = ConfigManager._load_json(CONFIG_PATH)
        return data.get("language", "ar")

    @staticmethod
    def set_language(lang: str) -> None:
        data = ConfigManager._load_json(CONFIG_PATH)
        data["language"] = lang
        ConfigManager._save_json(data, CONFIG_PATH)
    
    @staticmethod
    def get_config_value(key: str, default: Any = None) -> Any:
        data = ConfigManager._load_json(CONFIG_PATH)
        return data.get(key, default)

    @staticmethod
    def set_config_value(key: str, value: Any) -> None:
        data = ConfigManager._load_json(CONFIG_PATH)
        data[key] = value
        ConfigManager._save_json(data, CONFIG_PATH)

    @staticmethod
    def get_secret(key: str, default: Any = None) -> Any:
        data = ConfigManager._load_json(SECRETS_PATH)
        return data.get(key, default)

    @staticmethod
    def set_secret(key: str, value: Any) -> None:
        data = ConfigManager._load_json(SECRETS_PATH)
        data[key] = value
        ConfigManager._save_json(data, SECRETS_PATH)

    @staticmethod
    def save_window_state(name: str, window: Any) -> None:
        data = ConfigManager._load_json(CONFIG_PATH)
        if "windows" not in data: data["windows"] = {}
        
        state = {
            "w": window.width(),
            "h": window.height(),
            "x": window.x(),
            "y": window.y(),
            "maximized": window.isMaximized()
        }
        data["windows"][name] = state
        ConfigManager._save_json(data, CONFIG_PATH)

    @staticmethod
    def load_window_state(name: str, window: Any) -> None:
        data = ConfigManager._load_json(CONFIG_PATH)
        windows = data.get("windows", {})
        state = windows.get(name)
        if state:
            if state.get("w", 0) > 100 and state.get("h", 0) > 100:
                window.resize(state["w"], state["h"])
                window.move(state["x"], state["y"])
            if state.get("maximized", False):
                window.showMaximized()
# --- END OF FILE core/config.py ---
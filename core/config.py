import os
import json

CONFIG_PATH = "config.json"

class ConfigManager:
    @staticmethod
    def _load_json():
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except: return {}
        return {}

    @staticmethod
    def _save_json(data):
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def get_language():
        data = ConfigManager._load_json()
        return data.get("language", "ar")

    @staticmethod
    def set_language(lang):
        data = ConfigManager._load_json()
        data["language"] = lang
        ConfigManager._save_json(data)
    
    @staticmethod
    def get_config_value(key, default=None):
        data = ConfigManager._load_json()
        return data.get(key, default)

    @staticmethod
    def set_config_value(key, value):
        data = ConfigManager._load_json()
        data[key] = value
        ConfigManager._save_json(data)

    @staticmethod
    def save_window_state(name, window):
        data = ConfigManager._load_json()
        if "windows" not in data: data["windows"] = {}
        
        state = {
            "w": window.width(),
            "h": window.height(),
            "x": window.x(),
            "y": window.y(),
            "maximized": window.isMaximized()
        }
        data["windows"][name] = state
        ConfigManager._save_json(data)

    @staticmethod
    def load_window_state(name, window):
        data = ConfigManager._load_json()
        windows = data.get("windows", {})
        state = windows.get(name)
        if state:
            if state.get("w") > 100 and state.get("h") > 100:
                window.resize(state["w"], state["h"])
                window.move(state["x"], state["y"])
            if state.get("maximized", False):
                window.showMaximized()
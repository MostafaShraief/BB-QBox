from core.config import ConfigManager
from core.locales import TRANS

def tr(key):
    lang = ConfigManager.get_language()
    return TRANS.get(lang, TRANS["en"]).get(key, key)
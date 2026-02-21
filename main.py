# --- START OF FILE main.py ---
import sys
import os
import json
from PyQt6.QtWidgets import QApplication
from ui.menu import MainMenu

def ensure_config():
    defaults = {
        "answer_keywords": ["الحل", "الجواب", "الاجابة", "answer"],
        "note_keywords": ["ملاحظة", "توضيح", "شرح", "تنويه", "note", "hint"],
        "stop_chars": [":", "-", "."],
        "language": "ar",
        "shortcuts": {
            "save": "Ctrl+S",
            "undo": "Ctrl+Z",
            "redo": "Ctrl+Y",
            "delete": "Del",
            "renumber": "R",
            "link": "L",
            "unlink": "U",
            "mark_note": "Ctrl+M",
            "detect_page": "Ctrl+D",
            "detect_bulk": "Ctrl+B",
            "prev": "Left",
            "next": "Right"
        }
    }
    
    current = {}
    if os.path.exists("config.json"):
        try:
            with open("config.json", 'r', encoding='utf-8') as f:
                current = json.load(f)
        except Exception:
            current = {}
            
    # Recursive merge to ensure nested keys (like 'shortcuts') exist
    updated = False
    for k, v in defaults.items():
        if k not in current:
            current[k] = v
            updated = True
        elif isinstance(v, dict) and isinstance(current[k], dict):
            for sub_k, sub_v in v.items():
                if sub_k not in current[k]:
                    current[k][sub_k] = sub_v
                    updated = True
                    
    if updated or not os.path.exists("config.json"):
        with open("config.json", 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=4, ensure_ascii=False)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    ensure_config()
    
    menu = MainMenu(app)
    menu.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
# --- END OF FILE main.py ---
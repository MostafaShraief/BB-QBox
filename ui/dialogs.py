# --- START OF FILE ui/dialogs.py ---
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QKeySequenceEdit, QPlainTextEdit, 
                             QGroupBox, QLineEdit, QTextEdit, QComboBox, QMessageBox,
                             QFileDialog, QTabWidget, QWidget)
from PyQt6.QtGui import QKeySequence
from PyQt6.QtCore import Qt
from core.config import ConfigManager
from ui.common import tr
import os
import shutil
import json

class UnifiedSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(600, 650)
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # Tab 1: Keywords
        self.kw_tab = KeywordsWidget()
        self.tabs.addTab(self.kw_tab, tr("keyword_title"))
        
        # Tab 2: Shortcuts
        self.sc_tab = ShortcutsWidget()
        self.tabs.addTab(self.sc_tab, tr("shortcuts_title"))
        
        layout.addWidget(self.tabs)
        
        btn_save = QPushButton(tr("key_save"))
        btn_save.clicked.connect(self.save_all)
        layout.addWidget(btn_save)
        
    def save_all(self):
        self.kw_tab.save_data()
        self.sc_tab.save_data()
        self.accept()

class KeywordsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.cfg = ConfigManager._load_json()
        
        self.txt_ans = self.create_group(tr("kw_ans"), self.cfg.get("answer_keywords", []))
        self.txt_note = self.create_group(tr("kw_note"), self.cfg.get("note_keywords", []))
        self.txt_stop = self.create_group(tr("kw_stop"), self.cfg.get("stop_chars", []))

    def create_group(self, title, items):
        gb = QGroupBox(title)
        l = QVBoxLayout()
        txt = QPlainTextEdit()
        # Handle cases where items might not be a list
        if not isinstance(items, list): items = []
        txt.setPlainText("\n".join(str(i) for i in items))
        l.addWidget(txt)
        gb.setLayout(l)
        self.layout.addWidget(gb)
        return txt

    def save_data(self):
        self.cfg["answer_keywords"] = [x.strip() for x in self.txt_ans.toPlainText().split("\n") if x.strip()]
        self.cfg["note_keywords"] = [x.strip() for x in self.txt_note.toPlainText().split("\n") if x.strip()]
        self.cfg["stop_chars"] = [x.strip() for x in self.txt_stop.toPlainText().split("\n") if x.strip()]
        ConfigManager._save_json(self.cfg)

class ShortcutsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([tr("key_action"), tr("key_shortcut")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.table)
        
        self.shortcuts = ConfigManager.get_config_value("shortcuts", {})
        if not isinstance(self.shortcuts, dict): self.shortcuts = {}
        
        self.load_table()

    def load_table(self):
        self.table.setRowCount(len(self.shortcuts))
        row = 0
        self.key_editors = {}
        
        names = {
            "save": tr("save"), "undo": tr("undo"), "redo": tr("redo"),
            "delete": tr("delete"), "renumber": tr("renumber"),
            "link": tr("link_crops"), "unlink": tr("unlink_crops"),
            "detect_page": tr("auto_page"), "detect_bulk": tr("auto_bulk"),
            "prev": tr("prev"), "next": tr("next")
        }

        for key, val in self.shortcuts.items():
            display_name = names.get(key, key)
            name_item = QTableWidgetItem(str(display_name))
            name_item.setFlags(name_item.flags() ^ 2) # Read-only
            self.table.setItem(row, 0, name_item)
            
            # Defensive check for val
            safe_val = str(val) if val else ""
            editor = QKeySequenceEdit(QKeySequence(safe_val))
            self.table.setCellWidget(row, 1, editor)
            self.key_editors[key] = editor
            row += 1

    def save_data(self):
        new_conf = {}
        for key, editor in self.key_editors.items():
            seq = editor.keySequence().toString()
            new_conf[key] = seq
        ConfigManager.set_config_value("shortcuts", new_conf)

class EditQuestionDialog(QDialog):
    def __init__(self, question_data, q_index, bank_path, parent=None):
        super().__init__(parent)
        self.q_data = question_data
        self.q_index = q_index
        self.bank_path = bank_path
        self.modified_data = None
        self.should_delete = False
        self.image_modified = False
        
        self.setWindowTitle(tr("edit_title"))
        self.resize(600, 700)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tools
        h_tools = QHBoxLayout()
        btn_del = QPushButton(tr("delete_q"))
        btn_del.setStyleSheet("background-color: #FF5252; color: white;")
        btn_del.clicked.connect(self.delete_me)
        h_tools.addWidget(btn_del)
        
        btn_rep_img = QPushButton(tr("replace_img"))
        btn_rep_img.clicked.connect(self.replace_image)
        h_tools.addWidget(btn_rep_img)
        
        btn_crop = QPushButton(tr("crop_img"))
        btn_crop.clicked.connect(self.open_cropper)
        h_tools.addWidget(btn_crop)
        layout.addLayout(h_tools)
        
        # Form
        layout.addWidget(QLabel("Question Text:"))
        self.txt_q = QTextEdit()
        self.txt_q.setPlainText(self.q_data.get("question", ""))
        layout.addWidget(self.txt_q)
        
        layout.addWidget(QLabel("Options (one per line):"))
        self.txt_opts = QPlainTextEdit()
        self.txt_opts.setPlainText("\n".join(self.q_data.get("options", [])))
        layout.addWidget(self.txt_opts)
        
        layout.addWidget(QLabel("Correct Option Index (0=A, 1=B...):"))
        self.txt_correct = QLineEdit()
        correct_idx = self.q_data.get("correct_options", [0])
        self.txt_correct.setText(str(correct_idx[0]) if correct_idx else "0")
        layout.addWidget(self.txt_correct)
        
        layout.addWidget(QLabel("Explanation:"))
        self.txt_expl = QTextEdit()
        self.txt_expl.setPlainText(self.q_data.get("explanation", ""))
        layout.addWidget(self.txt_expl)
        
        # Actions
        h_btns = QHBoxLayout()
        btn_save = QPushButton(tr("save_changes"))
        btn_save.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_save.clicked.connect(self.save_data)
        btn_cancel = QPushButton(tr("cancel"))
        btn_cancel.clicked.connect(self.reject)
        
        h_btns.addWidget(btn_save)
        h_btns.addWidget(btn_cancel)
        layout.addLayout(h_btns)

    def save_data(self):
        try:
            c_idx = int(self.txt_correct.text().strip())
        except: c_idx = 0
        
        self.modified_data = {
            "type": "quiz",
            "question": self.txt_q.toPlainText(),
            "options": [x.strip() for x in self.txt_opts.toPlainText().split("\n") if x.strip()],
            "correct_options": [c_idx],
            "explanation": self.txt_expl.toPlainText()
        }
        self.accept()

    def delete_me(self):
        if QMessageBox.question(self, tr("delete"), tr("confirm_delete")) == QMessageBox.StandardButton.Yes:
            self.should_delete = True
            self.accept()

    def replace_image(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("replace_img"), "", "Images (*.jpg *.png)")
        if f:
            dest = os.path.join(self.bank_path, "images", f"{self.q_index+1}.jpg")
            if not os.path.exists(os.path.dirname(dest)): os.makedirs(os.path.dirname(dest))
            try:
                from PIL import Image
                img = Image.open(f).convert("RGB")
                img.save(dest, "JPEG")
                self.image_modified = True
                QMessageBox.information(self, "Done", "Image replaced.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def open_cropper(self):
        from ui.window import ImageCropperApp
        img_path = os.path.join(self.bank_path, "images", f"{self.q_index+1}.jpg")
        if not os.path.exists(img_path):
            QMessageBox.warning(self, "Error", "No image exists.")
            return
        
        self.cropper = ImageCropperApp(single_image_mode=True)
        self.cropper.load_single_image(img_path)
        self.cropper.show()
        # Mark modified so viewer reloads
        self.image_modified = True
# --- END OF FILE ui/dialogs.py ---
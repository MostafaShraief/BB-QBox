import os
import json
import shutil
import re
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QSplitter, 
                             QScrollArea, QRadioButton, QButtonGroup, QFrame,
                             QComboBox, QMessageBox, QCheckBox, QLineEdit,
                             QTextEdit, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

from utils import tr, ConfigManager

class OptionEditRow(QWidget):
    def __init__(self, prefix, text, is_correct, on_remove, on_set_correct, button_group):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)

        self.btn_del = QPushButton("✕")
        self.btn_del.setFixedSize(28, 28)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setStyleSheet("""
            QPushButton { background: #442222; border: 1px solid #663333; color: #ff5252; border-radius: 14px; }
            QPushButton:hover { background: #ff5252; color: white; }
        """)
        self.btn_del.clicked.connect(on_remove)
        layout.addWidget(self.btn_del)

        self.lbl_prefix = QLabel(prefix)
        self.lbl_prefix.setFixedWidth(35)
        self.lbl_prefix.setStyleSheet("font-weight: bold; color: #00f2ff; font-size: 15px;")
        layout.addWidget(self.lbl_prefix)

        clean_text = re.sub(r'^[a-zA-Zأ-ي0-9]\s*[-.)]\s*', '', text).strip()
        self.line_edit = QLineEdit(clean_text)
        self.line_edit.setStyleSheet("background: #111; border: 1px solid #333; height: 35px; padding-left: 10px;")
        layout.addWidget(self.line_edit)

        self.radio = QRadioButton()
        self.radio.setChecked(is_correct)
        button_group.addButton(self.radio)
        self.radio.toggled.connect(lambda checked: checked and on_set_correct())
        layout.addWidget(self.radio)

class QuestionViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("menu_viewer"))
        self.resize(1200, 850)
        
        if ConfigManager.get_language() == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.current_bank_data = []
        self.current_bank_path = ""
        self.current_q_index = -1
        self.edit_mode = False
        self.temp_correct_idx = 0
        self.option_rows = []
        
        self.edit_mode_button_group = QButtonGroup(self)
        self.edit_mode_button_group.setExclusive(True)

        ConfigManager.load_window_state("viewer", self)
        self.apply_styles()
        self.init_ui()
        self.scan_banks_folder()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0c0c0c; }
            QWidget { font-family: 'Segoe UI'; color: #e0e0e0; }
            
            /* Inputs & ComboBox Theme */
            QLineEdit, QTextEdit, QComboBox { 
                background-color: #111; border: 1px solid #333; color: white; padding: 5px; border-radius: 5px; 
            }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid #00f2ff; margin-right: 10px; }
            QComboBox QAbstractItemView { background-color: #181818; selection-background-color: #00f2ff; selection-color: black; border: 1px solid #333; outline: none; }

            /* Glowing Checkbox & Radio Theme */
            QRadioButton::indicator, QCheckBox::indicator {
                width: 20px; height: 20px; border-radius: 10px; border: 2px solid #555; background-color: #1a1a1a;
            }
            QCheckBox::indicator { border-radius: 4px; }
            QRadioButton::indicator:checked, QCheckBox::indicator:checked {
                background-color: #00f2ff; border: 2px solid #ffffff;
            }

            /* Sidebar Theme */
            QListWidget { background-color: #111; border: none; border-right: 1px solid #222; outline: none; }
            QListWidget::item { padding: 18px; border-bottom: 1px solid #1a1a1a; color: #aaa; font-size: 14px; }
            QListWidget::item:selected { background-color: #181818; color: #00f2ff; border-left: 4px solid #00f2ff; font-weight: bold; }

            #Card { background-color: #161616; border-radius: 12px; border: 1px solid #252525; padding: 20px; }
            #AnsBox { background-color: #0f1a16; border: 1px solid #1a332a; border-radius: 8px; padding: 15px; }

            QPushButton { background-color: #222; border: 1px solid #333; padding: 8px 15px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #2a2a2a; border-color: #00f2ff; }
            
            #PrimaryBtn { background-color: #005a9e; border: none; color: white; }
            #PrimaryBtn:hover { background-color: #0078d4; }
            #DeleteBtn { color: #ff5252; background: transparent; border: none; font-size: 18px; }
            #DeleteBtn:hover { background: #331111; border-radius: 5px; }
        """)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(5, 5, 5, 10)
        lbl_bank = QLabel(tr("view_sel_folder"))
        lbl_bank.setStyleSheet("color: #777; font-weight: bold;")
        header.addWidget(lbl_bank)
        
        self.combo_banks = QComboBox()
        self.combo_banks.setMinimumWidth(250)
        self.combo_banks.currentIndexChanged.connect(self.on_bank_selected)
        header.addWidget(self.combo_banks)
        header.addStretch()
        
        self.chk_always_show = QCheckBox(tr("view_always_show"))
        self.chk_always_show.setChecked(True)
        header.addWidget(self.chk_always_show)

        btn_home = QPushButton("🏠 " + tr("home"))
        btn_home.clicked.connect(self.go_home)
        header.addWidget(btn_home)
        main_layout.addLayout(header)

        # Body
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sidebar with fixed numbering
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.load_question)
        splitter.addWidget(self.list_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(20, 10, 20, 20)

        # Question Card
        self.card = QFrame()
        self.card.setObjectName("Card")
        card_v = QVBoxLayout(self.card)

        head = QHBoxLayout()
        self.lbl_q_num = QLabel()
        self.lbl_q_num.setStyleSheet("font-size: 20px; font-weight: bold; color: #00f2ff;")
        head.addWidget(self.lbl_q_num)
        head.addStretch()
        self.btn_edit = QPushButton("✏️ " + tr("edit_btn"))
        self.btn_edit.clicked.connect(self.toggle_edit_mode)
        head.addWidget(self.btn_edit)
        self.btn_delete = QPushButton("🗑️")
        self.btn_delete.setObjectName("DeleteBtn")
        self.btn_delete.clicked.connect(self.delete_current_question)
        head.addWidget(self.btn_delete)
        card_v.addLayout(head)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background: #080808; border-radius: 6px; padding: 10px; min-height: 100px;")
        card_v.addWidget(self.img_label)

        self.img_tools = QWidget()
        it_lay = QHBoxLayout(self.img_tools)
        it_lay.setContentsMargins(0,5,0,5)
        self.btn_rep_img = QPushButton() # Text set dynamically in load_question
        self.btn_rep_img.clicked.connect(self.replace_image)
        self.btn_crop_img = QPushButton("✂️ " + tr("crop_img"))
        self.btn_crop_img.clicked.connect(self.open_cropper_for_image)
        it_lay.addWidget(self.btn_rep_img)
        it_lay.addWidget(self.btn_crop_img)
        it_lay.addStretch()
        self.img_tools.hide()
        card_v.addWidget(self.img_tools)

        self.q_text_lbl = QLabel()
        self.q_text_lbl.setWordWrap(True)
        self.q_text_lbl.setFont(QFont("Segoe UI", 13))
        self.q_text_edit = QTextEdit()
        self.q_text_edit.setMinimumHeight(120)
        self.q_text_edit.hide()
        card_v.addWidget(self.q_text_lbl)
        card_v.addWidget(self.q_text_edit)

        # Viewer Options
        self.opt_group_view = QButtonGroup(self)
        self.opt_group_view.buttonClicked.connect(self.on_option_clicked)
        self.opt_view_layout = QVBoxLayout()
        card_v.addLayout(self.opt_view_layout)

        # Editor Options
        self.edit_opt_container = QWidget()
        self.edit_opt_layout = QVBoxLayout(self.edit_opt_container)
        self.edit_opt_layout.setContentsMargins(0,0,0,0)
        self.edit_opt_container.hide()
        card_v.addWidget(self.edit_opt_container)
        
        self.btn_add_opt = QPushButton("➕ Add New Option")
        self.btn_add_opt.setStyleSheet("color: #00f2ff; border: 1px dashed #00f2ff; margin-top: 10px; height: 38px;")
        self.btn_add_opt.clicked.connect(lambda: self.add_option_row("", False))
        self.btn_add_opt.hide()
        card_v.addWidget(self.btn_add_opt)

        self.content_layout.addWidget(self.card)

        # Answer Box
        self.ans_box = QFrame()
        self.ans_box.setObjectName("AnsBox")
        ans_v = QVBoxLayout(self.ans_box)
        self.lbl_ans_status = QLabel()
        self.lbl_ans_status.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_expl = QLabel()
        self.lbl_expl.setWordWrap(True)
        self.lbl_expl.setStyleSheet("line-height: 1.4;")
        self.edit_expl = QTextEdit()
        self.edit_expl.hide()
        ans_v.addWidget(self.lbl_ans_status)
        ans_v.addWidget(self.lbl_expl)
        ans_v.addWidget(self.edit_expl)
        self.ans_box.hide()
        self.content_layout.addWidget(self.ans_box)

        # Action Buttons
        self.btn_reveal = QPushButton("👁️ " + tr("view_show_ans"))
        self.btn_reveal.setObjectName("PrimaryBtn")
        self.btn_reveal.setMinimumHeight(50)
        self.btn_reveal.clicked.connect(self.reveal_answer)
        self.content_layout.addWidget(self.btn_reveal)

        self.btn_save = QPushButton("💾 " + tr("save_changes"))
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.setMinimumHeight(50)
        self.btn_save.hide()
        self.btn_save.clicked.connect(self.save_changes)
        self.content_layout.addWidget(self.btn_save)

        self.content_layout.addStretch()
        scroll.setWidget(container)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter)

    # --- Scanning & Display ---
    def scan_banks_folder(self):
        self.combo_banks.clear()
        if not os.path.exists("banks"): os.makedirs("banks")
        dirs = sorted([d for d in os.listdir("banks") if os.path.isdir(os.path.join("banks", d))])
        if dirs: self.combo_banks.addItems(dirs)

    def on_bank_selected(self):
        name = self.combo_banks.currentText()
        self.current_bank_path = os.path.join("banks", name)
        p = os.path.join(self.current_bank_path, "bank.json")
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                self.current_bank_data = json.load(f)
            self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for i, q in enumerate(self.current_bank_data):
            raw_txt = q.get('question','?')
            # Distinct Sidebar numbering: Strip internal question numbers to avoid "9. 10."
            clean_txt = re.sub(r'^\d+\s*[-.)]\s*', '', raw_txt).strip()
            preview = clean_txt[:35].replace('\n', ' ')
            # Cleaner Sidebar UI format
            self.list_widget.addItem(f"Q{i+1:02} | {preview}...")
        if self.current_bank_data: self.list_widget.setCurrentRow(0)

    def load_question(self, index):
        if index < 0 or index >= len(self.current_bank_data): return
        self.current_q_index = index
        self.edit_mode = False
        self.update_ui_state()
        
        q = self.current_bank_data[index]
        self.lbl_q_num.setText(f"Question #{index+1}")
        
        img_p = os.path.join(self.current_bank_path, "images", f"{index+1}.jpg")
        if os.path.exists(img_p):
            pix = QPixmap(img_p)
            if pix.width() > 850: pix = pix.scaledToWidth(850, Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(pix)
            self.img_label.show()
            self.btn_rep_img.setText("🔄 " + tr("replace_img"))
        else:
            self.img_label.clear()
            self.img_label.hide()
            self.btn_rep_img.setText("➕ Add Image")
        
        self.q_text_lbl.setText(q.get("question", ""))
        
        for b in self.opt_group_view.buttons():
            self.opt_view_layout.removeWidget(b); b.deleteLater()
        
        for i, opt in enumerate(q.get("options", [])):
            rb = QRadioButton(opt)
            rb.setProperty("idx", i)
            self.opt_view_layout.addWidget(rb)
            self.opt_group_view.addButton(rb)

        self.ans_box.hide()
        if self.chk_always_show.isChecked(): self.reveal_answer()

    # --- Editing Logic ---
    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            q = self.current_bank_data[self.current_q_index]
            self.q_text_edit.setText(q.get("question", ""))
            self.temp_correct_idx = q.get("correct_options", [0])[0]
            self.edit_expl.setText(q.get("explanation", ""))
            
            while self.edit_opt_layout.count():
                it = self.edit_opt_layout.takeAt(0); it.widget().deleteLater()
            
            for btn in self.edit_mode_button_group.buttons():
                self.edit_mode_button_group.removeButton(btn)
            
            self.option_rows = []
            for i, opt in enumerate(q.get("options", [])):
                self.add_option_row(opt, i == self.temp_correct_idx)
            self.ans_box.show()
        
        self.update_ui_state()

    def add_option_row(self, text, is_correct):
        row_idx = len(self.option_rows)
        prefix = self.generate_prefix(row_idx)
        
        def on_remove():
            self.edit_mode_button_group.removeButton(row.radio)
            self.option_rows.remove(row); row.deleteLater()
            self.reorder_prefixes()

        def on_set():
            if row in self.option_rows: self.temp_correct_idx = self.option_rows.index(row)

        row = OptionEditRow(prefix, text, is_correct, on_remove, on_set, self.edit_mode_button_group)
        self.edit_opt_layout.addWidget(row)
        self.option_rows.append(row)
        self.reorder_prefixes()

    def generate_prefix(self, index):
        lang_ref = self.option_rows[0].line_edit.text() if self.option_rows else ""
        is_arabic = any("\u0600" <= c <= "\u06FF" for c in lang_ref)
        if is_arabic:
            chars = "أبجدهوزحطيكلمنسعفصقرشتثخذضظغ"
            char = chars[index] if index < len(chars) else "?"
        else:
            char = chr(ord('a') + index) if index < 26 else "?"
        return f"{char})"

    def reorder_prefixes(self):
        for i, row in enumerate(self.option_rows): row.lbl_prefix.setText(self.generate_prefix(i))

    def save_changes(self):
        q = self.current_bank_data[self.current_q_index]
        q['question'] = self.q_text_edit.toPlainText()
        q['explanation'] = self.edit_expl.toPlainText()
        
        final_opts = []
        for i, row in enumerate(self.option_rows):
            final_opts.append(f"{self.generate_prefix(i)} {row.line_edit.text().strip()}")
            if row.radio.isChecked(): self.temp_correct_idx = i
        
        q['options'] = final_opts
        q['correct_options'] = [self.temp_correct_idx]
        
        with open(os.path.join(self.current_bank_path, "bank.json"), 'w', encoding='utf-8') as f:
            json.dump(self.current_bank_data, f, indent=2, ensure_ascii=False)
            
        self.toggle_edit_mode(); self.load_question(self.current_q_index); self.refresh_list()

    # --- UI Helpers ---
    def update_ui_state(self):
        v = self.edit_mode
        self.q_text_lbl.setVisible(not v); self.q_text_edit.setVisible(v)
        self.edit_opt_container.setVisible(v); self.btn_add_opt.setVisible(v); self.img_tools.setVisible(v)
        for b in self.opt_group_view.buttons(): b.setVisible(not v)
        self.lbl_ans_status.setVisible(not v); self.lbl_expl.setVisible(not v); self.edit_expl.setVisible(v)
        self.btn_reveal.setVisible(not v); self.btn_save.setVisible(v)
        self.btn_edit.setText("✔️ " + tr("cancel") if v else "✏️ " + tr("edit_btn"))

    def reveal_answer(self):
        q = self.current_bank_data[self.current_q_index]
        correct = q.get("correct_options", [0])[0]
        for b in self.opt_group_view.buttons():
            if b.property("idx") == correct: b.setStyleSheet("color: #00f2ff; font-weight: bold;")
            else: b.setStyleSheet("")
        self.lbl_expl.setText(f"<b>{tr('view_ans_header')}</b> Option {correct+1}<br><br>{q.get('explanation','')}")
        self.ans_box.show()

    def on_option_clicked(self, btn):
        if self.edit_mode: return
        correct = self.current_bank_data[self.current_q_index].get("correct_options", [0])[0]
        if btn.property("idx") == correct:
            self.lbl_ans_status.setText("✅ " + tr("view_correct")); self.lbl_ans_status.setStyleSheet("color: #4CAF50;")
            self.reveal_answer()
        else:
            self.lbl_ans_status.setText("❌ " + tr("view_wrong")); self.lbl_ans_status.setStyleSheet("color: #ff5252;")
            self.ans_box.show()

    # --- External Image Handling ---
    def replace_image(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("replace_img"), "", "Images (*.jpg *.png)")
        if f:
            dest = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}.jpg")
            if not os.path.exists(os.path.dirname(dest)): os.makedirs(os.path.dirname(dest))
            shutil.copy(f, dest); self.load_question(self.current_q_index)

    def open_cropper_for_image(self):
        from ui.window import ImageCropperApp
        img_p = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}.jpg")
        if not os.path.exists(img_p):
            # If no image exists, we can't crop. We could show a message or do nothing.
            return
        self.cropper_ref = ImageCropperApp(single_image_mode=True)
        self.cropper_ref.load_single_image(img_p)
        self.cropper_ref.show()

    def delete_current_question(self):
        if QMessageBox.question(self, tr("delete"), tr("confirm_delete")) != QMessageBox.StandardButton.Yes: return
        idx = self.current_q_index
        self.current_bank_data.pop(idx)
        img_dir = os.path.join(self.current_bank_path, "images")
        t_img = os.path.join(img_dir, f"{idx+1}.jpg")
        if os.path.exists(t_img): os.remove(t_img)
        curr = idx + 2
        while True:
            old = os.path.join(img_dir, f"{curr}.jpg")
            if not os.path.exists(old): break
            shutil.move(old, os.path.join(img_dir, f"{curr-1}.jpg")); curr += 1
        with open(os.path.join(self.current_bank_path, "bank.json"), 'w', encoding='utf-8') as f:
            json.dump(self.current_bank_data, f, indent=2, ensure_ascii=False)
        self.refresh_list(); self.load_question(min(idx, len(self.current_bank_data)-1))

    def go_home(self):
        from ui.menu import MainMenu
        self.menu = MainMenu(None); self.menu.show(); self.close()

    def keyPressEvent(self, e):
        if self.edit_mode: return super().keyPressEvent(e)
        if e.key() == Qt.Key.Key_Space: self.reveal_answer()
        elif e.key() == Qt.Key.Key_Left: self.list_widget.setCurrentRow(max(0, self.current_q_index-1))
        elif e.key() == Qt.Key.Key_Right: self.list_widget.setCurrentRow(min(len(self.current_bank_data)-1, self.current_q_index+1))
        super().keyPressEvent(e)
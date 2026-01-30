import os
import json
import shutil
import re
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QSplitter, 
                             QScrollArea, QRadioButton, QButtonGroup, QFrame,
                             QComboBox, QMessageBox, QCheckBox, QLineEdit,
                             QTextEdit, QFileDialog, QScrollBar)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont
from core.config import ConfigManager
from ui.common import tr

class OptionEditRow(QWidget):
    def __init__(self, prefix, text, is_correct, on_remove, on_set_correct, button_group):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)

        self.btn_del = QPushButton("✕")
        self.btn_del.setFixedSize(32, 32)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setStyleSheet("""
            QPushButton { 
                background-color: #3e2020; border: 1px solid #552222; 
                color: #ff6b6b; border-radius: 6px; font-weight: bold; font-size: 16px;
            }
            QPushButton:hover { background-color: #d32f2f; color: white; border-color: #d32f2f; }
        """)
        self.btn_del.clicked.connect(on_remove)
        layout.addWidget(self.btn_del)

        self.lbl_prefix = QLabel(prefix)
        self.lbl_prefix.setFixedWidth(35)
        self.lbl_prefix.setStyleSheet("color: #4da3ff; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.lbl_prefix)

        clean_text = re.sub(r'^[a-zA-Zأ-ي0-9]\s*[-.)]\s*', '', text).strip()
        self.line_edit = QLineEdit(clean_text)
        
        # EDIT: Option Text (Optional) translation
        ph_text = "نص الخيار (اختياري)..." if ConfigManager.get_language() == "ar" else "Option text (optional)..."
        self.line_edit.setPlaceholderText(ph_text)
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

    def closeEvent(self, event):
        ConfigManager.save_window_state("viewer", self)
        super().closeEvent(event)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 10px;
                color: #ffffff;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #4da3ff;
                background-color: #333;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                color: #ddd;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #505050; border-color: #4da3ff; color: white;
            }
            QPushButton#PrimaryBtn {
                background-color: #1565C0; border: 1px solid #0D47A1;
                color: white; font-weight: bold; font-size: 17px; border-radius: 8px;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #1976D2; border-color: #42a5f5;
            }
            QPushButton#DeleteBtn {
                background-color: #3e2020; border: 1px solid #552222; color: #ff6b6b;
            }
            QListWidget {
                background-color: #252525; border-right: 1px solid #333; outline: none;
            }
            QListWidget::item { padding: 12px 10px; border-bottom: 1px solid #2f2f2f; color: #bbb; }
            QListWidget::item:selected {
                background-color: #383838; color: #4da3ff; border-left: 4px solid #4da3ff; font-weight: bold;
            }
            QFrame#Card {
                background-color: #2d2d2d; border-radius: 12px; border: 1px solid #444;
            }
            QFrame#AnsBox {
                background-color: #202b26; border: 1px solid #2e7d32; border-radius: 8px; margin-top: 15px;
            }
            QLabel#AnsTitle { color: #66bb6a; font-weight: bold; font-size: 18px; margin-bottom: 5px; }
            
            /* --- Improved Radio & Checkbox Styles --- */
            QRadioButton { spacing: 10px; padding: 5px; border-radius: 4px; }
            QRadioButton::indicator { width: 20px; height: 20px; border: 2px solid #666; border-radius: 12px; }
            QRadioButton::indicator:checked { background-color: #4da3ff; border-color: #4da3ff; }

            QCheckBox { spacing: 10px; color: #ddd; }
            QCheckBox::indicator {
                width: 22px; height: 22px;
                background-color: #333;
                border: 2px solid #555;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #1565C0;
                border-color: #4da3ff;
                image: url(ui/resources/check_white.png); /* Fallback to a drawn tick if missing */
            }
            QCheckBox::indicator:hover {
                border-color: #4da3ff;
            }
        """)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Header ---
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #252525; border-bottom: 1px solid #333;")
        # EDIT: Set a fixed height for the bar so it doesn't take half the screen
        header_widget.setFixedHeight(75)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        lbl_bank = QLabel(tr("view_sel_folder"))
        lbl_bank.setStyleSheet("color: #ccc; font-weight: bold; border: none;")
        header_layout.addWidget(lbl_bank)
        
        self.combo_banks = QComboBox()
        self.combo_banks.setMinimumWidth(250)
        self.combo_banks.currentIndexChanged.connect(self.on_bank_selected)
        header_layout.addWidget(self.combo_banks)
        
        header_layout.addStretch()
        
        # EDIT: Show answer auto checked by default and styled
        self.chk_always_show = QCheckBox(tr("view_always_show"))
        self.chk_always_show.setChecked(True)
        header_layout.addWidget(self.chk_always_show)

        btn_home = QPushButton("🏠 " + tr("home"))
        btn_home.setStyleSheet("background-color: #00796b; border: none; font-weight: bold;")
        btn_home.clicked.connect(self.go_home)
        header_layout.addWidget(btn_home)
        
        main_layout.addWidget(header_widget)

        # --- Splitter Body ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #111; }")

        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.currentRowChanged.connect(self.load_question)
        splitter.addWidget(self.list_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: #1e1e1e; }")
        
        content_container = QWidget()
        content_container.setStyleSheet("background-color: #1e1e1e;") 
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setContentsMargins(40, 30, 40, 40)
        self.content_layout.setSpacing(25)

        # 1. Question Card
        self.card = QFrame()
        self.card.setObjectName("Card")
        card_v = QVBoxLayout(self.card)
        card_v.setSpacing(20)
        card_v.setContentsMargins(30, 30, 30, 30)

        head = QHBoxLayout()
        self.lbl_q_num = QLabel()
        self.lbl_q_num.setStyleSheet("font-size: 24px; font-weight: bold; color: #4da3ff; border: none; background: transparent;")
        head.addWidget(self.lbl_q_num)
        head.addStretch()
        
        self.btn_edit = QPushButton("✏️ " + tr("edit_btn"))
        self.btn_edit.clicked.connect(self.toggle_edit_mode)
        head.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("🗑️ " + tr("delete"))
        self.btn_delete.setObjectName("DeleteBtn")
        self.btn_delete.setFixedWidth(120) 
        self.btn_delete.clicked.connect(self.delete_current_question)
        head.addWidget(self.btn_delete)
        card_v.addLayout(head)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background: #000; border-radius: 6px; border: 1px solid #444; padding: 5px;")
        self.img_label.hide()
        card_v.addWidget(self.img_label)

        # EDIT: Image Tools - Add color and translations
        self.img_tools = QWidget()
        self.img_tools.setStyleSheet("background: transparent; border: none;")
        it_lay = QHBoxLayout(self.img_tools)
        it_lay.setContentsMargins(0,0,0,0)
        
        img_btn_style = "background-color: #263238; border: 1px solid #37474f; font-weight: bold;"
        self.btn_rep_img = QPushButton() 
        self.btn_rep_img.setStyleSheet(img_btn_style)
        self.btn_rep_img.clicked.connect(self.replace_image)
        
        crop_txt = "✂️ " + ("قص الصورة" if ConfigManager.get_language() == "ar" else "Crop Image")
        self.btn_crop_img = QPushButton(crop_txt)
        self.btn_crop_img.setStyleSheet(img_btn_style)
        self.btn_crop_img.clicked.connect(self.open_cropper_for_image)
        
        it_lay.addWidget(self.btn_rep_img)
        it_lay.addWidget(self.btn_crop_img)
        it_lay.addStretch()
        self.img_tools.hide()
        card_v.addWidget(self.img_tools)

        self.q_text_lbl = QLabel()
        self.q_text_lbl.setWordWrap(True)
        self.q_text_lbl.setStyleSheet("font-size: 19px; line-height: 1.6; font-weight: 500; border: none; background: transparent;")
        self.q_text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        self.q_text_edit = QTextEdit()
        self.q_text_edit.setMinimumHeight(120)
        self.q_text_edit.hide()
        card_v.addWidget(self.q_text_lbl)
        card_v.addWidget(self.q_text_edit)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #444; border: none; max-height: 1px;")
        card_v.addWidget(line)

        self.opt_group_view = QButtonGroup(self)
        self.opt_group_view.buttonClicked.connect(self.on_option_clicked)
        self.opt_view_layout = QVBoxLayout()
        self.opt_view_layout.setSpacing(12)
        card_v.addLayout(self.opt_view_layout)

        self.edit_opt_container = QWidget()
        self.edit_opt_layout = QVBoxLayout(self.edit_opt_container)
        self.edit_opt_layout.setContentsMargins(0,0,0,0)
        self.edit_opt_container.hide()
        card_v.addWidget(self.edit_opt_container)
        
        # EDIT: Translate Add Option
        add_opt_txt = "➕ " + ("إضافة خيار" if ConfigManager.get_language() == "ar" else "Add Option")
        self.btn_add_opt = QPushButton(add_opt_txt)
        self.btn_add_opt.setStyleSheet("background-color: #333; border: 1px dashed #666; color: #aaa; padding: 12px;")
        self.btn_add_opt.clicked.connect(lambda: self.add_option_row("", False))
        self.btn_add_opt.hide()
        card_v.addWidget(self.btn_add_opt)

        self.content_layout.addWidget(self.card)

        # 2. Answer Box
        self.ans_box = QFrame()
        self.ans_box.setObjectName("AnsBox")
        ans_v = QVBoxLayout(self.ans_box)
        ans_v.setContentsMargins(25, 25, 25, 25)
        ans_v.setSpacing(10)
        
        self.lbl_ans_status = QLabel()
        self.lbl_ans_status.setObjectName("AnsTitle")
        
        self.lbl_expl = QLabel()
        self.lbl_expl.setWordWrap(True)
        self.lbl_expl.setStyleSheet("color: #ddd; font-size: 16px; line-height: 1.5; border: none; background: transparent;")
        self.lbl_expl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        self.edit_expl = QTextEdit()
        self.edit_expl.setMinimumHeight(100)
        self.edit_expl.hide()
        
        ans_v.addWidget(self.lbl_ans_status)
        ans_v.addWidget(self.lbl_expl)
        ans_v.addWidget(self.edit_expl)
        self.ans_box.hide()
        self.content_layout.addWidget(self.ans_box)

        # 3. Action Buttons
        h_actions = QHBoxLayout()
        h_actions.setSpacing(15)
        
        self.btn_reveal = QPushButton("👁️ " + tr("view_show_ans"))
        self.btn_reveal.setObjectName("PrimaryBtn")
        self.btn_reveal.setMinimumHeight(55)
        self.btn_reveal.clicked.connect(self.reveal_answer)
        h_actions.addWidget(self.btn_reveal)

        self.btn_save = QPushButton("💾 " + tr("save_changes"))
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.setMinimumHeight(55)
        self.btn_save.hide()
        self.btn_save.clicked.connect(self.save_changes)
        h_actions.addWidget(self.btn_save)
        
        self.content_layout.addLayout(h_actions)
        self.content_layout.addStretch()
        
        self.scroll_area.setWidget(content_container)
        splitter.addWidget(self.scroll_area)
        
        # EDIT: Ensure the splitter takes up the remaining height
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter, 1)

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
        else:
            self.current_bank_data = []
            self.list_widget.clear()

    def refresh_list(self):
        self.list_widget.clear()
        for i, q in enumerate(self.current_bank_data):
            raw_txt = q.get('question','?')
            clean_txt = re.sub(r'^\d+\s*[-.)]\s*', '', raw_txt).strip()
            preview = clean_txt[:30].replace('\n', ' ')
            self.list_widget.addItem(f"{i+1}. {preview}...")
        if self.current_bank_data: self.list_widget.setCurrentRow(0)

    def load_question(self, index):
        if index < 0 or index >= len(self.current_bank_data): return
        self.current_q_index = index
        self.edit_mode = False
        self.update_ui_state()
        
        q = self.current_bank_data[index]
        is_ar = ConfigManager.get_language() == "ar"
        
        if is_ar:
            self.lbl_q_num.setText(f"سؤال رقم {index+1}")
            self.lbl_q_num.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            self.lbl_q_num.setText(f"Question #{index+1}")
            self.lbl_q_num.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        img_p = os.path.join(self.current_bank_path, "images", f"{index+1}.jpg")
        if os.path.exists(img_p):
            pix = QPixmap(img_p)
            if pix.width() > 900: pix = pix.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(pix)
            self.img_label.show()
            self.btn_rep_img.setText("🔄 " + (tr("replace_img") if tr("replace_img") != "replace_img" else "Replace Image"))
        else:
            self.img_label.clear()
            self.img_label.hide()
            self.btn_rep_img.setText("➕ " + ("إضافة صورة" if is_ar else "Add Image"))
        
        self.q_text_lbl.setText(q.get("question", ""))
        if is_ar: self.q_text_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        for b in self.opt_group_view.buttons():
            self.opt_view_layout.removeWidget(b); b.deleteLater()
        
        for i, opt in enumerate(q.get("options", [])):
            rb = QRadioButton(opt)
            rb.setProperty("idx", i)
            rb.setStyleSheet("font-size: 16px; padding: 6px;")
            self.opt_view_layout.addWidget(rb)
            self.opt_group_view.addButton(rb)

        self.ans_box.hide()
        if self.chk_always_show.isChecked(): self.reveal_answer()

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        q = self.current_bank_data[self.current_q_index]

        if self.edit_mode:
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
            self.lbl_ans_status.setText("تعديل الشرح:" if ConfigManager.get_language() == "ar" else "Editing Explanation:")
            self.lbl_ans_status.setStyleSheet("color: #4da3ff;")
        else:
            self.load_question(self.current_q_index)
            return

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
        chars = "abcdefghijklmnopqrstuvwxyz"
        if index < len(chars): return f"{chars[index]})"
        return f"{index+1})"

    def reorder_prefixes(self):
        for i, row in enumerate(self.option_rows): row.lbl_prefix.setText(self.generate_prefix(i))

    def save_changes(self):
        q = self.current_bank_data[self.current_q_index]
        q['question'] = self.q_text_edit.toPlainText()
        q['explanation'] = self.edit_expl.toPlainText()
        
        final_opts = []
        for i, row in enumerate(self.option_rows):
            txt = row.line_edit.text().strip()
            final_opts.append(f"{self.generate_prefix(i)} {txt}")
            if row.radio.isChecked(): self.temp_correct_idx = i
        
        q['options'] = final_opts
        q['correct_options'] = [self.temp_correct_idx]
        
        with open(os.path.join(self.current_bank_path, "bank.json"), 'w', encoding='utf-8') as f:
            json.dump(self.current_bank_data, f, indent=2, ensure_ascii=False)
            
        self.toggle_edit_mode(); self.load_question(self.current_q_index); self.refresh_list()

    def update_ui_state(self):
        v = self.edit_mode
        self.q_text_lbl.setVisible(not v); self.q_text_edit.setVisible(v)
        self.edit_opt_container.setVisible(v); self.btn_add_opt.setVisible(v); self.img_tools.setVisible(v)
        
        for i in range(self.opt_view_layout.count()):
            w = self.opt_view_layout.itemAt(i).widget()
            if w: w.setVisible(not v)
            
        self.lbl_expl.setVisible(not v); self.edit_expl.setVisible(v)
        self.btn_reveal.setVisible(not v); self.btn_save.setVisible(v)
        
        if v:
            self.btn_edit.setText("↩ " + tr("cancel"))
            self.btn_edit.setStyleSheet("background-color: #555;")
        else:
            self.btn_edit.setText("✏️ " + tr("edit_btn"))
            self.btn_edit.setStyleSheet("")

    def reveal_answer(self):
        q = self.current_bank_data[self.current_q_index]
        correct = q.get("correct_options", [0])[0]
        is_ar = ConfigManager.get_language() == "ar"
        
        for b in self.opt_group_view.buttons():
            idx = b.property("idx")
            if idx == correct:
                b.setStyleSheet("color: #66bb6a; font-weight: bold; font-size: 17px; border: 1px solid #66bb6a; border-radius: 4px;")
            else:
                b.setStyleSheet("color: #999; font-size: 16px;")
        
        # EDIT: Correct Arabic Translation for Answer Box
        self.lbl_ans_status.setText("✅ " + (tr("view_ans_header") if tr("view_ans_header") != "view_ans_header" else "الإجابة الصحيحة:"))
        self.lbl_ans_status.setStyleSheet("color: #66bb6a; font-weight: bold;")
        
        expl_text = q.get('explanation', '').strip()
        
        # Arabic labels for the answer box
        expl_header = "الشرح:" if is_ar else "Explanation:"
        no_expl_txt = "لا يوجد شرح لهذا السؤال." if is_ar else "No explanation provided."
        ans_txt_label = "الإجابة الصحيحة: الخيار" if is_ar else "Correct Answer: Option"

        if not expl_text: expl_text = f"<i>{no_expl_txt}</i>"
        
        self.lbl_expl.setText(f"<b>{ans_txt_label} {correct+1}</b><br><br><b>{expl_header}</b><br>{expl_text}")
        
        self.ans_box.show()
        if self.scroll_area.verticalScrollBar():
             self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def on_option_clicked(self, btn):
        if self.edit_mode: return
        correct = self.current_bank_data[self.current_q_index].get("correct_options", [0])[0]
        
        if btn.property("idx") == correct:
            self.reveal_answer()
        else:
            is_ar = ConfigManager.get_language() == "ar"
            wrong_title = "إجابة خاطئة" if is_ar else "Wrong Answer"
            wrong_msg = "حاول مرة أخرى أو اضغط على 'إظهار الإجابة'." if is_ar else "Try again or click 'Show Answer'."
            
            self.lbl_ans_status.setText(f"❌ {wrong_title}") 
            self.lbl_ans_status.setStyleSheet("color: #ef5350; font-weight: bold;")
            self.lbl_expl.setText(wrong_msg)
            self.ans_box.show()

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
            QMessageBox.warning(self, "Error", "No image exists for this question.")
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
            
        self.refresh_list()
        next_idx = min(idx, len(self.current_bank_data)-1)
        if next_idx >= 0: self.load_question(next_idx)

    def go_home(self):
        from ui.menu import MainMenu
        self.menu = MainMenu(None); self.menu.show(); self.close()

    def keyPressEvent(self, e):
        if self.edit_mode: return super().keyPressEvent(e)
        if e.key() == Qt.Key.Key_Space: self.reveal_answer()
        elif e.key() == Qt.Key.Key_Left: 
            if self.list_widget.currentRow() > 0:
                self.list_widget.setCurrentRow(self.list_widget.currentRow() - 1)
        elif e.key() == Qt.Key.Key_Right: 
             if self.list_widget.currentRow() < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(self.list_widget.currentRow() + 1)
        super().keyPressEvent(e)
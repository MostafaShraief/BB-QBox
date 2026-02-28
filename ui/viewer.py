# --- START OF FILE ui/viewer.py ---
import os
import json
import shutil
import re
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QSplitter, 
                             QScrollArea, QRadioButton, QButtonGroup, QFrame,
                             QComboBox, QMessageBox, QCheckBox, QLineEdit,
                             QTextEdit, QFileDialog, QMenu, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut
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

        clean_text = re.sub(r'^[a-zA-Zأ-ي0-9]\s*[-.)]\s*', '', str(text)).strip()
        self.line_edit = QLineEdit(clean_text)
        
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
        self.valid_indices = [] 
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
        self.setup_shortcuts()
        self.scan_banks_folder()

    def closeEvent(self, event):
        ConfigManager.save_window_state("viewer", self)
        super().closeEvent(event)

    def setup_shortcuts(self):
        self.short_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.short_left.activated.connect(self.nav_prev)
        
        self.short_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.short_right.activated.connect(self.nav_next)
        
        self.short_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.short_space.activated.connect(self.reveal_answer)

    def set_nav_shortcuts_enabled(self, enabled):
        self.short_left.setEnabled(enabled)
        self.short_right.setEnabled(enabled)
        self.short_space.setEnabled(enabled)

    def nav_prev(self):
        if self.list_widget.currentRow() > 0:
            self.list_widget.setCurrentRow(self.list_widget.currentRow() - 1)

    def nav_next(self):
        if self.list_widget.currentRow() < self.list_widget.count() - 1:
            self.list_widget.setCurrentRow(self.list_widget.currentRow() + 1)

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
                image: url(ui/resources/check_white.png); 
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
        header_widget.setFixedHeight(75)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        lbl_bank = QLabel(tr("view_sel_folder"))
        lbl_bank.setStyleSheet("color: #ccc; font-weight: bold; border: none;")
        header_layout.addWidget(lbl_bank)
        
        self.combo_banks = QComboBox()
        self.combo_banks.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combo_banks.setMinimumWidth(250)
        self.combo_banks.currentIndexChanged.connect(self.on_bank_selected)
        header_layout.addWidget(self.combo_banks)
        
        header_layout.addStretch()
        
        self.chk_always_show = QCheckBox(tr("view_always_show"))
        self.chk_always_show.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chk_always_show.setChecked(True)
        header_layout.addWidget(self.chk_always_show)

        btn_home = QPushButton("🏠 " + tr("home"))
        btn_home.setStyleSheet("background-color: #00796b; border: none; font-weight: bold;")
        btn_home.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        splitter.addWidget(self.list_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.btn_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_edit.clicked.connect(self.toggle_edit_mode)
        head.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("🗑️ " + tr("delete"))
        self.btn_delete.setObjectName("DeleteBtn")
        self.btn_delete.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_delete.setFixedWidth(120) 
        self.btn_delete.clicked.connect(self.delete_current_question)
        head.addWidget(self.btn_delete)
        card_v.addLayout(head)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background: #000; border-radius: 6px; border: 1px solid #444; padding: 5px;")
        self.img_label.hide()
        card_v.addWidget(self.img_label)

        self.img_tools = QWidget()
        self.img_tools.setStyleSheet("background: transparent; border: none;")
        it_lay = QHBoxLayout(self.img_tools)
        it_lay.setContentsMargins(0,0,0,0)
        
        img_btn_style = "background-color: #263238; border: 1px solid #37474f; font-weight: bold;"
        self.btn_rep_img = QPushButton() 
        self.btn_rep_img.setStyleSheet(img_btn_style)
        self.btn_rep_img.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_rep_img.clicked.connect(self.replace_image)
        
        crop_txt = "✂️ " + ("قص الصورة" if ConfigManager.get_language() == "ar" else "Crop Image")
        self.btn_crop_img = QPushButton(crop_txt)
        self.btn_crop_img.setStyleSheet(img_btn_style)
        self.btn_crop_img.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_crop_img.clicked.connect(self.open_cropper_for_image)

        self.btn_del_img = QPushButton("🗑️")
        self.btn_del_img.setFixedSize(38, 38)
        self.btn_del_img.setStyleSheet("background-color: #3e2020; border: 1px solid #552222; color: #ff6b6b; border-radius: 6px; font-weight: bold;")
        self.btn_del_img.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_del_img.clicked.connect(self.delete_image)
        
        it_lay.addWidget(self.btn_rep_img)
        it_lay.addWidget(self.btn_crop_img)
        it_lay.addWidget(self.btn_del_img)
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
        
        add_opt_txt = "➕ " + ("إضافة خيار" if ConfigManager.get_language() == "ar" else "Add Option")
        self.btn_add_opt = QPushButton(add_opt_txt)
        self.btn_add_opt.setStyleSheet("background-color: #333; border: 1px dashed #666; color: #aaa; padding: 12px;")
        self.btn_add_opt.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        
        self.note_img_label = QLabel()
        self.note_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note_img_label.setStyleSheet("background: #000; border-radius: 6px; border: 1px solid #444; padding: 5px;")
        self.note_img_label.hide()
        
        # Tools for note image directly
        self.note_img_tools = QWidget()
        self.note_img_tools.setStyleSheet("background: transparent; border: none;")
        nit_lay = QHBoxLayout(self.note_img_tools)
        nit_lay.setContentsMargins(0,0,0,0)
        
        self.btn_rep_note_img = QPushButton() 
        self.btn_rep_note_img.setStyleSheet(img_btn_style)
        self.btn_rep_note_img.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_rep_note_img.clicked.connect(self.replace_note_image)
        
        self.btn_crop_note_img = QPushButton(crop_txt)
        self.btn_crop_note_img.setStyleSheet(img_btn_style)
        self.btn_crop_note_img.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_crop_note_img.clicked.connect(self.open_cropper_for_note_image)

        self.btn_del_note_img = QPushButton("🗑️")
        self.btn_del_note_img.setFixedSize(38, 38)
        self.btn_del_note_img.setStyleSheet("background-color: #3e2020; border: 1px solid #552222; color: #ff6b6b; border-radius: 6px; font-weight: bold;")
        self.btn_del_note_img.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_del_note_img.clicked.connect(self.delete_note_image)
        
        nit_lay.addWidget(self.btn_rep_note_img)
        nit_lay.addWidget(self.btn_crop_note_img)
        nit_lay.addWidget(self.btn_del_note_img)
        nit_lay.addStretch()
        self.note_img_tools.hide()
        
        self.edit_expl = QTextEdit()
        self.edit_expl.setMinimumHeight(100)
        self.edit_expl.hide()
        
        ans_v.addWidget(self.lbl_ans_status)
        ans_v.addWidget(self.lbl_expl)
        ans_v.addWidget(self.note_img_label)
        ans_v.addWidget(self.note_img_tools)
        ans_v.addWidget(self.edit_expl)
        self.ans_box.hide()
        self.content_layout.addWidget(self.ans_box)

        # 3. Action Buttons
        h_actions = QHBoxLayout()
        h_actions.setSpacing(15)
        
        self.btn_reveal = QPushButton("👁️ " + tr("view_show_ans"))
        self.btn_reveal.setObjectName("PrimaryBtn")
        self.btn_reveal.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reveal.setMinimumHeight(55)
        self.btn_reveal.clicked.connect(self.reveal_answer)
        h_actions.addWidget(self.btn_reveal)

        self.btn_save = QPushButton("💾 " + tr("save_changes"))
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_save.setMinimumHeight(55)
        self.btn_save.hide()
        self.btn_save.clicked.connect(self.save_changes)
        h_actions.addWidget(self.btn_save)
        
        self.content_layout.addLayout(h_actions)
        self.content_layout.addStretch()
        
        self.scroll_area.setWidget(content_container)
        splitter.addWidget(self.scroll_area)
        
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
            self.refresh_list(-1)
        else:
            self.current_bank_data =[]
            self.list_widget.clear()

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        
        menu = QMenu(self)
        is_ar = ConfigManager.get_language() == "ar"
        
        act_edit = menu.addAction("✏️ " + tr("edit_btn"))
        act_del = menu.addAction("🗑️ " + tr("delete"))
        menu.addSeparator()
        act_ins_before = menu.addAction("⬆️ " + ("إدراج سؤال قبل" if is_ar else "Insert question before"))
        act_ins_after = menu.addAction("⬇️ " + ("إدراج سؤال بعد" if is_ar else "Insert question after"))
        menu.addSeparator()
        act_inc = menu.addAction("+1 " + ("زيادة ترقيم األسئلة من هنا" if is_ar else "Increase numbering from here"))
        act_dec = menu.addAction("-1 " + ("إنقاص ترقيم األسئلة من هنا" if is_ar else "Decrease numbering from here"))
        
        action = menu.exec(self.list_widget.viewport().mapToGlobal(pos))
        
        # Ensure we work on the clicked item's index, not necessarily the 'current' selected one if they differ
        clicked_index = self.list_widget.row(item)
        if clicked_index != -1:
            self.list_widget.setCurrentRow(clicked_index)
            
        if action == act_edit:
            if not self.edit_mode:
                self.toggle_edit_mode()
        elif action == act_del:
            self.delete_current_question()
        elif action == act_ins_before:
            self.insert_question(after=False)
        elif action == act_ins_after:
            self.insert_question(after=True)
        elif action == act_inc:
            self.manual_renumber(1)
        elif action == act_dec:
            self.manual_renumber(-1)

    def refresh_list(self, current_actual_index=-1):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self.valid_indices = []
        
        visible_count = 1
        for i, q in enumerate(self.current_bank_data):
            q_text = re.sub(r'^[\d\s\-.)]+', '', q.get("question", "")).strip()
            # If totally empty from text extractor, we just hide it from Viewer.
            if not q.get("options") and not q.get("explanation") and not q_text:
                continue
                
            self.valid_indices.append(i)
            raw_txt = q.get('question','?')
            clean_txt = re.sub(r'^\d+\s*[-.)]\s*', '', raw_txt).strip()
            preview = clean_txt[:30].replace('\n', ' ')
            self.list_widget.addItem(f"{visible_count}. {preview}...")
            visible_count += 1
            
        self.list_widget.blockSignals(False)
        
        if self.valid_indices:
            list_idx_to_select = 0
            if current_actual_index >= 0:
                try:
                    list_idx_to_select = self.valid_indices.index(current_actual_index)
                except ValueError:
                    list_idx_to_select = min(0, len(self.valid_indices)-1)
                    
            self.list_widget.setCurrentRow(list_idx_to_select)
            self.load_question(list_idx_to_select)

    def load_question(self, list_index):
        if list_index < 0 or list_index >= len(self.valid_indices): return
        actual_index = self.valid_indices[list_index]
        self.current_q_index = actual_index
        
        self.edit_mode = False
        self.update_ui_state()
        self.set_nav_shortcuts_enabled(True)
        
        q = self.current_bank_data[actual_index]
        is_ar = ConfigManager.get_language() == "ar"
        
        # Use visible list_index + 1 to match the sidebar counter
        display_num = list_index + 1
        
        if is_ar:
            self.lbl_q_num.setText(f"سؤال رقم {display_num}")
            self.lbl_q_num.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            self.lbl_q_num.setText(f"Question #{display_num}")
            self.lbl_q_num.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # ... (rest of the method remains the same)
        img_p = os.path.join(self.current_bank_path, "images", f"{actual_index+1}.jpg")
        if os.path.exists(img_p):
            pix = QPixmap(img_p)
            if pix.width() > 900: pix = pix.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(pix)
            self.img_label.show()
            self.btn_rep_img.setText("🔄 " + (tr("replace_img") if tr("replace_img") != "replace_img" else "Replace Image"))
            self.btn_del_img.show()
        else:
            self.img_label.clear()
            self.img_label.hide()
            self.btn_rep_img.setText("➕ " + ("إضافة صورة" if is_ar else "Add Image"))
            self.btn_del_img.hide()

        note_img_p = os.path.join(self.current_bank_path, "images", f"{actual_index+1}_note.jpg")
        if os.path.exists(note_img_p):
            pix = QPixmap(note_img_p)
            if pix.width() > 900: pix = pix.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)
            self.note_img_label.setPixmap(pix)
            self.note_img_label.show()
            self.btn_rep_note_img.setText("🔄 " + (tr("replace_img") if tr("replace_img") != "replace_img" else "Replace Image"))
            self.btn_del_note_img.show()
        else:
            self.note_img_label.hide()
            self.btn_rep_note_img.setText("➕ " + ("إضافة صورة ملاحظة" if is_ar else "Add Note Image"))
            self.btn_del_note_img.hide()
            
        self.q_text_lbl.setText(q.get("question", ""))
        if is_ar: self.q_text_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        for b in self.opt_group_view.buttons():
            self.opt_view_layout.removeWidget(b); b.deleteLater()
        
        for i, opt in enumerate(q.get("options",[])):
            rb = QRadioButton(str(opt))
            rb.setProperty("idx", i)
            rb.setStyleSheet("font-size: 16px; padding: 6px;")
            rb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.opt_view_layout.addWidget(rb)
            self.opt_group_view.addButton(rb)

        self.ans_box.hide()
        self.note_img_label.hide()
        if self.chk_always_show.isChecked(): self.reveal_answer()
        
        QTimer.singleShot(0, lambda: self.scroll_area.verticalScrollBar().setValue(0))

    def _validate_numbering(self, start_idx):
        """Checks if questions from start_idx onwards have valid numbering formats based on JSON string ONLY."""
        for i in range(start_idx, len(self.current_bank_data)):
            q = self.current_bank_data[i]
            q_text = q.get("question", "").strip()
            # If text is empty, it's fine, we just skip it (as per prompt "if empty... no problem")
            if not q_text:
                continue
            
            # Match strict number at start of string
            match = re.match(r'^(\d+)(\s*[-.)]\s*)', q_text)
            if not match:
                # Warning and abort
                QMessageBox.warning(self, "Format Error", 
                    f"Cannot adjust numbering automatically.\n"
                    f"Question at index {i+1} does not start with a recognized number format:\n\n"
                    f"'{q_text[:50]}...'\n\n"
                    "Please fix this question manually before using auto-renumbering.")
                self.list_widget.setCurrentRow(i)
                return False
        return True

    def _apply_numbering_shift(self, start_idx, delta):
        """Shifts numbers in JSON strings by delta for questions starting at start_idx."""
        for i in range(start_idx, len(self.current_bank_data)):
            q = self.current_bank_data[i]
            q_text = q.get("question", "").strip()
            if not q_text: continue
            
            match = re.match(r'^(\d+)(\s*[-.)]\s*)(.*)', q_text, re.DOTALL)
            if match:
                old_num = int(match.group(1))
                new_num = old_num + delta
                # We enforce minimum of 0 to avoid negative numbers if strange things happen
                if new_num < 0: new_num = 0
                
                separator = match.group(2)
                content = match.group(3)
                q["question"] = f"{new_num}{separator}{content}"

    def manual_renumber(self, delta):
        # We use the current VALID index from valid_indices mapping if available, 
        # but operations must happen on the real full data index.
        list_idx = self.list_widget.currentRow()
        if list_idx < 0: return
        
        # Map list index to real data index
        if list_idx < len(self.valid_indices):
            real_idx = self.valid_indices[list_idx]
        else:
            real_idx = list_idx

        if not self._validate_numbering(real_idx):
            return
            
        self._apply_numbering_shift(real_idx, delta)
        self.save_and_refresh(real_idx)

    def insert_question(self, after=True):
        idx = self.current_q_index
        new_idx = idx + 1 if after else idx
        
        # Validate first
        if not self._validate_numbering(new_idx):
            return

        # Shift numbers down to make room
        self._apply_numbering_shift(new_idx, 1)
        
        # Calculate new number based on previous question if possible
        new_q_num = 1
        if new_idx > 0:
            prev_q = self.current_bank_data[new_idx - 1]
            match = re.match(r'^(\d+)', prev_q.get("question","").strip())
            if match:
                new_q_num = int(match.group(1)) + 1
                
        # Image shifting
        img_dir = os.path.join(self.current_bank_path, "images")
        max_idx = len(self.current_bank_data)
        
        # Shift images forward carefully
        for curr in range(max_idx, new_idx, -1):
            old = os.path.join(img_dir, f"{curr}.jpg")
            old_note = os.path.join(img_dir, f"{curr}_note.jpg")
            if os.path.exists(old):
                shutil.move(old, os.path.join(img_dir, f"{curr+1}.jpg"))
            if os.path.exists(old_note):
                shutil.move(old_note, os.path.join(img_dir, f"{curr+1}_note.jpg"))
        
        new_q_text = "سؤال جديد" if ConfigManager.get_language() == "ar" else "New Question"
        empty_q = {
            "type": "quiz",
            "question": f"{new_q_num}. {new_q_text}",
            "options": [],
            "correct_options": [0],
            "explanation": ""
        }
        
        self.current_bank_data.insert(new_idx, empty_q)
        
        self.save_and_refresh(new_idx)
        if not self.edit_mode:
            self.toggle_edit_mode()

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        q = self.current_bank_data[self.current_q_index]

        self.set_nav_shortcuts_enabled(not self.edit_mode)

        if self.edit_mode:
            self.q_text_edit.setText(q.get("question", ""))
            
            correct = q.get("correct_options", [0])
            self.temp_correct_idx = correct[0] if correct else 0
            
            self.edit_expl.setText(q.get("explanation", ""))
            
            while self.edit_opt_layout.count():
                it = self.edit_opt_layout.takeAt(0); it.widget().deleteLater()
            
            for btn in self.edit_mode_button_group.buttons():
                self.edit_mode_button_group.removeButton(btn)
            
            self.option_rows = []
            for i, opt in enumerate(q.get("options",[])):
                self.add_option_row(opt, i == self.temp_correct_idx)
            
            self.ans_box.show()
            self.lbl_ans_status.setText("تعديل الشرح:" if ConfigManager.get_language() == "ar" else "Editing Explanation:")
            self.lbl_ans_status.setStyleSheet("color: #4da3ff;")
        else:
            list_idx = self.valid_indices.index(self.current_q_index)
            self.load_question(list_idx)
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
        
        final_opts =[]
        for i, row in enumerate(self.option_rows):
            txt = row.line_edit.text().strip()
            final_opts.append(f"{self.generate_prefix(i)} {txt}")
            if row.radio.isChecked(): self.temp_correct_idx = i
        
        q['options'] = final_opts
        q['correct_options'] =[self.temp_correct_idx]
        
        with open(os.path.join(self.current_bank_path, "bank.json"), 'w', encoding='utf-8') as f:
            json.dump(self.current_bank_data, f, indent=2, ensure_ascii=False)
            
        self.toggle_edit_mode()
        self.refresh_list(self.current_q_index)

    def update_ui_state(self):
        v = self.edit_mode
        self.q_text_lbl.setVisible(not v); self.q_text_edit.setVisible(v)
        self.edit_opt_container.setVisible(v); self.btn_add_opt.setVisible(v); self.img_tools.setVisible(v)
        
        for i in range(self.opt_view_layout.count()):
            w = self.opt_view_layout.itemAt(i).widget()
            if w: w.setVisible(not v)
            
        self.lbl_expl.setVisible(not v); self.edit_expl.setVisible(v)
        self.note_img_tools.setVisible(v)
        
        self.btn_reveal.setVisible(not v); self.btn_save.setVisible(v)
        
        if v:
            self.btn_edit.setText("↩ " + tr("cancel"))
            self.btn_edit.setStyleSheet("background-color: #555;")
        else:
            self.btn_edit.setText("✏️ " + tr("edit_btn"))
            self.btn_edit.setStyleSheet("")

    def reveal_answer(self):
        q = self.current_bank_data[self.current_q_index]
        correct_opts = q.get("correct_options", [0])
        correct = correct_opts[0] if correct_opts else 0
        is_ar = ConfigManager.get_language() == "ar"
        
        for b in self.opt_group_view.buttons():
            idx = b.property("idx")
            if idx == correct:
                b.setStyleSheet("color: #66bb6a; font-weight: bold; font-size: 17px; border: 1px solid #66bb6a; border-radius: 4px;")
            else:
                b.setStyleSheet("color: #999; font-size: 16px;")
        
        self.lbl_ans_status.setText("✅ " + (tr("view_ans_header") if tr("view_ans_header") != "view_ans_header" else "الإجابة الصحيحة:"))
        self.lbl_ans_status.setStyleSheet("color: #66bb6a; font-weight: bold;")
        
        expl_text = q.get('explanation', '').strip()
        
        expl_header = "الشرح:" if is_ar else "Explanation:"
        no_expl_txt = "لا يوجد شرح لهذا السؤال." if is_ar else "No explanation provided."
        ans_txt_label = "الإجابة الصحيحة: الخيار" if is_ar else "Correct Answer: Option"

        if not expl_text: expl_text = f"<i>{no_expl_txt}</i>"
        
        self.lbl_expl.setText(f"<b>{ans_txt_label} {correct+1}</b><br><br><b>{expl_header}</b><br>{expl_text}")
        
        note_img_p = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}_note.jpg")
        if os.path.exists(note_img_p):
            pix = QPixmap(note_img_p)
            if pix.width() > 900: pix = pix.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)
            self.note_img_label.setPixmap(pix)
            self.note_img_label.show()
        else:
            self.note_img_label.hide()
            
        self.ans_box.show()
        if self.scroll_area.verticalScrollBar():
             self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def on_option_clicked(self, btn):
        if self.edit_mode: return
        correct_opts = self.current_bank_data[self.current_q_index].get("correct_options", [0])
        correct = correct_opts[0] if correct_opts else 0
        
        if btn.property("idx") == correct:
            self.reveal_answer()
        else:
            is_ar = ConfigManager.get_language() == "ar"
            wrong_title = "إجابة خاطئة" if is_ar else "Wrong Answer"
            wrong_msg = "حاول مرة أخرى أو اضغط على 'إظهار الإجابة'." if is_ar else "Try again or click 'Show Answer'."
            
            self.lbl_ans_status.setText(f"❌ {wrong_title}") 
            self.lbl_ans_status.setStyleSheet("color: #ef5350; font-weight: bold;")
            self.lbl_expl.setText(wrong_msg)
            self.note_img_label.hide()
            self.ans_box.show()

    def replace_image(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("replace_img"), "", "Images (*.jpg *.png)")
        if f:
            dest = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}.jpg")
            if not os.path.exists(os.path.dirname(dest)): os.makedirs(os.path.dirname(dest))
            shutil.copy(f, dest) 
            self.load_question(self.list_widget.currentRow())

    def open_cropper_for_image(self):
        from ui.window import ImageCropperApp
        img_p = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}.jpg")
        if not os.path.exists(img_p):
            QMessageBox.warning(self, "Error", "No image exists for this question.")
            return
        self.cropper_ref = ImageCropperApp(single_image_mode=True)
        self.cropper_ref.load_single_image(img_p)
        self.cropper_ref.show()
        
    def delete_image(self):
        if QMessageBox.question(self, tr("delete"), "Are you sure you want to delete this question image?") == QMessageBox.StandardButton.Yes:
            img_p = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}.jpg")
            if os.path.exists(img_p):
                os.remove(img_p)
                self.load_question(self.list_widget.currentRow())
        
    def replace_note_image(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("replace_img"), "", "Images (*.jpg *.png)")
        if f:
            dest = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}_note.jpg")
            if not os.path.exists(os.path.dirname(dest)): os.makedirs(os.path.dirname(dest))
            shutil.copy(f, dest)
            self.load_question(self.list_widget.currentRow())

    def open_cropper_for_note_image(self):
        from ui.window import ImageCropperApp
        img_p = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}_note.jpg")
        if not os.path.exists(img_p):
            QMessageBox.warning(self, "Error", "No note image exists for this question. Add one first.")
            return
        self.cropper_ref = ImageCropperApp(single_image_mode=True)
        self.cropper_ref.load_single_image(img_p)
        self.cropper_ref.show()

    def delete_note_image(self):
        if QMessageBox.question(self, tr("delete"), "Are you sure you want to delete this note image?") == QMessageBox.StandardButton.Yes:
            img_p = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}_note.jpg")
            if os.path.exists(img_p):
                os.remove(img_p)
                self.load_question(self.list_widget.currentRow())

    def delete_current_question(self):
        if QMessageBox.question(self, tr("delete"), tr("confirm_delete")) != QMessageBox.StandardButton.Yes: return
        idx = self.current_q_index
        
        # Validate numbering for subsequent questions before doing anything
        if not self._validate_numbering(idx + 1):
            return

        # Shift numbering of subsequent questions DOWN by 1 (e.g. 6->5)
        self._apply_numbering_shift(idx + 1, -1)

        self.current_bank_data.pop(idx)
        
        img_dir = os.path.join(self.current_bank_path, "images")
        
        t_img = os.path.join(img_dir, f"{idx+1}.jpg")
        if os.path.exists(t_img): os.remove(t_img)
        t_note_img = os.path.join(img_dir, f"{idx+1}_note.jpg")
        if os.path.exists(t_note_img): os.remove(t_note_img)
        
        curr = idx + 2
        while True:
            old = os.path.join(img_dir, f"{curr}.jpg")
            old_note = os.path.join(img_dir, f"{curr}_note.jpg")
            
            moved_any = False
            if os.path.exists(old): 
                shutil.move(old, os.path.join(img_dir, f"{curr-1}.jpg"))
                moved_any = True
            if os.path.exists(old_note):
                shutil.move(old_note, os.path.join(img_dir, f"{curr-1}_note.jpg"))
                moved_any = True
                
            if not moved_any and not os.path.exists(os.path.join(img_dir, f"{curr+1}.jpg")): 
                break
            curr += 1
            
        next_idx = min(idx, len(self.current_bank_data)-1)
        self.save_and_refresh(next_idx)

    def save_and_refresh(self, index_to_select):
        with open(os.path.join(self.current_bank_path, "bank.json"), 'w', encoding='utf-8') as f:
            json.dump(self.current_bank_data, f, indent=2, ensure_ascii=False)
        self.refresh_list(index_to_select)

    def go_home(self):
        from ui.menu import MainMenu
        self.menu = MainMenu(None); self.menu.show(); self.close()
# --- END OF FILE ui/viewer.py ---
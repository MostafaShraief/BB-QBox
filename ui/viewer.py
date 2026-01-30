# --- START OF FILE ui/viewer.py ---
import os
import json
import shutil
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QSplitter, 
                             QScrollArea, QRadioButton, QButtonGroup, QFrame,
                             QComboBox, QMessageBox, QCheckBox, QLineEdit,
                             QTextEdit, QFileDialog, QToolButton)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont, QKeyEvent, QAction
from utils import tr, ConfigManager

class QuestionViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("menu_viewer"))
        self.resize(1100, 750)
        
        self.is_rtl = ConfigManager.get_language() == "ar"
        if self.is_rtl: self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else: self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.current_bank_data = []
        self.current_bank_path = ""
        self.current_q_index = 0
        self.edit_mode = False
        
        ConfigManager.load_window_state("viewer", self)
        self.init_ui()
        self.scan_banks_folder()

    def closeEvent(self, event):
        ConfigManager.save_window_state("viewer", self)
        super().closeEvent(event)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel(tr("view_sel_folder")))
        self.combo_banks = QComboBox()
        self.combo_banks.setMinimumWidth(250)
        self.combo_banks.currentIndexChanged.connect(self.on_bank_selected)
        top_bar.addWidget(self.combo_banks)

        top_bar.addStretch()
        self.chk_always_show = QCheckBox(tr("view_always_show"))
        self.chk_always_show.setChecked(True)
        top_bar.addWidget(self.chk_always_show)
        
        btn_home = QPushButton(tr("home"))
        btn_home.clicked.connect(self.go_home)
        top_bar.addWidget(btn_home)
        main_layout.addLayout(top_bar)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.load_question)
        self.list_widget.setMaximumWidth(220)
        splitter.addWidget(self.list_widget)

        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        content_scroll.setWidget(self.content_widget)
        splitter.addWidget(content_scroll)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter)

        # --- Content Area ---
        
        # Tools Layout (Edit/Delete/Image)
        tools_layout = QHBoxLayout()
        self.btn_edit = QPushButton(tr("edit_mode"))
        self.btn_edit.clicked.connect(self.toggle_edit_mode)
        tools_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton(tr("delete_q"))
        self.btn_delete.setStyleSheet("color: #FF5252;")
        self.btn_delete.clicked.connect(self.delete_current_question)
        tools_layout.addWidget(self.btn_delete)
        
        self.btn_replace_img = QPushButton(tr("replace_img"))
        self.btn_replace_img.clicked.connect(self.replace_image)
        self.btn_replace_img.hide()
        tools_layout.addWidget(self.btn_replace_img)
        
        self.btn_crop_img = QPushButton(tr("crop_img"))
        self.btn_crop_img.clicked.connect(self.open_cropper_for_image)
        self.btn_crop_img.hide()
        tools_layout.addWidget(self.btn_crop_img)
        
        tools_layout.addStretch()
        self.content_layout.addLayout(tools_layout)

        # Image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px dashed #ccc; padding: 10px; background: #f9f9f9;")
        self.content_layout.addWidget(self.image_label)
        
        # Question Text
        self.q_text_label = QLabel()
        self.q_text_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.q_text_label.setWordWrap(True)
        self.q_text_edit = QTextEdit() # For editing
        self.q_text_edit.hide()
        self.content_layout.addWidget(self.q_text_label)
        self.content_layout.addWidget(self.q_text_edit)
        
        # Options
        self.opts_container = QWidget()
        self.opts_layout = QVBoxLayout(self.opts_container)
        self.content_layout.addWidget(self.opts_container)
        
        # Edit Options Area (Hidden by default)
        self.edit_opts_container = QWidget()
        self.edit_opts_layout = QVBoxLayout(self.edit_opts_container)
        self.edit_opts_container.hide()
        self.content_layout.addWidget(self.edit_opts_container)

        self.btn_show_ans = QPushButton(tr("view_show_ans"))
        self.btn_show_ans.clicked.connect(self.toggle_answer)
        self.content_layout.addWidget(self.btn_show_ans)
        
        # Answer/Explanation Box
        self.ans_frame = QFrame()
        self.ans_frame.setStyleSheet("background-color: #333; color: #fff; border-radius: 8px; padding: 15px;")
        v_ans = QVBoxLayout(self.ans_frame)
        self.lbl_result = QLabel()
        self.lbl_result.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_explanation = QLabel()
        self.lbl_explanation.setWordWrap(True)
        
        # Edit Fields for Answer
        self.edit_ans_idx = QLineEdit()
        self.edit_ans_idx.setPlaceholderText("Correct Option Index (0=A, 1=B...)")
        self.edit_expl = QTextEdit()
        self.edit_expl.setPlaceholderText("Explanation...")
        self.edit_ans_idx.hide()
        self.edit_expl.hide()

        v_ans.addWidget(self.lbl_result)
        v_ans.addWidget(self.lbl_explanation)
        v_ans.addWidget(self.edit_ans_idx)
        v_ans.addWidget(self.edit_expl)
        
        self.ans_frame.hide()
        self.content_layout.addWidget(self.ans_frame)
        
        # Save/Cancel Edit Buttons
        h_edit_btns = QHBoxLayout()
        self.btn_save_edit = QPushButton(tr("save_changes"))
        self.btn_save_edit.setStyleSheet("background: #4CAF50; color: white;")
        self.btn_save_edit.clicked.connect(self.save_edits)
        self.btn_cancel_edit = QPushButton(tr("cancel_edit"))
        self.btn_cancel_edit.clicked.connect(self.toggle_edit_mode)
        
        self.btn_save_edit.hide()
        self.btn_cancel_edit.hide()
        
        h_edit_btns.addWidget(self.btn_save_edit)
        h_edit_btns.addWidget(self.btn_cancel_edit)
        self.content_layout.addLayout(h_edit_btns)

    # --- Loading Logic ---
    def scan_banks_folder(self):
        self.combo_banks.clear()
        base = "banks"
        if not os.path.exists(base): os.makedirs(base)
        subs = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])
        if subs: self.combo_banks.addItems(subs)
        else: self.combo_banks.addItem("No Banks Found")

    def on_bank_selected(self):
        name = self.combo_banks.currentText()
        path = os.path.join("banks", name, "bank.json")
        self.current_bank_path = os.path.dirname(path)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.current_bank_data = json.load(f)
            self.refresh_list()
        else:
            self.list_widget.clear()
            self.current_bank_data = []

    def refresh_list(self):
        self.list_widget.clear()
        for i, q in enumerate(self.current_bank_data):
            self.list_widget.addItem(f"{i+1}. {q.get('question','?')[:30]}...")
        if self.current_bank_data:
            self.list_widget.setCurrentRow(0)

    def load_question(self, index):
        if index < 0 or index >= len(self.current_bank_data): return
        self.current_q_index = index
        self.edit_mode = False 
        self.update_ui_mode()
        
        q = self.current_bank_data[index]
        
        # Image
        img_p = os.path.join(self.current_bank_path, "images", f"{index+1}.jpg")
        if os.path.exists(img_p):
            pix = QPixmap(img_p)
            if pix.height() > 400: pix = pix.scaledToHeight(400, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(pix)
            self.image_label.show()
        else:
            self.image_label.hide()
        
        self.q_text_label.setText(tr("view_lbl_q").format(index+1) + "\n" + q.get("question", ""))
        
        # Display Options
        for i in reversed(range(self.opts_layout.count())): 
            self.opts_layout.itemAt(i).widget().setParent(None)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.buttonClicked.connect(self.check_answer)
        for i, opt in enumerate(q.get("options", [])):
            rb = QRadioButton(opt)
            rb.setProperty("idx", i)
            rb.setFont(QFont("Segoe UI", 12))
            self.opts_layout.addWidget(rb)
            self.btn_group.addButton(rb)
            
        self.ans_frame.hide()
        self.lbl_result.setText("")
        
        # Explanation setup
        expl = q.get("explanation", "")
        self.lbl_explanation.setText(expl)
        
        if self.chk_always_show.isChecked(): self.reveal_details()

    # --- Interaction ---
    def check_answer(self, btn):
        q = self.current_bank_data[self.current_q_index]
        correct = q.get("correct_options", [0])[0]
        if btn.property("idx") == correct:
            self.lbl_result.setText("✅ " + tr("view_correct"))
            self.lbl_result.setStyleSheet("color: #4CAF50;")
            self.reveal_details()
        else:
            self.lbl_result.setText("❌ " + tr("view_wrong"))
            self.lbl_result.setStyleSheet("color: #FF5252;")
            self.ans_frame.show()

    def toggle_answer(self):
        if self.ans_frame.isVisible(): self.ans_frame.hide()
        else: self.reveal_details()

    def reveal_details(self):
        self.ans_frame.show()
        q = self.current_bank_data[self.current_q_index]
        correct = q.get("correct_options", [0])[0]
        opts = q.get("options", [])
        
        for btn in self.btn_group.buttons():
            if btn.property("idx") == correct:
                btn.setStyleSheet("color: #2196F3; font-weight: bold;")
        
        txt = ""
        if correct < len(opts):
            txt += f"<b>{tr('view_ans_header')}</b> {opts[correct]}<br><br>"
        if q.get("explanation"):
            txt += f"<b>📝 {tr('view_note_header')}</b><br>{q['explanation']}"
        self.lbl_explanation.setText(txt)

    # --- Editing Logic ---
    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.update_ui_mode()
        
        if self.edit_mode:
            # Populate fields
            q = self.current_bank_data[self.current_q_index]
            self.q_text_edit.setText(q.get("question", ""))
            
            # Populate Options Editor
            for i in reversed(range(self.edit_opts_layout.count())):
                 self.edit_opts_layout.itemAt(i).widget().setParent(None)
            self.opt_edits = []
            for opt in q.get("options", []):
                le = QLineEdit(opt)
                self.edit_opts_layout.addWidget(le)
                self.opt_edits.append(le)
            
            correct = q.get("correct_options", [0])[0]
            self.edit_ans_idx.setText(str(correct))
            self.edit_expl.setText(q.get("explanation", ""))
            self.ans_frame.show() # Show frame to edit expl

    def update_ui_mode(self):
        vis = self.edit_mode
        # Visibility Swaps
        self.q_text_label.setVisible(not vis)
        self.q_text_edit.setVisible(vis)
        self.opts_container.setVisible(not vis)
        self.edit_opts_container.setVisible(vis)
        
        self.lbl_result.setVisible(not vis)
        self.lbl_explanation.setVisible(not vis)
        self.edit_ans_idx.setVisible(vis)
        self.edit_expl.setVisible(vis)
        
        self.btn_save_edit.setVisible(vis)
        self.btn_cancel_edit.setVisible(vis)
        self.btn_replace_img.setVisible(vis)
        self.btn_crop_img.setVisible(vis)
        
        self.btn_edit.setVisible(not vis)
        self.btn_delete.setVisible(not vis)
        self.btn_show_ans.setVisible(not vis)

    def save_edits(self):
        q = self.current_bank_data[self.current_q_index]
        q['question'] = self.q_text_edit.toPlainText()
        q['options'] = [le.text() for le in self.opt_edits]
        try:
            q['correct_options'] = [int(self.edit_ans_idx.text())]
        except: pass
        q['explanation'] = self.edit_expl.toPlainText()
        
        self._save_json_to_disk()
        self.toggle_edit_mode() # Exit edit
        self.load_question(self.current_q_index) # Refresh

    def _save_json_to_disk(self):
        path = os.path.join(self.current_bank_path, "bank.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.current_bank_data, f, indent=2, ensure_ascii=False)

    def delete_current_question(self):
        if QMessageBox.question(self, tr("delete"), tr("confirm_delete")) != QMessageBox.StandardButton.Yes:
            return
        
        idx = self.current_q_index
        # 1. Remove from Data
        self.current_bank_data.pop(idx)
        self._save_json_to_disk()
        
        # 2. Handle Image Deletion and Renaming
        img_dir = os.path.join(self.current_bank_path, "images")
        deleted_img = os.path.join(img_dir, f"{idx+1}.jpg")
        if os.path.exists(deleted_img): os.remove(deleted_img)
        
        # Shift subsequent images down (6.jpg -> 5.jpg)
        # We start from idx+2 (old next question) which becomes idx+1
        # Loop until we find no more images
        curr = idx + 2
        while True:
            old_p = os.path.join(img_dir, f"{curr}.jpg")
            if not os.path.exists(old_p): break
            new_p = os.path.join(img_dir, f"{curr-1}.jpg")
            shutil.move(old_p, new_p)
            curr += 1
            
        self.refresh_list()
        new_sel = min(idx, len(self.current_bank_data)-1)
        if new_sel >= 0: self.list_widget.setCurrentRow(new_sel)

    def replace_image(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("replace_img"), "", "Images (*.jpg *.png)")
        if f:
            dest = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}.jpg")
            if not os.path.exists(os.path.dirname(dest)): os.makedirs(os.path.dirname(dest))
            # Convert to jpg standard
            try:
                from PIL import Image
                img = Image.open(f).convert("RGB")
                img.save(dest, "JPEG")
                self.load_question(self.current_q_index) # Refresh image view
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def open_cropper_for_image(self):
        img_path = os.path.join(self.current_bank_path, "images", f"{self.current_q_index+1}.jpg")
        if not os.path.exists(img_path):
            QMessageBox.warning(self, "Error", "No image exists for this question.")
            return
        
        from ui.window import ImageCropperApp
        # Pass single_image_mode=True
        self.cropper = ImageCropperApp(single_image_mode=True)
        self.cropper.load_single_image(img_path)
        # When cropper closes, refresh
        self.cropper.destroyed.connect(lambda: self.load_question(self.current_q_index))
        self.cropper.show()

    def go_home(self):
        from ui.menu import MainMenu
        self.menu = MainMenu(None)
        self.menu.show()
        self.close()
# --- END OF FILE ui/viewer.py ---
# --- START OF FILE ui/extractor.py ---
# (Keep imports and logic the same, just adding setLayoutDirection in __init__)
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QCheckBox, 
                             QFileDialog, QMessageBox, QGroupBox, QRadioButton,
                             QDialog, QTextBrowser)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from core.config import ConfigManager
from ui.common import tr

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("help_btn"))
        self.resize(600, 500)
        self.setStyleSheet("background-color: #ffffff; color: #000000;")
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setHtml(tr("help_html"))
        layout.addWidget(browser)
        btn = QPushButton(tr("back_menu").replace("القائمة الرئيسية", "Close"))
        btn.clicked.connect(self.close)
        layout.addWidget(btn)

class ProcessingWorker(QThread):
    finished = pyqtSignal(str) 
    error = pyqtSignal(str)

    def __init__(self, file_path, folder_name, use_filename, split_lecture, create_imgs, inline_note, multiline_note):
        super().__init__()
        from core.parser import QuestionParser 
        self.parser_cls = QuestionParser
        self.file_path = file_path
        self.folder_name = folder_name
        self.use_filename = use_filename
        self.split_lecture = split_lecture
        self.create_imgs = create_imgs
        self.inline_note = inline_note
        self.multiline_note = multiline_note

    def run(self):
        try:
            parser = self.parser_cls()
            banks = parser.parse_text(
                self.file_path, 
                split_lectures=self.split_lecture,
                inline_note=self.inline_note,
                multiline_note=self.multiline_note
            )
            if not banks:
                self.error.emit(tr("no_detect_msg"))
                return
            base_name = ""
            if self.use_filename:
                base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            else:
                base_name = self.folder_name if self.folder_name else "Untitled_Bank"
            paths = parser.save_banks(banks, base_name, self.create_imgs)
            msg = f"{tr('success_header')}!\nProcessed {len(banks)} sections.\nSaved to:\n" + "\n".join(paths)
            self.finished.emit(msg)
        except Exception as e:
            self.error.emit(str(e))

class TextExtractorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("ext_title"))
        self.resize(650, 650)
        
        # RTL Check
        if ConfigManager.get_language() == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            
        self.selected_file = None
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI';
                font-size: 14px;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 20px;
                font-weight: bold;
                color: #4da3ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
            }
            QLineEdit {
                background-color: #333;
                color: #fff;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #4da3ff;
            }
            QCheckBox, QRadioButton {
                spacing: 8px;
                color: #eee;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #888;
                border-radius: 3px;
                background: #333;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background-color: #4da3ff;
                border-color: #4da3ff;
            }
        """)

        h_header = QHBoxLayout()
        title_lbl = QLabel(tr("ext_title"))
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        h_header.addWidget(title_lbl)
        h_header.addStretch()
        btn_help = QPushButton(tr("help_btn"))
        btn_help.setStyleSheet("background-color: #00796b;")
        btn_help.clicked.connect(self.show_help)
        h_header.addWidget(btn_help)
        layout.addLayout(h_header)

        gb_file = QGroupBox(tr("ext_input"))
        v_file = QVBoxLayout()
        h_sel = QHBoxLayout()
        self.lbl_file = QLineEdit()
        self.lbl_file.setPlaceholderText("Select .txt file...")
        self.lbl_file.setReadOnly(True)
        btn_browse = QPushButton(tr("browse"))
        btn_browse.clicked.connect(self.browse_file)
        h_sel.addWidget(self.lbl_file)
        h_sel.addWidget(btn_browse)
        v_file.addLayout(h_sel)
        gb_file.setLayout(v_file)
        layout.addWidget(gb_file)

        gb_opts = QGroupBox(tr("parsing_opts"))
        v_opts = QVBoxLayout()
        self.chk_split = QCheckBox(tr("opt_split"))
        self.chk_inline = QCheckBox(tr("opt_inline"))
        self.chk_multiline = QCheckBox(tr("opt_multiline"))
        self.chk_split.setStyleSheet("color: #ffb74d; font-weight: bold;")
        v_opts.addWidget(self.chk_split)
        v_opts.addWidget(self.chk_inline)
        v_opts.addWidget(self.chk_multiline)
        gb_opts.setLayout(v_opts)
        layout.addWidget(gb_opts)

        gb_out = QGroupBox(tr("out_opts"))
        v_out = QVBoxLayout()
        self.radio_fname = QRadioButton(tr("use_fname"))
        self.radio_fname.setChecked(True)
        self.radio_custom = QRadioButton(tr("use_custom"))
        self.txt_custom = QLineEdit()
        self.txt_custom.setEnabled(False)
        self.radio_custom.toggled.connect(lambda: self.txt_custom.setEnabled(self.radio_custom.isChecked()))
        self.chk_imgs = QCheckBox(tr("create_img"))
        self.chk_imgs.setChecked(True)
        v_out.addWidget(self.radio_fname)
        h_cust = QHBoxLayout()
        h_cust.addWidget(self.radio_custom)
        h_cust.addWidget(self.txt_custom)
        v_out.addLayout(h_cust)
        v_out.addWidget(self.chk_imgs)
        gb_out.setLayout(v_out)
        layout.addWidget(gb_out)

        layout.addStretch()
        self.btn_run = QPushButton(tr("run_btn"))
        self.btn_run.setMinimumHeight(55)
        self.btn_run.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold; font-size: 16px; border: none;")
        self.btn_run.clicked.connect(self.start_processing)
        layout.addWidget(self.btn_run)
        
        btn_back = QPushButton(tr("back_menu"))
        btn_back.setStyleSheet("background: transparent; color: #888; text-decoration: underline; border: none;")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.go_back)
        layout.addWidget(btn_back)

    def browse_file(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("open_files"), "", "Text Files (*.txt)")
        if f:
            self.selected_file = f
            self.lbl_file.setText(os.path.basename(f))

    def show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def start_processing(self):
        if not self.selected_file:
            QMessageBox.warning(self, tr("error_header"), tr("error_sel"))
            return
        self.btn_run.setEnabled(False)
        self.btn_run.setText(tr("processing"))
        self.worker = ProcessingWorker(
            self.selected_file,
            self.txt_custom.text().strip(),
            self.radio_fname.isChecked(),
            self.chk_split.isChecked(),
            self.chk_imgs.isChecked(),
            self.chk_inline.isChecked(),
            self.chk_multiline.isChecked()
        )
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_success(self, msg):
        self.btn_run.setEnabled(True)
        self.btn_run.setText(tr("run_btn"))
        QMessageBox.information(self, tr("success_header"), msg)

    def on_error(self, err):
        self.btn_run.setEnabled(True)
        self.btn_run.setText(tr("run_btn"))
        QMessageBox.critical(self, tr("error_header"), f"An error occurred:\n{err}")

    def go_back(self):
        from ui.menu import MainMenu
        self.menu = MainMenu(None)
        self.menu.show()
        self.close()

class MainMenu(QWidget):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.setWindowTitle("BB-QBox")
        self.resize(500, 500)
        
        # RTL Check
        if ConfigManager.get_language() == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            
        self.init_ui()

    def init_ui(self):
        if self.layout(): QWidget().setLayout(self.layout())
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)

        h_top = QHBoxLayout()
        h_top.addStretch()
        btn_lang = QPushButton(tr("lang_switch"))
        btn_lang.setFlat(True)
        btn_lang.clicked.connect(self.toggle_language)
        h_top.addWidget(btn_lang)
        layout.addLayout(h_top)

        title = QLabel(tr("app_title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        btn_cropper = self.create_btn(tr("menu_cropper"), "✂️")
        btn_extractor = self.create_btn(tr("menu_extractor"), "📝")
        btn_viewer = self.create_btn(tr("menu_viewer"), "👁️")

        btn_cropper.clicked.connect(self.open_cropper)
        btn_extractor.clicked.connect(self.open_extractor)
        btn_viewer.clicked.connect(self.open_viewer)

        layout.addWidget(btn_cropper)
        layout.addWidget(btn_extractor)
        layout.addWidget(btn_viewer)
        layout.addStretch()
        
        footer = QLabel(tr("menu_footer"))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: gray;")
        layout.addWidget(footer)

    def create_btn(self, text, icon):
        btn = QPushButton(f"  {icon}  {text}")
        btn.setFont(QFont("Segoe UI", 12))
        btn.setMinimumHeight(60)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def toggle_language(self):
        curr = ConfigManager.get_language()
        new_lang = "en" if curr == "ar" else "ar"
        ConfigManager.set_language(new_lang)
        
        # Refresh RTL
        if new_lang == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            
        self.init_ui()

    def open_cropper(self):
        from ui.window import ImageCropperApp
        self.cropper = ImageCropperApp()
        self.cropper.show()
        self.close()

    def open_extractor(self):
        from ui.extractor import TextExtractorWindow
        self.extractor = TextExtractorWindow()
        self.extractor.show()
        self.close()
        
    def open_viewer(self):
        from ui.viewer import QuestionViewer
        self.viewer = QuestionViewer()
        self.viewer.show()
        self.close()
# --- END OF FILE ui/menu.py ---
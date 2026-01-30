# --- START OF FILE ui/menu.py ---
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QHBoxLayout, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
from core.config import ConfigManager
from ui.common import tr

class MainMenu(QWidget):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.setWindowTitle("BB-QBox")
        self.resize(500, 700) # Increased height for new button
        
        # RTL Check
        if ConfigManager.get_language() == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            
        ConfigManager.load_window_state("menu", self)
        self.apply_styles()
        self.init_ui()

    def closeEvent(self, event):
        ConfigManager.save_window_state("menu", self)
        super().closeEvent(event)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI';
                font-size: 16px; 
            }
            QLabel#Title {
                font-size: 28px;
                font-weight: bold;
                color: #4da3ff;
                margin-bottom: 5px;
            }
            QLabel#Subtitle {
                font-size: 14px;
                color: #aaaaaa;
                margin-bottom: 25px;
            }
            QPushButton.MenuBtn {
                background-color: #383838;
                border: 1px solid #505050;
                border-radius: 10px;
                color: #fff;
                padding: 20px; 
                text-align: left;
                font-size: 18px; 
                font-weight: 600;
                margin-bottom: 10px;
            }
            QPushButton.MenuBtn:hover {
                background-color: #444444;
                border-color: #4da3ff;
            }
            QPushButton.MenuBtn:pressed {
                background-color: #1976D2;
                border-color: #1976D2;
            }
            QPushButton#LangBtn {
                background-color: transparent;
                color: #888;
                border: none;
                font-size: 14px;
            }
            QPushButton#LangBtn:hover {
                color: #fff;
                text-decoration: underline;
            }
            QFrame#Divider {
                background-color: #444;
                max-height: 1px;
                margin: 15px 0;
            }
            QLabel#Footer {
                color: #666;
                font-size: 12px;
            }
        """)

    def init_ui(self):
        if self.layout(): QWidget().setLayout(self.layout())
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(40, 40, 40, 40)

        # --- Top Bar ---
        h_top = QHBoxLayout()
        h_top.addStretch()
        btn_lang = QPushButton(tr("lang_switch"))
        btn_lang.setObjectName("LangBtn")
        btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_lang.clicked.connect(self.toggle_language)
        h_top.addWidget(btn_lang)
        layout.addLayout(h_top)

        # --- Header ---
        title = QLabel(tr("app_title"))
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Comprehensive Question Bank Management")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # --- Divider ---
        div = QFrame()
        div.setObjectName("Divider")
        layout.addWidget(div)

        # --- Buttons ---
        layout.addSpacing(15)
        
        btn_cropper = self.create_btn(tr("menu_cropper"), "✂️")
        btn_extractor = self.create_btn(tr("menu_extractor"), "📝")
        btn_viewer = self.create_btn(tr("menu_viewer"), "👁️")
        # New Button
        btn_telegram = self.create_btn(tr("menu_telegram"), "✈️")

        btn_cropper.clicked.connect(self.open_cropper)
        btn_extractor.clicked.connect(self.open_extractor)
        btn_viewer.clicked.connect(self.open_viewer)
        btn_telegram.clicked.connect(self.open_telegram)

        layout.addWidget(btn_cropper)
        layout.addWidget(btn_extractor)
        layout.addWidget(btn_viewer)
        layout.addWidget(btn_telegram)
        
        layout.addStretch()
        
        # --- Footer ---
        footer = QLabel(tr("menu_footer"))
        footer.setObjectName("Footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    def create_btn(self, text, icon):
        btn = QPushButton(f"  {icon}   {text}")
        btn.setObjectName("MenuBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(75) 
        return btn

    def toggle_language(self):
        curr = ConfigManager.get_language()
        new_lang = "en" if curr == "ar" else "ar"
        ConfigManager.set_language(new_lang)
        
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

    def open_telegram(self):
        from ui.telegram_sender import TelegramWindow
        self.tg = TelegramWindow()
        self.tg.show()
        self.close()
# --- END OF FILE ui/menu.py ---
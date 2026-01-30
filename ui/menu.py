# --- START OF FILE ui/menu.py ---
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QSpacerItem, QSizePolicy, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils import tr, ConfigManager

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
            
        ConfigManager.load_window_state("menu", self)
        self.init_ui()

    def closeEvent(self, event):
        ConfigManager.save_window_state("menu", self)
        super().closeEvent(event)

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
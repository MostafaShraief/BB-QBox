# --- START OF FILE utils.py ---
import os
import fitz  # PyMuPDF
import re
import json
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QRectF, Qt

# --- Localization & Config ---
CONFIG_PATH = "config.json"

TRANS = {
    "ar": {
        "app_title": "BB-QBox",
        "menu_cropper": "أداة قص الصور (PDF/صور)",
        "menu_extractor": "محول الأسئلة النصية (Txt)",
        "menu_viewer": "مستعرض بنك الأسئلة",
        "menu_footer": "الإصدار 3.1 - إصلاحات شاملة",
        "lang_switch": "Switch to English",
        "back_menu": "العودة للقائمة الرئيسية",
        "open_files": "فتح ملفات",
        "save": "حفظ",
        "undo": "تراجع",
        "redo": "إعادة",
        "delete": "حذف",
        "renumber": "إعادة ترقيم",
        "link_crops": "ربط بسؤال (رئيسي/فرعي)",
        "unlink_crops": "فك الارتباط",
        "auto_page": "كشف تلقائي (صفحة)",
        "auto_bulk": "كشف جماعي (نطاق)",
        "prev": "السابق",
        "next": "التالي",
        "home": "الرئيسية",
        "detect_msg": "تم كشف {} سؤال.",
        "no_detect_msg": "لم يتم كشف أسئلة أو الملف ليس PDF.",
        "bulk_prompt": "أدخل نطاق الصفحات (الإجمالي: {})\nالصيغة: بداية-نهاية",
        "bulk_confirm": "سيتم استبدال القص الموجود في {} صفحة.\nهل أنت متأكد؟",
        "processing": "جاري المعالجة...",
        "saved_msg": "تم حفظ {} صورة (وتم دمج المجموعات).",
        "ext_title": "محول النص إلى JSON",
        "ext_input": "الملف المصدري",
        "browse": "تصفح...",
        "parsing_opts": "خيارات التحليل",
        "opt_split": "تفعيل وضع 'فصل المحاضرات/الفصول'",
        "opt_inline": "اعتبار النص بجانب 'الحل' ملاحظة",
        "opt_multiline": "اعتبار الأسطر أسفل 'الحل' ملاحظة",
        "out_opts": "خيارات الحفظ",
        "use_fname": "استخدام اسم الملف كاسم للمجلد",
        "use_custom": "اسم مجلد مخصص:",
        "create_img": "إنشاء مجلد للصور 'images'",
        "run_btn": "بدء التحويل",
        "help_btn": "شرح الخيارات",
        "settings_btn": "إعدادات الكلمات المفتاحية",
        "error_sel": "يرجى اختيار ملف نصي أولاً.",
        "success_header": "تمت العملية",
        "error_header": "خطأ",
        "view_sel_folder": "اختر بنك الأسئلة:",
        "view_lbl_q": "سؤال رقم: {}",
        "view_show_ans": "إظهار الإجابة (Space)",
        "view_hide_ans": "إخفاء الإجابة",
        "view_always_show": "إظهار الإجابة تلقائياً عند التنقل",
        "view_correct": "إجابة صحيحة!",
        "view_wrong": "إجابة خاطئة، حاول مجدداً.",
        "view_ans_header": "الإجابة الصحيحة:",
        "view_note_header": "ملاحظة / الشرح:",
        "align_title": "خيارات الدمج",
        "align_label": "محاذاة الصور المدمجة:",
        "align_menu": "محاذاة الدمج",
        "align_right": "يمين",
        "align_center": "وسط",
        "align_left": "يسار",
        "link_prompt_id": "أدخل رقم السؤال الرئيسي (Global ID):",
        "link_prompt_order": "أدخل ترتيب هذا الجزء (1, 2, 3...):",
        "renumber_link_title": "تغيير ترتيب الجزء",
        "renumber_link_msg": "أدخل الترتيب الجديد لهذا الجزء:",
        "edit_btn": "تعديل السؤال",
        "edit_title": "تعديل بيانات السؤال",
        "save_changes": "حفظ التعديلات",
        "cancel": "إلغاء",
        "delete_q": "حذف السؤال نهائياً",
        "confirm_delete": "هل أنت متأكد من حذف هذا السؤال؟ سيتم إعادة ترتيب الصور تلقائياً.",
        "replace_img": "استبدال الصورة",
        "crop_img": "قص الصورة (أداة القص)",
        "shortcuts_menu": "اختصارات لوحة المفاتيح",
        "shortcuts_title": "تخصيص الاختصارات",
        "keyword_title": "إعدادات الكلمات المفتاحية",
        "key_action": "الإجراء",
        "key_shortcut": "الاختصار",
        "key_save": "حفظ الإعدادات",
        "kw_ans": "كلمات الحل (سطر جديد لكل كلمة)",
        "kw_note": "كلمات الملاحظة (سطر جديد لكل كلمة)",
        "kw_stop": "أحرف التوقف",
        "help_html": """
        <h2 style='color: #4da3ff;'>دليل الخيارات التفصيلي</h2>
        <hr>
        <h3 style='color: #4CAF50;'>1. الملاحظات المضمنة (نفس السطر)</h3>
        <p>عند التفعيل، يتم حفظ النص الموجود بعد الإجابة مباشرة كملاحظة.</p>
        <p><b>مثال:</b> <code>الجواب: أ (لأن 1+1=2)</code> -> سيتم حفظ القوسين كشرح.</p>
        
        <h3 style='color: #4CAF50;'>2. الملاحظات (الأسطر بالأسفل)</h3>
        <p>يتم دمج جميع الأسطر الموجودة تحت سطر الحل وحفظها كشرح للسؤال، حتى يبدأ السؤال الجديد.</p>
        
        <h3 style='color: #ff9800;'>3. فصل المحاضرات</h3>
        <p>استخدم هذا الخيار إذا كان الملف يحتوي على فصول متعددة (إعادة ترقيم من جديد).</p>
        <p><b>كيف يعمل؟</b><br>
        إذا وصل البرنامج للسؤال رقم 50، ثم وجد بعده السؤال رقم 1، سيفهم أن هذا فصل جديد، وسيقوم بحفظ الفصل الأول في مجلد منفصل، ويبدأ مجلداً جديداً للفصل الثاني.</p>
        """
    },
    "en": {
        "app_title": "BB-QBox",
        "menu_cropper": "Image Cropper (PDF/Img)",
        "menu_extractor": "Text Question Extractor (Txt)",
        "menu_viewer": "Question Bank Viewer",
        "menu_footer": "v3.1 - Stable Release",
        "lang_switch": "التبديل للعربية",
        "back_menu": "Back to Main Menu",
        "open_files": "Open",
        "save": "Save",
        "undo": "Undo",
        "redo": "Redo",
        "delete": "Delete",
        "renumber": "Renumber",
        "link_crops": "Link Crop (Global ID)",
        "unlink_crops": "Unlink (Make Independent)",
        "auto_page": "Auto Detect (Page)",
        "auto_bulk": "Bulk Detect (Range)",
        "prev": "Previous",
        "next": "Next",
        "home": "Home",
        "detect_msg": "Detected {} questions.",
        "no_detect_msg": "No questions detected or not a PDF.",
        "bulk_prompt": "Enter Page Range (Total: {})\nFormat: Start-End",
        "bulk_confirm": "This will overwrite existing crops on {} pages.\nProceed?",
        "processing": "Processing...",
        "saved_msg": "Saved {} images (groups merged).",
        "ext_title": "Text to JSON Extractor",
        "ext_input": "Input Source",
        "browse": "Browse",
        "parsing_opts": "Parsing Logic",
        "opt_split": "Enable 'Lecture/Chapter Split' Mode",
        "opt_inline": "Treat text next to 'Answer' as Note",
        "opt_multiline": "Treat lines under 'Answer' as Note",
        "out_opts": "Output Settings",
        "use_fname": "Use Source Filename as Folder Name",
        "use_custom": "Custom Folder Name:",
        "create_img": "Create 'images' subfolder",
        "run_btn": "Extract & Convert",
        "help_btn": "Help / Examples",
        "settings_btn": "Keyword Settings",
        "error_sel": "Please select a text file first.",
        "success_header": "Success",
        "error_header": "Error",
        "view_sel_folder": "Select Question Bank:",
        "view_lbl_q": "Question #: {}",
        "view_show_ans": "Show Answer (Space)",
        "view_hide_ans": "Hide Answer",
        "view_always_show": "Always show answer when navigating",
        "view_correct": "Correct Answer!",
        "view_wrong": "Wrong Answer, try again.",
        "view_ans_header": "Correct Answer:",
        "view_note_header": "Note / Explanation:",
        "align_title": "Merge Options",
        "align_label": "Merged Image Alignment:",
        "align_menu": "Merge Alignment",
        "align_right": "Right",
        "align_center": "Center",
        "align_left": "Left",
        "link_prompt_id": "Enter Main Question ID (Global):",
        "link_prompt_order": "Enter Sub-Order (1, 2, 3...):",
        "renumber_link_title": "Change Sub-Order",
        "renumber_link_msg": "Enter new order for this part:",
        "edit_btn": "Edit Question",
        "edit_title": "Edit Question Data",
        "save_changes": "Save Changes",
        "cancel": "Cancel",
        "delete_q": "Delete Question Permanently",
        "confirm_delete": "Are you sure? This will delete the question and reorder subsequent images.",
        "replace_img": "Replace Image",
        "crop_img": "Crop Image (Open Tool)",
        "shortcuts_menu": "Keyboard Shortcuts",
        "shortcuts_title": "Customize Shortcuts",
        "keyword_title": "Keyword Settings",
        "key_action": "Action",
        "key_shortcut": "Shortcut",
        "key_save": "Save Settings",
        "kw_ans": "Answer Keywords",
        "kw_note": "Note Keywords",
        "kw_stop": "Stop Chars",
        "help_html": """
        <h2>Detailed Options Guide</h2>
        <hr>
        <h3>1. Inline Notes</h3>
        <p>Text on the same line as the answer is saved as a note.</p>
        <h3>2. Multiline Notes</h3>
        <p>Lines below the answer line are saved as a detailed explanation.</p>
        <h3>3. Lecture Splitting</h3>
        <p>Use this if your file has multiple chapters (renumbering resets).</p>
        """
    }
}

class ConfigManager:
    @staticmethod
    def _load_json():
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except: return {}
        return {}

    @staticmethod
    def _save_json(data):
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def get_language():
        data = ConfigManager._load_json()
        return data.get("language", "ar")

    @staticmethod
    def set_language(lang):
        data = ConfigManager._load_json()
        data["language"] = lang
        ConfigManager._save_json(data)
    
    @staticmethod
    def get_config_value(key, default=None):
        data = ConfigManager._load_json()
        return data.get(key, default)

    @staticmethod
    def set_config_value(key, value):
        data = ConfigManager._load_json()
        data[key] = value
        ConfigManager._save_json(data)

    @staticmethod
    def save_window_state(name, window):
        data = ConfigManager._load_json()
        if "windows" not in data: data["windows"] = {}
        
        state = {
            "w": window.width(),
            "h": window.height(),
            "x": window.x(),
            "y": window.y(),
            "maximized": window.isMaximized()
        }
        data["windows"][name] = state
        ConfigManager._save_json(data)

    @staticmethod
    def load_window_state(name, window):
        data = ConfigManager._load_json()
        windows = data.get("windows", {})
        state = windows.get(name)
        if state:
            if state.get("w") > 100 and state.get("h") > 100:
                window.resize(state["w"], state["h"])
                window.move(state["x"], state["y"])
            if state.get("maximized", False):
                window.showMaximized()

def tr(key):
    lang = ConfigManager.get_language()
    return TRANS.get(lang, TRANS["en"]).get(key, key)

# --- PDF/Image Utils ---
PDF_ZOOM = 3.0 

def load_pdf_page(doc, page_num):
    page = doc.load_page(page_num)
    mat = fitz.Matrix(PDF_ZOOM, PDF_ZOOM)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.samples
    qt_img = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qt_img)

def load_image_file(path):
    return QPixmap(path)

def analyze_pdf_layout(doc, page_num):
    page = doc.load_page(page_num)
    blocks = page.get_text("blocks", sort=True)
    detected_rects = []
    curr_rect = None
    page_h = page.rect.height
    header_margin = page_h * 0.10
    footer_margin = page_h * 0.93
    
    cfg = ConfigManager._load_json()
    stop_keywords = cfg.get("answer_keywords", []) + cfg.get("note_keywords", []) + ["Blue Bits"]
    if not stop_keywords: stop_keywords = ["الحل", "الجواب", "ملاحظة"]

    question_start_pattern = re.compile(r'^(\d+\s*[-–.)]|[-–.)]\s*\d+)')

    for b in blocks:
        x0, y0, x1, y1, text, _, _ = b
        text = text.strip()
        if not text or y0 < header_margin or y0 > footer_margin: continue
        if any(k in text for k in stop_keywords):
            if curr_rect:
                detected_rects.append(curr_rect)
                curr_rect = None
            continue 
        is_new_q = question_start_pattern.match(text)
        if is_new_q:
            if curr_rect: detected_rects.append(curr_rect)
            curr_rect = [x0, y0, x1, y1]
        else:
            if curr_rect:
                c_x0, c_y0, c_x1, c_y1 = curr_rect
                curr_rect = [min(c_x0, x0), min(c_y0, y0), max(c_x1, x1), max(c_y1, y1)]

    if curr_rect: detected_rects.append(curr_rect)

    final_qrects = []
    padding = 5
    for r in detected_rects:
        rx0, ry0, rx1, ry1 = r
        ui_x = rx0 * PDF_ZOOM
        ui_y = ry0 * PDF_ZOOM
        ui_w = (rx1 - rx0) * PDF_ZOOM
        ui_h = (ry1 - ry0) * PDF_ZOOM
        final_qrects.append(QRectF(ui_x - padding, ui_y - padding, ui_w + (padding*2), ui_h + (padding*2)))

    return final_qrects

def save_cropped_images_merged(file_list, pages_data, destination_folder, alignment="right"):
    # (Restored to original working logic)
    questions_map = {} 
    auto_counter = 1
    sorted_page_indices = sorted(pages_data.keys())
    
    for page_idx in sorted_page_indices:
        crops_list = pages_data[page_idx]
        if not crops_list: continue
        
        file_type, file_obj, *extra = file_list[page_idx]
        pil_source = None
        if file_type == 'img':
            pil_source = Image.open(file_obj)
        else:
            doc = file_obj
            page_num = extra[0]
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(PDF_ZOOM, PDF_ZOOM))
            pil_source = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        img_w, img_h = pil_source.size

        for crop_data in crops_list:
            rect = crop_data['rect']
            man_id = crop_data.get('id')
            man_order = crop_data.get('order', 0)
            
            x1 = max(0, int(rect.left()))
            y1 = max(0, int(rect.top()))
            x2 = min(img_w, int(rect.right()))
            y2 = min(img_h, int(rect.bottom()))
            if x2 <= x1 or y2 <= y1: continue
            try:
                sub_img = pil_source.crop((x1, y1, x2, y2))
            except: continue

            final_id = 0
            if man_id is not None and man_id > 0:
                final_id = man_id
                if final_id >= auto_counter:
                    auto_counter = final_id + 1
            else:
                final_id = auto_counter
                auto_counter += 1
            
            final_order = man_order if man_order is not None else 0
            
            if final_id not in questions_map:
                questions_map[final_id] = []
            questions_map[final_id].append((final_order, sub_img))

    saved_count = 0
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    for q_id, parts in questions_map.items():
        parts.sort(key=lambda x: x[0])
        imgs = [x[1] for x in parts]
        if not imgs: continue
        
        if len(imgs) == 1:
            final_img = imgs[0]
        else:
            total_h = sum(img.height for img in imgs)
            max_w = max(img.width for img in imgs)
            final_img = Image.new('RGB', (max_w, total_h), (255, 255, 255))
            
            curr_y = 0
            for img in imgs:
                x_pos = 0
                if alignment == "right":
                    x_pos = max_w - img.width
                elif alignment == "center":
                    x_pos = (max_w - img.width) // 2
                else: 
                    x_pos = 0
                
                final_img.paste(img, (x_pos, curr_y))
                curr_y += img.height
        
        try:
            save_path = os.path.join(destination_folder, f"{q_id}.jpg")
            final_img.save(save_path, "JPEG", quality=95)
            saved_count += 1
        except Exception as e:
            print(f"Error saving {q_id}: {e}")

    return saved_count
# --- END OF FILE utils.py ---
# --- START OF FILE core/pdf_ops.py ---
import fitz  # PyMuPDF
import re
import os
import logging
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QRectF
from core.config import ConfigManager

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
        
        # Original simple stop check
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
    questions_map = {} 
    notes_map = {}
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
            is_note = crop_data.get('is_note', False)
            
            x1 = max(0, int(rect.left()))
            y1 = max(0, int(rect.top()))
            x2 = min(img_w, int(rect.right()))
            y2 = min(img_h, int(rect.bottom()))
            if x2 <= x1 or y2 <= y1: continue
            try:
                sub_img = pil_source.crop((x1, y1, x2, y2))
            except Exception as e:
                logging.warning("Failed to crop image region: %s", e)
                continue

            final_id = 0
            if man_id is not None and man_id > 0:
                final_id = man_id
                if not is_note and final_id >= auto_counter:
                    auto_counter = final_id + 1
            else:
                if is_note:
                    final_id = max(1, auto_counter - 1)
                else:
                    final_id = auto_counter
                    auto_counter += 1
            
            final_order = man_order if man_order is not None else 0
            
            if is_note:
                if final_id not in notes_map:
                    notes_map[final_id] = []
                notes_map[final_id].append((final_order, sub_img))
            else:
                if final_id not in questions_map:
                    questions_map[final_id] = []
                questions_map[final_id].append((final_order, sub_img))

    saved_count = 0
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    def merge_and_save(img_list, save_path):
        if len(img_list) == 1:
            final_img = img_list[0]
        else:
            total_h = sum(img.height for img in img_list)
            max_w = max(img.width for img in img_list)
            final_img = Image.new('RGB', (max_w, total_h), (255, 255, 255))
            
            curr_y = 0
            for img in img_list:
                x_pos = 0
                if alignment == "right":
                    x_pos = max_w - img.width
                elif alignment == "center":
                    x_pos = (max_w - img.width) // 2
                else: 
                    x_pos = 0
                
                final_img.paste(img, (x_pos, curr_y))
                curr_y += img.height
        final_img.save(save_path, "JPEG", quality=95)

    for q_id, parts in questions_map.items():
        parts.sort(key=lambda x: x[0])
        imgs = [x[1] for x in parts]
        if not imgs: continue
        
        try:
            save_path = os.path.join(destination_folder, f"{q_id}.jpg")
            merge_and_save(imgs, save_path)
            saved_count += 1
        except Exception as e:
            logging.error("Error saving question %s: %s", q_id, e)

    for q_id, parts in notes_map.items():
        parts.sort(key=lambda x: x[0])
        imgs = [x[1] for x in parts]
        if not imgs: continue
        
        try:
            save_path = os.path.join(destination_folder, f"{q_id}_note.jpg")
            merge_and_save(imgs, save_path)
        except Exception as e:
            logging.error("Error saving note %s: %s", q_id, e)

    return saved_count
# --- END OF FILE core/pdf_ops.py ---
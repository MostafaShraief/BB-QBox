# --- START OF FILE ui/window.py ---
import os
import logging
import fitz
import copy
from PyQt6.QtWidgets import (QMainWindow, QFileDialog, QMessageBox, 
                             QLabel, QVBoxLayout, QWidget, QToolBar, 
                             QStatusBar, QInputDialog, QProgressDialog, QApplication,
                             QMenu, QPushButton)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt, QSize, QUrl

from core.config import ConfigManager
from core.pdf_ops import load_pdf_page, load_image_file, save_cropped_images_merged, analyze_pdf_layout
from ui.common import tr
from ui.canvas import EditorScene, ImageEditorView, CropItem

class ImageCropperApp(QMainWindow):
    def __init__(self, single_image_mode=False):
        super().__init__()
        self.setWindowTitle(tr("menu_cropper"))
        self.resize(1200, 800)
        self.setAcceptDrops(True)
        
        if ConfigManager.get_language() == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.file_list =[]
        self.current_index = 0
        self.merge_alignment = "right"
        self.pages_crops = {} 
        self.undo_stack =[]
        self.redo_stack =[]
        self.single_image_mode = single_image_mode

        ConfigManager.load_window_state("cropper", self)
        self.init_ui()

    def closeEvent(self, event):
        ConfigManager.save_window_state("cropper", self)
        super().closeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            supported = ('.pdf', '.png', '.jpg', '.jpeg')
            if any(url.toLocalFile().lower().endswith(supported) for url in event.mimeData().urls()):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        paths =[url.toLocalFile() for url in event.mimeData().urls()
                 if url.toLocalFile().lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))]
        if paths:
            self.load_files(paths)
            event.acceptProposedAction()

    def init_ui(self):
        central_widget = QWidget()
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central_widget)

        self.toolbar = QToolBar("Main")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)

        if not self.single_image_mode:
            self.add_action("Home", tr("home"), self.go_home, None)
            self.toolbar.addSeparator()
            self.add_action("Open", tr("open_files"), self.open_files_dialog, None)
            
        self.add_action("Save", tr("save"), self.perform_save_direct, "save")
        
        if not self.single_image_mode:
            self.btn_align = QPushButton(tr("align_menu") + f" ({tr('align_right')})")
            menu = QMenu(self)
            for k in["right", "center", "left"]:
                menu.addAction(tr(f"align_{k}"), lambda m=k: self.set_alignment(m, tr(f"align_{m}")))
            self.btn_align.setMenu(menu)
            self.toolbar.addWidget(self.btn_align)

        self.toolbar.addSeparator()
        self.act_undo = self.add_action("Undo", tr("undo"), self.undo, "undo")
        self.act_redo = self.add_action("Redo", tr("redo"), self.redo, "redo")
        
        self.toolbar.addSeparator()
        self.add_action("Delete", tr("delete"), self.delete_selected_crop, "delete")
        self.add_action("Renumber", tr("renumber"), self.renumber_selected_crop, "renumber")
        
        self.toolbar.addSeparator()
        self.add_action("Link", tr("link_crops"), self.link_crop_manual, "link")
        
        self.act_note_mode = QAction("🟩 " + tr("mark_note"), self)
        self.act_note_mode.setCheckable(True)
        sc = ConfigManager.get_config_value("shortcuts", {}).get("mark_note", "")
        if sc: self.act_note_mode.setShortcut(QKeySequence(sc))
        self.act_note_mode.toggled.connect(self.toggle_note_mode)
        self.toolbar.addAction(self.act_note_mode)
        
        self.add_action("Unlink", tr("unlink_crops"), self.unlink_crop, "unlink")

        if not self.single_image_mode:
            self.toolbar.addSeparator()
            self.add_action("DetectPage", tr("auto_page"), self.auto_detect_current_page, "detect_page")
            self.add_action("DetectBulk", tr("auto_bulk"), self.auto_detect_batch, "detect_bulk")
            self.toolbar.addSeparator()
            
            self.act_prev = self.add_action("Prev", tr("prev"), lambda: self.navigate(-1), "prev")
            self.lbl_page_info = QLabel(" 0 / 0 ")
            self.toolbar.addWidget(self.lbl_page_info)
            self.act_next = self.add_action("Next", tr("next"), lambda: self.navigate(1), "next")
        
        self.update_undo_redo_buttons()

        self.scene = EditorScene()
        self.view = ImageEditorView(self.scene)
        self.layout.addWidget(self.view)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.scene.interaction_started.connect(self.push_undo)
        self.scene.item_geometry_changed.connect(self.handle_geometry_update)
        self.scene.item_created.connect(self.handle_creation)

    def add_action(self, uid, name, method, config_key):
        action = QAction(name, self)
        if config_key:
            sc = ConfigManager.get_config_value("shortcuts", {}).get(config_key, "")
            if sc:
                action.setShortcut(QKeySequence(sc))
                action.setToolTip(f"{name} ({sc})")
            else:
                action.setToolTip(name)
        
        action.triggered.connect(method)
        self.toolbar.addAction(action)
        return action

    def toggle_note_mode(self, checked):
        self.scene.note_mode = checked
        if checked:
            self.act_note_mode.setText("🟩 " + tr("mark_note") + " (ON)")
        else:
            self.act_note_mode.setText("🟩 " + tr("mark_note"))

    def set_alignment(self, mode, label):
        self.merge_alignment = mode
        self.btn_align.setText(tr("align_menu") + f" ({label})")

    def go_home(self):
        from ui.menu import MainMenu
        self.menu = MainMenu(None)
        self.menu.show()
        self.close()

    def get_current_page_crops(self):
        if self.current_index not in self.pages_crops: self.pages_crops[self.current_index] =[]
        return self.pages_crops[self.current_index]

    def _calc_auto_id_start(self):
        count = 1
        for p in sorted(self.pages_crops.keys()):
            if p == self.current_index: break
            for item in self.pages_crops[p]:
                if item.get('id') is None and not item.get('is_note', False): 
                    count += 1
        return count

    def link_crop_manual(self):
        sel = self.scene.selectedItems()
        if not sel or not isinstance(sel[0], CropItem): return
        item = sel[0]
        data = self.get_current_page_crops()[item.unique_id]
        
        default_id = max(1, self._calc_auto_id_start() - 1)
        gid, ok = QInputDialog.getInt(self, tr("link_crops"), tr("link_prompt_id"), default_id, 1, 99999)
        if ok:
            order, ok2 = QInputDialog.getInt(self, tr("link_crops"), tr("link_prompt_order"), 1, 0, 99)
            if ok2:
                self.push_undo()
                data['id'] = gid; data['order'] = order
                self.draw_overlays_only()

    def unlink_crop(self):
        self.push_undo()
        for item in self.scene.selectedItems():
            if isinstance(item, CropItem):
                c = self.get_current_page_crops()[item.unique_id]
                c['id'] = None; c['order'] = None; c['is_note'] = False
        self.draw_overlays_only()

    def renumber_selected_crop(self):
        sel = self.scene.selectedItems()
        if not sel: return
        self.push_undo()
        item = sel[0]
        lst = self.get_current_page_crops()
        if item.unique_id < len(lst):
             new_pos, ok = QInputDialog.getInt(self, tr("renumber"), "Position:", item.unique_id + 1, 1, len(lst))
             if ok:
                 lst.insert(new_pos-1, lst.pop(item.unique_id))
                 self.draw_overlays_only()
    
    def delete_selected_crop(self):
        sel = self.scene.selectedItems()
        if not sel: return
        self.push_undo()
        lst = self.get_current_page_crops()
        for i in sorted([x.unique_id for x in sel if isinstance(x, CropItem)], reverse=True):
            if i < len(lst): lst.pop(i)
        self.draw_overlays_only()

    def handle_geometry_update(self, idx, rect):
        self.get_current_page_crops()[idx]['rect'] = rect
        
    def handle_creation(self, rect, is_note):
        self.get_current_page_crops().append({'rect': rect, 'id': None, 'order': None, 'is_note': is_note})
        self.get_current_page_crops().sort(key=lambda x: x['rect'].top())
        self.draw_overlays_only()

    def draw_overlays_only(self):
        self.scene.clearSelection()
        for i in self.scene.items(): 
            if isinstance(i, CropItem): self.scene.removeItem(i)
        
        crops = self.get_current_page_crops()
        crops.sort(key=lambda x: x['rect'].top())
        cnt = self._calc_auto_id_start()
        
        for i, d in enumerate(crops):
            is_note = d.get('is_note', False)
            if not d.get('id'):
                display_id = max(1, cnt - 1) if is_note else cnt
            else:
                display_id = d['id']
                
            lbl = f"{display_id}_{d.get('order', '')}" if d.get('order') else str(display_id)
            if is_note:
                lbl += " (N)"
                
            if not d.get('id') and not is_note: 
                cnt += 1
                
            self.scene.addItem(CropItem(d['rect'], self.scene, i, lbl, bool(d.get('id')), is_note))

    def auto_detect_current_page(self):
        if not self.file_list: return
        self.push_undo()
        f = self.file_list[self.current_index]
        if f[0] == 'pdf':
            try:
                is_note = self.scene.note_mode
                r = analyze_pdf_layout(f[1], f[2], detect_notes_only=is_note)
                if is_note:
                    new_crops =[{'rect': x, 'id': None, 'order': None, 'is_note': True} for x in r]
                    self.pages_crops[self.current_index].extend(new_crops)
                else:
                    self.pages_crops[self.current_index] =[{'rect': x, 'id': None, 'order': None, 'is_note': False} for x in r]
                self.draw_overlays_only()
            except Exception as e:
                logging.warning("Auto-detect failed: %s", e)

    def auto_detect_batch(self):
        if not self.file_list: return
        text, ok = QInputDialog.getText(self, tr("auto_bulk"), tr("bulk_prompt").format(len(self.file_list)), text="2-{}".format(len(self.file_list)))
        if ok and text:
            try:
                if '-' in text: s, e = map(int, text.split('-'))
                else: s = e = int(text)
                self.push_undo()
                pd = QProgressDialog(tr("processing"), "Cancel", 0, e-s+1, self)
                pd.setWindowModality(Qt.WindowModality.WindowModal)
                cnt = 0
                is_note = self.scene.note_mode
                for i in range(s-1, e):
                    if pd.wasCanceled(): break
                    f = self.file_list[i]
                    if f[0] == 'pdf':
                        r = analyze_pdf_layout(f[1], f[2], detect_notes_only=is_note)
                        if is_note:
                            new_crops =[{'rect': x, 'id': None, 'order': None, 'is_note': True} for x in r]
                            if i not in self.pages_crops:
                                self.pages_crops[i] = []
                            self.pages_crops[i].extend(new_crops)
                        else:
                            self.pages_crops[i] =[{'rect':x, 'id':None, 'order':None, 'is_note': False} for x in r]
                    cnt += 1; pd.setValue(cnt); QApplication.processEvents()
                if (s-1) <= self.current_index < e: self.draw_overlays_only()
            except Exception as e:
                logging.warning("Auto-detect batch failed: %s", e)

    def navigate(self, d):
        n = self.current_index + d
        if 0 <= n < len(self.file_list):
            self.current_index = n
            self.load_page(n, True)
            self.update_labels()
            
    def update_labels(self):
        self.lbl_page_info.setText(f" {self.current_index+1} / {len(self.file_list)} ")

    def load_page(self, idx, fit=False):
        self.scene.clear()
        t, o, e = self.file_list[idx]
        pix = load_pdf_page(o, e) if t == 'pdf' else load_image_file(o)
        self.scene.addPixmap(pix)
        self.scene.setSceneRect(0, 0, pix.width(), pix.height())
        if fit: self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.draw_overlays_only()

    def open_files_dialog(self):
        f, _ = QFileDialog.getOpenFileNames(self, tr("open_files"), "", "Files (*.pdf *.png *.jpg)")
        if f: self.load_files(f)
        
    def load_files(self, paths):
        self.file_list =[]
        for p in sorted(paths):
            if p.lower().endswith('.pdf'):
                d = fitz.open(p)
                for i in range(len(d)): self.file_list.append(('pdf', d, i))
            else: self.file_list.append(('img', p, None))
        if self.file_list:
            self.current_index = 0
            self.pages_crops = {}
            self.undo_stack.clear()
            self.load_page(0, True)
            self.update_labels()

    def load_single_image(self, path):
        self.file_list = [('img', path, None)]
        self.current_index = 0
        self.pages_crops = {}
        self.undo_stack.clear()
        self.load_page(0, True)

    def perform_save_direct(self):
        if self.single_image_mode:
            try:
                _, path, _ = self.file_list[0]
                save_cropped_images_merged(self.file_list, self.pages_crops, os.path.dirname(path), self.merge_alignment)
                gen_path = os.path.join(os.path.dirname(path), "1.jpg")
                if os.path.exists(gen_path):
                     import shutil
                     shutil.move(gen_path, path)
                QMessageBox.information(self, tr("success_header"), tr("saved_msg").format(1))
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        else:
            folder = QFileDialog.getExistingDirectory(self, tr("save"))
            if folder:
                c = save_cropped_images_merged(self.file_list, self.pages_crops, folder, self.merge_alignment)
                QMessageBox.information(self, tr("success_header"), tr("saved_msg").format(c))
    
    def push_undo(self):
        self.undo_stack.append(copy.deepcopy(self.pages_crops))
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.update_undo_redo_buttons()
    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.pages_crops))
            self.pages_crops = self.undo_stack.pop()
            self.update_undo_redo_buttons()
            self.draw_overlays_only()
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.pages_crops))
            self.pages_crops = self.redo_stack.pop()
            self.update_undo_redo_buttons()
            self.draw_overlays_only()
    def update_undo_redo_buttons(self):
        self.act_undo.setEnabled(bool(self.undo_stack))
        self.act_redo.setEnabled(bool(self.redo_stack))
# --- END OF FILE ui/window.py ---
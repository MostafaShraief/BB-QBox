# --- START OF FILE ui/canvas.py ---
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QWheelEvent, QAction

class Handle:
    NONE = 0
    TOP_LEFT = 1; TOP = 2; TOP_RIGHT = 3
    RIGHT = 4; BOTTOM_RIGHT = 5; BOTTOM = 6
    BOTTOM_LEFT = 7; LEFT = 8; MOVE = 9

class ImageEditorView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRubberBandSelectionMode(Qt.ItemSelectionMode.IntersectsItemShape)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag) 

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in = event.angleDelta().y() > 0
            self.do_zoom(zoom_in)
            event.accept()
        else:
            super().wheelEvent(event)

    def do_zoom(self, zoom_in=True):
        factor = 1.15 if zoom_in else 1 / 1.15
        self.scale(factor, factor)

class CropItem(QGraphicsRectItem):
    def __init__(self, rect, scene_parent, unique_id, display_text, is_linked_child=False, is_note=False):
        super().__init__(rect)
        self.scene_parent = scene_parent
        self.unique_id = unique_id 
        self.display_text = display_text
        self.is_linked_child = is_linked_child
        self.is_note = is_note
        
        self.setFlags(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
        self.update_style()
        
        self.current_handle = Handle.NONE
        self.resize_start_pos = None
        self.initial_rect = None
        self.is_interacting = False

    def update_style(self):
        # Default Red
        color = QColor("#FF3333") 
        fill = QColor(255, 51, 51, 50)
        
        # Linked (Child) Green
        if self.is_linked_child:
            color = QColor("#4CAF50")
            fill = QColor(76, 175, 80, 50)
            
        # Note Blue
        if self.is_note:
            color = QColor("#4da3ff")
            fill = QColor(77, 163, 255, 50)

        self.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))
        self.setBrush(QBrush(fill))

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        rect = self.rect()
        
        bg_color = QColor("#D90000")
        if self.is_linked_child: bg_color = QColor("#388E3C")
        if self.is_note: bg_color = QColor("#1976D2")
        
        text = str(self.display_text)
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        fm = lambda: painter.fontMetrics()
        
        badge_w = max(24, fm().horizontalAdvance(text) + 10)
        badge_h = 24

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRect(QRectF(rect.left(), rect.top(), badge_w, badge_h))
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(font)
        painter.drawText(QRectF(rect.left(), rect.top(), badge_w, badge_h), 
                         Qt.AlignmentFlag.AlignCenter, text)
        
        if self.isSelected():
            painter.setBrush(Qt.GlobalColor.white)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            r = 6
            for x, y in [(rect.left(), rect.top()), (rect.right()-r, rect.top()),
                         (rect.right()-r, rect.bottom()-r), (rect.left(), rect.bottom()-r)]:
                painter.drawRect(QRectF(x, y, r, r))

    def get_handle_at(self, pos):
        r = self.rect(); m = 10
        x, y = pos.x(), pos.y()
        if abs(x - r.left()) < m and abs(y - r.top()) < m: return Handle.TOP_LEFT
        if abs(x - r.right()) < m and abs(y - r.bottom()) < m: return Handle.BOTTOM_RIGHT
        if abs(x - r.right()) < m and abs(y - r.top()) < m: return Handle.TOP_RIGHT
        if abs(x - r.left()) < m and abs(y - r.bottom()) < m: return Handle.BOTTOM_LEFT
        if r.contains(pos): return Handle.MOVE
        return Handle.NONE

    def hoverMoveEvent(self, event):
        handle = self.get_handle_at(event.pos())
        cursors = {
            Handle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor, Handle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            Handle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor, Handle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            Handle.MOVE: Qt.CursorShape.SizeAllCursor
        }
        self.setCursor(cursors.get(handle, Qt.CursorShape.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.current_handle = self.get_handle_at(event.pos())
            if self.current_handle != Handle.NONE:
                self.is_interacting = True
                self.resize_start_pos = event.scenePos()
                self.initial_rect = self.rect()
                self.scene_parent.notify_interaction_start()
                self.setSelected(True)
                event.accept()
            else:
                super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_interacting and self.current_handle != Handle.NONE:
            diff = event.scenePos() - self.resize_start_pos
            r = self.initial_rect
            l, t, w, h = r.left(), r.top(), r.width(), r.height()
            dx, dy = diff.x(), diff.y()

            if self.current_handle == Handle.MOVE:
                new_l = l + dx; new_t = t + dy
                self.setRect(new_l, new_t, w, h)
            else:
                if self.current_handle in [Handle.LEFT, Handle.TOP_LEFT, Handle.BOTTOM_LEFT]: l += dx; w -= dx
                if self.current_handle in [Handle.RIGHT, Handle.TOP_RIGHT, Handle.BOTTOM_RIGHT]: w += dx
                if self.current_handle in [Handle.TOP, Handle.TOP_LEFT, Handle.TOP_RIGHT]: t += dy; h -= dy
                if self.current_handle in [Handle.BOTTOM, Handle.BOTTOM_LEFT, Handle.BOTTOM_RIGHT]: h += dy
                
                if w > 10 and h > 10: self.setRect(l, t, w, h)
            
            self.scene_parent.notify_geometry_change(self.unique_id, self.rect())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.is_interacting = False
        self.current_handle = Handle.NONE
        super().mouseReleaseEvent(event)

class EditorScene(QGraphicsScene):
    interaction_started = pyqtSignal() 
    item_geometry_changed = pyqtSignal(int, QRectF) 
    item_created = pyqtSignal(QRectF)

    def __init__(self):
        super().__init__()
        self.drawing = False
        self.start_point = None
        self.current_temp_item = None

    def notify_interaction_start(self):
        self.interaction_started.emit()

    def notify_geometry_change(self, idx, rect):
        self.item_geometry_changed.emit(idx, rect)

    def mousePressEvent(self, event):
        clicked_item = self.itemAt(event.scenePos(), QGraphicsView().transform())
        is_background = (clicked_item is None) or isinstance(clicked_item, QGraphicsPixmapItem)

        if is_background and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = event.scenePos()
            self.current_temp_item = QGraphicsRectItem(QRectF(self.start_point, self.start_point))
            self.current_temp_item.setPen(QPen(Qt.GlobalColor.red, 1, Qt.PenStyle.DashLine))
            self.addItem(self.current_temp_item)
            self.clearSelection()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing:
            new_rect = QRectF(self.start_point, event.scenePos()).normalized()
            self.current_temp_item.setRect(new_rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drawing:
            self.drawing = False
            final_rect = self.current_temp_item.rect()
            self.removeItem(self.current_temp_item)
            self.current_temp_item = None
            if final_rect.width() > 10 and final_rect.height() > 10:
                self.interaction_started.emit() 
                self.item_created.emit(final_rect)
        super().mouseReleaseEvent(event)
# --- END OF FILE ui/canvas.py ---
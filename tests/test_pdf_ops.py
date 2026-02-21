"""Unit tests for core/pdf_ops.py"""
import os
import sys
import types
import pytest
from unittest.mock import MagicMock
from PIL import Image


# ---------------------------------------------------------------------------
# Provide lightweight stubs so pdf_ops can be imported without a Qt display
# ---------------------------------------------------------------------------

def _make_qt_stubs():
    """Create minimal PyQt6 stubs needed for importing core.pdf_ops."""
    pyqt6_mod = types.ModuleType("PyQt6")
    qtgui = types.ModuleType("PyQt6.QtGui")
    qtcore = types.ModuleType("PyQt6.QtCore")

    qtgui.QImage = MagicMock()
    qtgui.QPixmap = MagicMock()

    class _QRectF:
        def __init__(self, x, y, w, h):
            self._x, self._y, self._w, self._h = x, y, w, h
        def left(self): return self._x
        def top(self): return self._y
        def right(self): return self._x + self._w
        def bottom(self): return self._y + self._h

    qtcore.QRectF = _QRectF
    pyqt6_mod.QtGui = qtgui
    pyqt6_mod.QtCore = qtcore
    sys.modules.setdefault("PyQt6", pyqt6_mod)
    sys.modules.setdefault("PyQt6.QtGui", qtgui)
    sys.modules.setdefault("PyQt6.QtCore", qtcore)
    return _QRectF


# Install stubs before importing the module under test
_QRectF = _make_qt_stubs()

from core.pdf_ops import save_cropped_images_merged  # noqa: E402


def test_merge_and_save_single_image(tmp_path):
    """Test merging a single image saves without modification."""
    img = Image.new("RGB", (100, 50), color=(255, 0, 0))
    img_path = str(tmp_path / "source.jpg")
    img.save(img_path)

    file_list = [('img', img_path, None)]
    pages_data = {
        0: [{'rect': _QRectF(0, 0, 80, 40), 'id': 1, 'order': 0, 'is_note': False}]
    }

    dest = str(tmp_path / "output")
    count = save_cropped_images_merged(file_list, pages_data, dest)
    assert count == 1
    assert os.path.exists(os.path.join(dest, "1.jpg"))


def test_merge_and_save_multiple_parts(tmp_path):
    """Test that multiple parts of the same question are merged vertically."""
    img = Image.new("RGB", (200, 200), color=(0, 255, 0))
    img_path = str(tmp_path / "source.jpg")
    img.save(img_path)

    file_list = [('img', img_path, None)]
    pages_data = {
        0: [
            {'rect': _QRectF(0, 0, 100, 50), 'id': 1, 'order': 1, 'is_note': False},
            {'rect': _QRectF(0, 60, 100, 50), 'id': 1, 'order': 2, 'is_note': False},
        ]
    }

    dest = str(tmp_path / "output")
    count = save_cropped_images_merged(file_list, pages_data, dest)
    assert count == 1
    merged = Image.open(os.path.join(dest, "1.jpg"))
    # Merged height should be sum of part heights
    assert merged.height > 50


def test_save_note_image(tmp_path):
    """Test that note crops are saved as {id}_note.jpg."""
    img = Image.new("RGB", (200, 200), color=(0, 0, 255))
    img_path = str(tmp_path / "source.jpg")
    img.save(img_path)

    file_list = [('img', img_path, None)]
    pages_data = {
        0: [
            {'rect': _QRectF(0, 0, 100, 50), 'id': None, 'order': None, 'is_note': False},
            {'rect': _QRectF(0, 60, 100, 50), 'id': None, 'order': None, 'is_note': True},
        ]
    }

    dest = str(tmp_path / "output")
    save_cropped_images_merged(file_list, pages_data, dest)
    assert os.path.exists(os.path.join(dest, "1_note.jpg"))


def test_invalid_crop_region_skipped(tmp_path):
    """Test that invalid/zero-size crop regions are skipped without error."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    img_path = str(tmp_path / "source.jpg")
    img.save(img_path)

    file_list = [('img', img_path, None)]
    # Zero-size rect
    pages_data = {
        0: [{'rect': _QRectF(50, 50, 0, 0), 'id': 1, 'order': 0, 'is_note': False}]
    }

    dest = str(tmp_path / "output")
    count = save_cropped_images_merged(file_list, pages_data, dest)
    assert count == 0


"""Image buttons that follow the application's active palette."""

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QToolButton


IMAGES_DIR = Path(__file__).resolve().parent / "images"


class IconButton(QToolButton):
    def __init__(self, filename, label, size):
        super().__init__()
        self._image = QPixmap(str(IMAGES_DIR / filename))
        self.setIconSize(QSize(size, size))
        self.set_label(label)

    def set_label(self, label):
        self.setAccessibleName(label)
        self.setToolTip(label)

    def refresh_icon(self):
        if self._image.isNull():
            return
        self.ensurePolished()
        icon = self._image.copy()
        with QPainter(icon) as painter:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(icon.rect(), self.palette().color(QPalette.ColorRole.ButtonText))
        self.setIcon(QIcon(icon))

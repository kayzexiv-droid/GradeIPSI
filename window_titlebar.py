"""Window controls integrated into the application menu bar."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMenuBar, QWidget

from ui_icons import IconButton


class WindowControlButton(IconButton):
    def __init__(self, filename, label, action):
        super().__init__(filename, label, 14)
        self.setObjectName("WindowCloseButton" if filename == "cross.png" else "WindowControlButton")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.clicked.connect(action)


class WindowTitleBar(QMenuBar):
    def __init__(self, window):
        super().__init__(window)
        self.setNativeMenuBar(False)
        self._drag_start = None

        logo_container = QWidget(self)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(10, 0, 6, 0)
        logo = QLabel(logo_container)
        logo.setAccessibleName("GradeIPSI")
        logo.setPixmap(window.windowIcon().pixmap(24, 24))
        logo_layout.addWidget(logo)
        self.command_layout = logo_layout
        self.setCornerWidget(logo_container, Qt.Corner.TopLeftCorner)

        controls = QWidget(self)
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(WindowControlButton("minuss.png", "Réduire", window.showMinimized))
        self.maximize_button = WindowControlButton("vector.png", "Agrandir", self.toggle_maximized)
        self.maximize_button.setCheckable(True)
        layout.addWidget(self.maximize_button)
        layout.addWidget(WindowControlButton("cross.png", "Fermer", window.close))
        self.setCornerWidget(controls, Qt.Corner.TopRightCorner)

    def toggle_maximized(self):
        window = self.window()
        if window.isMaximized() or window.isFullScreen():
            window.showNormal()
        else:
            window.showMaximized()

    def sync_window_state(self):
        can_restore = self.window().isMaximized() or self.window().isFullScreen()
        self.maximize_button.setChecked(can_restore)
        self.maximize_button.set_label("Restaurer" if can_restore else "Agrandir")

    def _is_title_area(self, event):
        return (
            event.button() == Qt.MouseButton.LeftButton
            and self.actionAt(event.position().toPoint()) is None
            and QApplication.activePopupWidget() is None
        )

    def mousePressEvent(self, event):
        if self._is_title_area(event) and not self.window().isFullScreen():
            self._drag_start = event.globalPosition().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.globalPosition().toPoint() - self._drag_start).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self._drag_start = None
                self.window().windowHandle().startSystemMove()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            self._drag_start = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._is_title_area(event):
            self._drag_start = None
            self.toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

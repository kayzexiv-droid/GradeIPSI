import sys
from PySide6.QtWidgets import QApplication
from app_window import GradeTrackerApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GradeTrackerApp()
    window.show()
    sys.exit(app.exec())

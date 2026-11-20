import sys
from PySide6.QtWidgets import QApplication
from app_window import GradeTrackerApp
from update_installer import UPDATE_ERROR_ARGUMENT


if __name__ == "__main__":
    update_error = ""
    if len(sys.argv) > 1 and sys.argv[1].startswith(UPDATE_ERROR_ARGUMENT):
        update_error = sys.argv.pop(1)[len(UPDATE_ERROR_ARGUMENT):]
    app = QApplication(sys.argv)
    window = GradeTrackerApp(update_error)
    window.show()
    sys.exit(app.exec())

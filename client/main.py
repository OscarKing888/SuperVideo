"""SuperVideo Client entry point."""

import sys
import os

# Add project src to path for the classifier and frame extractor modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))
# Add project root for client imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from client.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SuperVideo Client")
    app.setOrganizationName("SuperVideo")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

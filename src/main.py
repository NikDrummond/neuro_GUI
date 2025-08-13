"""Main entry point for the modular Neurosetta GUI application."""

import sys
from PySide2.QtWidgets import QApplication
from ui import MainWindow


def main():
    """Main application entry point."""
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

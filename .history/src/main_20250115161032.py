import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QAction
)
from vedo import Plotter, Points


class MainWindow(QMainWindow):
    def __init__(self, aprent = None):
        super().__init__()
        self.setWindowTitle("3D Point Cloud Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Vedo Plotter
        self.plotter = Plotter(qt_widget=True, bg="white")
        self.setCentralWidget(self.plotter.interactor)

        # Initialize menu bar
        self.init_menu_bar()

    def init_menu_bar(self):
        # Create the menu bar
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Read CSV Action
        read_csv_action = QAction("Read CSV", self)
        read_csv_action.triggered.connect(self.read_csv)
        file_menu.addAction(read_csv_action)

        # Exit Action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close_application)
        file_menu.addAction(exit_action)

    def close_application(self):
        self.close()

    def read_csv(self):
        # Open file dialog to select CSV file
        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)")
        if file_name:
            try:
                # Read CSV file
                df = pd.read_csv(file_name)

                # Validate the presence of x, y, z columns
                if not all(col in df.columns for col in ["x", "y", "z"]):
                    raise ValueError("CSV file must contain 'x', 'y', and 'z' columns")

                # Convert DataFrame to numpy array
                points = df[["x", "y", "z"]].to_numpy()

                # Render the point cloud
                self.render_point_cloud(points)

                QMessageBox.information(self, "Success", f"Successfully loaded point cloud from {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load point cloud: {str(e)}")

    def render_point_cloud(self, points):
        # Create a Vedo Points object
        point_cloud = Points(points, r=5, c="cyan")

        # Clear the existing visualization and add the new point cloud
        self.plotter.clear()
        self.plotter.add(point_cloud)
        self.plotter.show(resetcam=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

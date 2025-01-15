import pyqtgraph.opengl as gl
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox


def load_csv(file_path):
    """
    Load a CSV file containing 3D point cloud data.
    Automatically downsamples large datasets for performance.
    """
    try:
        data = pd.read_csv(file_path)
        if not all(col in data.columns for col in ['x', 'y', 'z']):
            raise ValueError("CSV file must contain 'x', 'y', and 'z' columns.")

        if len(data) > 100000:  # Example threshold
            QMessageBox.warning(None, "Large Dataset",
                                 f"The file contains {len(data)} points. Downsampling for performance.")
            data = data.sample(100000)

        points = data[['x', 'y', 'z']].to_numpy()
        return points
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to load CSV: {e}")
        return None



def main():
    # Create the application
    app = QApplication([])

    # File dialog to load a CSV file
    file_dialog = QFileDialog()
    file_path, _ = file_dialog.getOpenFileName(
        None,
        "Open Point Cloud CSV File",
        "",
        "CSV Files (*.csv);;All Files (*)"
    )

    if not file_path:
        QMessageBox.warning(None, "No File Selected", "Please select a CSV file to continue.")
        return

    # Load point cloud data
    points = load_csv(file_path)
    if points is None:
        return

    # Create a 3D view widget
    widget = gl.GLViewWidget()
    widget.setWindowTitle("3D Point Cloud Viewer")
    widget.show()

    # Create and display the point cloud
    scatter = gl.GLScatterPlotItem(pos=points, color=(0, 1, 0, 1), size=5)  # Green points
    widget.addItem(scatter)

    # Start the application loop
    app.exec()


if __name__ == "__main__":
    main()

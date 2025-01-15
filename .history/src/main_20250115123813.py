import pyqtgraph.opengl as gl
import numpy as np
from PySide6.QtWidgets import QApplication

def main():
    # Create the application
    app = QApplication([])

    # Create a 3D view widget
    widget = gl.GLViewWidget()
    widget.setWindowTitle("3D Point Cloud Viewer")
    widget.show()

    # Generate example point cloud data
    points = np.random.rand(1000, 3) * 10  # 1000 points in a 10x10x10 space
    scatter = gl.GLScatterPlotItem(pos=points, color=(1, 0, 0, 1), size=5)  # Red points
    widget.addItem(scatter)

    

    # Start the application loop
    app.exec()

if __name__ == "__main__":
    main()
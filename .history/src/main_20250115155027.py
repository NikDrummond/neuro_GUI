import sys
from PyQt5 import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vedo import Plotter, Cone, printc
import Neurosetta as nr

import sys
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QFileDialog, QMessageBox, QAction
)
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk



# main viewer class widget
class MainWindow(Qt.QMainWindow):

    def __init__(self, parent=None):

        Qt.QMainWindow.__init__(self, parent)
        self.frame = Qt.QFrame()
        self.layout = Qt.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)

        # Create renderer and add the vedo objects and callbacks
        self.plt = Plotter(qt_widget=self.vtkWidget)
        # self.id1 = self.plt.add_callback("mouse click", self.onMouseClick)
        # self.id2 = self.plt.add_callback("key press",   self.onKeypress)
        # self.plt += Cone().rotate_x(20)
        self.plt.show()                  # <--- show the vedo rendering

        # Set-up the rest of the Qt window
        # button = Qt.QPushButton("My Button makes the cone red")
        # button.setToolTip('This is an example button')
        # button.clicked.connect(self.onClick)
        # self.layout.addWidget(self.vtkWidget)
        # self.layout.addWidget(button)
        # self.frame.setLayout(self.layout)
        # self.setCentralWidget(self.frame)
        self.show()                     # <--- show the Qt Window

        # menu bar
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
        # Create a vtkPoints object and populate it with the point cloud
        vtk_points = vtk.vtkPoints()
        for x, y, z in points:
            vtk_points.InsertNextPoint(x, y, z)

        # Create a vtkPolyData object
        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(vtk_points)

        # Create a vertex glyph filter
        glyph_filter = vtk.vtkVertexGlyphFilter()
        glyph_filter.SetInputData(poly_data)
        glyph_filter.Update()

        # Create a mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(glyph_filter.GetOutputPort())

        # Create an actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetPointSize(2)  # Adjust point size

        # Add the actor to the renderer
        self.renderer.RemoveAllViewProps()  # Clear any existing visualization
        self.renderer.AddActor(actor)
        self.renderer.ResetCamera()

    # def onMouseClick(self, evt):
    #     printc("You have clicked your mouse button. Event info:\n", evt, c='y')

    # def onKeypress(self, evt):
    #     printc("You have pressed key:", evt.keypress, c='b')

    # @Qt.pyqtSlot()
    # def onClick(self):
    #     printc("..calling onClick")
    #     self.plt.objects[0].color('red').rotate_z(40)
    #     self.plt.interactor.Render()

    def onClose(self):
        #Disable the interactor before closing to prevent it
        #from trying to act on already deleted items
        # printc("..calling onClose")
        self.vtkWidget.close()

if __name__ == "__main__":
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    app.aboutToQuit.connect(window.onClose) # <-- connect the onClose event
    app.exec_()
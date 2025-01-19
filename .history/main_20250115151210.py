import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor 
import vedo as vd

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Point Cloud Tool")
        self.setGeometry(100, 100, 1200, 800)

        # VTK Renderer
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.setCentralWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        self.renderer.SetBackground(0.1, 0.1, 0.1)  # Dark background

        # Example sphere to verify VTK
        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(5)
        sphere.SetThetaResolution(32)
        sphere.SetPhiResolution(32)

        sphere_mapper = vtk.vtkPolyDataMapper()
        sphere_mapper.SetInputConnection(sphere.GetOutputPort())

        sphere_actor = vtk.vtkActor()
        sphere_actor.SetMapper(sphere_mapper)

        self.renderer.AddActor(sphere_actor)
        self.renderer.ResetCamera()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

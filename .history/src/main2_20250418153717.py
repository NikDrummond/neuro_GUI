import os
# suppress Qt plugin debug messages
os.environ['QT_DEBUG_PLUGINS'] = '0'
# point to system GObject typelib
os.environ['GI_TYPELIB_PATH'] = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
# ensure system libs are preferred
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH','')
# Graphviz plugin path
os.environ['GV_PLUGIN_PATH'] = '/usr/lib/graphviz'

import sys
import pathlib
import pandas as pd
import numpy as np
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QAction, QWidget, QVBoxLayout, QHBoxLayout, QColorDialog,
    QPushButton, QLabel, QStyle
)
from PySide2.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import vtkPointPicker
import Neurosetta as nr
import vedo as vd
import warnings

warnings.filterwarnings("ignore")

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("Neurosetta Viewer")

        # Main frame and layout
        self.frame = QWidget()
        self.main_layout = QVBoxLayout(self.frame)
        self.setCentralWidget(self.frame)

        # VTK rendering widget and plotter
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.plotter = vd.Plotter(qt_widget=self.vtkWidget, bg="white")

        # Side panel: file info + select toggle
        self.side_panel = QWidget()
        side_layout = QVBoxLayout(self.side_panel)
        side_layout.setContentsMargins(5,5,5,5)
        side_layout.addWidget(QLabel("Current File:"))
        self.filename_label = QLabel("")
        self.filename_label.setStyleSheet("font-weight: bold;")
        side_layout.addWidget(self.filename_label)
        side_layout.addSpacing(10)
        # Select Points toggle
        self.select_btn = QPushButton("Select Points")
        self.select_btn.setCheckable(True)
        self.select_btn.toggled.connect(self.toggle_select_points)
        side_layout.addWidget(self.select_btn)
        side_layout.addStretch(1)
        self.side_panel.setFixedWidth(180)

        # Navigation buttons (icon arrows)
        prev_btn = QPushButton()
        prev_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
        prev_btn.clicked.connect(self.show_previous)
        next_btn = QPushButton()
        next_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        next_btn.clicked.connect(self.show_next)
        # layout for nav buttons under the viewer
        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(prev_btn)
        nav_layout.addStretch(1)
        nav_layout.addWidget(next_btn)

        # Viewer area: vtk + nav buttons in vertical stack
        viewer_area = QWidget()
        va_layout = QVBoxLayout(viewer_area)
        va_layout.setContentsMargins(0, 0, 0, 0)
        va_layout.setSpacing(5)
        va_layout.addWidget(self.vtkWidget)
        va_layout.addWidget(nav_container)

        # Combine viewer area and side panel horizontally
        viewer_container = QWidget()
        vc_layout = QHBoxLayout(viewer_container)
        vc_layout.setContentsMargins(0, 0, 0, 0)
        vc_layout.addWidget(viewer_area, stretch=1)
        vc_layout.addWidget(self.side_panel)

        self.main_layout.addWidget(viewer_container)

        # Set up GTK picker for point selection
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        interactor.SetPicker(self.picker)
        interactor.Initialize()
        interactor.Start()

        # Internal state
        self.files = []
        self.current_index = 0
        self.current_lines = None
        self.current_object = None
        self.vertex_coords = None
        self.selected_points = []
        self.hover_obs = None
        self.click_obs = None

        # Build menus
        self._init_menu_bar()

    def _init_menu_bar(self):
        mb = self.menuBar()
        file_menu = mb.addMenu("File")
        file_menu.addAction(QAction("Load File…", self, triggered=self.read_file))
        file_menu.addAction(QAction("Load Folder…", self, triggered=self.read_folder))
        file_menu.addAction(QAction("Save…", self, triggered=self.save_file))
        file_menu.addAction(QAction("Exit", self, triggered=self.close))
        mb.addMenu("Tools")
        vm = mb.addMenu("Viewer")
        vm.addAction(QAction("Set Neuron Colour…", self, triggered=self.set_neuron_colour))

    def read_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open File", "",
            "CSV (*.csv);;Neurosetta (*.nr);;SWC (*.swc)")
        if fname:
            self.files = [fname]; self.current_index = 0; self.load_current_file()

    def read_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.files = [str(p) for p in pathlib.Path(folder).glob("*")
                if p.suffix.lower() in [".nr", ".swc"]]
            self.current_index = 0
            if self.files: self.load_current_file()

    def load_current_file(self):
        f = self.files[self.current_index]
        self.filename_label.setText(pathlib.Path(f).name)
        try:
            suf = pathlib.Path(f).suffix.lower()
            if suf == ".csv":
                df = pd.read_csv(f)
                if not all(c in df.columns for c in ["x","y","z"]):
                    raise ValueError("CSV must have x,y,z columns")
                pts = df[["x","y","z"]].to_numpy(); self.vertex_coords = pts
                self.render_point_cloud(pts)
            else:
                n = nr.load(f); coords = nr.g_vert_coords(n)
                self.vertex_coords = np.array(coords); self.render_nr(n)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def save_file(self):
        if not self.current_object:
            return QMessageBox.warning(self, "Warning", "Nothing to save.")
        sp, _ = QFileDialog.getSaveFileName(self, "Save As", "", "Neurosetta (*.nr)")
        if sp: nr.save(self.current_object, sp)

    def render_point_cloud(self, pts):
        obj = vd.Points(pts, r=5, c="cyan"); self._display(obj)
    def render_nr(self, n):
        ln = nr.plotting._vd_tree_lines(n, c="red")
        soma = vd.Point(nr.g_vert_coords(n, nr.g_root_ind(n))[0], c="red", r=10)
        self.current_lines = ln; self._display(vd.Assembly([ln, soma]))

    def _display(self, obj):
        self.selected_points.clear(); self.current_object = obj
        self.plotter.clear(); self.plotter.add(obj)
        self.plotter.show(resetcam=True); self.vtkWidget.update()

    def show_previous(self):
        if self.current_index>0:
            self.current_index-=1; self.load_current_file()
    def show_next(self):
        if self.current_index<len(self.files)-1:
            self.current_index+=1; self.load_current_file()

    def set_neuron_colour(self):
        col = QColorDialog.getColor()
        if col.isValid() and self.current_lines:
            self.current_lines.c(col.name()); self.plotter.render()

    def toggle_select_points(self, on):
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        if on:
            self.hover_obs = iren.AddObserver("MouseMoveEvent", self._on_hover)
            self.click_obs = iren.AddObserver("LeftButtonPressEvent", self._on_click)
        else:
            if self.hover_obs: iren.RemoveObserver(self.hover_obs)
            if self.click_obs: iren.RemoveObserver(self.click_obs)

    def _on_hover(self, caller, event):
        x,y=caller.GetEventPosition(); self.picker.Pick(x,y,0,self.plotter.renderer)
        pid=self.picker.GetPointId()
        if pid>=0 and self.vertex_coords is not None:
            coord=self.vertex_coords[pid]; tmp=vd.Point(coord,c="yellow",r=15)
            self.plotter.add(tmp,resetcam=False); self.plotter.render(); self.plotter.remove(tmp)

    def _on_click(self, caller, event):
        x,y=caller.GetEventPosition(); self.picker.Pick(x,y,0,self.plotter.renderer)
        pid=self.picker.GetPointId()
        if pid>=0 and self.vertex_coords is not None:
            coord=self.vertex_coords[pid]; mk=vd.Point(coord,c="blue",r=20)
            self.selected_points.append(mk); self.plotter.add(mk); self.plotter.render()

if __name__=="__main__":
    app=QApplication(sys.argv); win=MainWindow(); win.show(); sys.exit(app.exec_())

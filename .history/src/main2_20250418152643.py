import os
# suppress Qt plugin debug messages
os.environ['QT_DEBUG_PLUGINS'] = '0'
# help GTK+ locate correct typelib
os.environ['GI_TYPELIB_PATH'] = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
# ensure system libs are found before any bundled ones
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH','')
# help Graphviz find its plugin directory
os.environ['GV_PLUGIN_PATH'] = '/usr/lib/graphviz'

import sys
import pathlib
import pandas as pd
import numpy as np
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QAction, QWidget, QVBoxLayout, QHBoxLayout, QColorDialog,
    QPushButton, QDockWidget, QCheckBox, QLabel
)
from PySide2.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import vtkPointPicker
import Neurosetta as nr
import vedo as vd
import warnings

warnings.filterwarnings("ignore")  # suppress non-critical warnings

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("Neurosetta Viewer")

        # Main container and vertical layout
        self.frame = QWidget()
        self.main_layout = QVBoxLayout(self.frame)
        self.setCentralWidget(self.frame)

        # VTK render widget & plotter
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.plotter = vd.Plotter(qt_widget=self.vtkWidget, bg="white")
        self.main_layout.addWidget(self.vtkWidget)

        # Label for current filename (in sidebar)
        self.filename_label = QLabel("")

        # Picker for point selection
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        interactor.SetPicker(self.picker)
        interactor.Initialize()
        interactor.Start()

        # State variables
        self.files = []
        self.current_index = 0
        self.current_lines = None
        self.current_object = None
        self.vertex_coords = None
        self.selected_points = []
        self.hover_obs_id = None
        self.click_obs_id = None

        # Build UI
        self._init_menu_bar()
        self._init_navigation_buttons()
        self._init_sidebar()

    # ------------------- UI Setup -------------------
    def _init_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self._make_action("Load File…", self.read_file))
        file_menu.addAction(self._make_action("Load Folder…", self.read_folder))
        file_menu.addAction(self._make_action("Save…", self.save_file))
        file_menu.addAction(self._make_action("Exit", self.close))
        menu_bar.addMenu("Tools")  # placeholder
        viewer_menu = menu_bar.addMenu("Viewer")
        viewer_menu.addAction(self._make_action("Set Neuron Colour…", self.set_neuron_colour))

    def _make_action(self, name, slot):
        act = QAction(name, self)
        act.triggered.connect(slot)
        return act

    def _init_navigation_buttons(self):
        # Horizontal layout: Previous left, Next right
        prev_btn = QPushButton("Previous")
        prev_btn.clicked.connect(self.show_previous)
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.show_next)
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.addWidget(prev_btn)
        nav_layout.addStretch(1)
        nav_layout.addWidget(next_btn)
        self.main_layout.addWidget(nav_widget)

    def _init_sidebar(self):
        # Dock on the right: file info + select toggle
        dock = QDockWidget("Info & Selection", self)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        # File info section
        layout.addWidget(QLabel("Current File:"))
        layout.addWidget(self.filename_label)
        # Point selection toggle
        self.select_toggle = QCheckBox("Select Points")
        self.select_toggle.stateChanged.connect(self.toggle_select_points)
        layout.addWidget(self.select_toggle)
        widget.setLayout(layout)
        dock.setWidget(widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    # ------------------- File Handling -------------------
    def read_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open File", "",
            "CSV (*.csv);;Neurosetta (*.nr);;SWC (*.swc)"
        )
        if fname:
            self.files = [fname]
            self.current_index = 0
            self.load_current_file()

    def read_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.files = [str(p) for p in pathlib.Path(folder).glob("*")
                          if p.suffix.lower() in [".nr", ".swc"]]
            self.current_index = 0
            if self.files:
                self.load_current_file()

    def load_current_file(self):
        fname = self.files[self.current_index]
        # update sidebar label
        self.filename_label.setText(pathlib.Path(fname).name)
        try:
            suf = pathlib.Path(fname).suffix.lower()
            if suf == ".csv":
                df = pd.read_csv(fname)
                if not all(c in df.columns for c in ["x","y","z"]):
                    raise ValueError("CSV must have x,y,z columns")
                pts = df[["x","y","z"]].to_numpy()
                self.vertex_coords = pts
                self.render_point_cloud(pts)
            else:
                n = nr.load(fname)
                coords = nr.g_vert_coords(n)
                self.vertex_coords = np.array(coords)
                self.render_nr(n)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def save_file(self):
        if not self.current_object:
            QMessageBox.warning(self, "Warning", "Nothing to save.")
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", "Neurosetta (*.nr)"
        )
        if save_path:
            nr.save(self.current_object, save_path)

    # ------------------- Rendering -------------------
    def render_point_cloud(self, points):
        obj = vd.Points(points, r=5, c="cyan")
        self._display_object(obj)

    def render_nr(self, n):
        lns = nr.plotting._vd_tree_lines(n, c="red")
        soma_coords = nr.g_vert_coords(n, nr.g_root_ind(n))[0]
        soma = vd.Point(soma_coords, c="red", r=10)
        self.current_lines = lns
        self._display_object(vd.Assembly([lns, soma]))

    def _display_object(self, obj):
        self.selected_points.clear()
        self.current_object = obj
        self.plotter.clear()
        self.plotter.add(obj)
        self.plotter.show(resetcam=True)
        self.vtkWidget.update()

    # ------------------- Navigation -------------------
    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_file()

    def show_next(self):
        if self.current_index < len(self.files)-1:
            self.current_index += 1
            self.load_current_file()

    # ------------------- Viewer Actions -------------------
    def set_neuron_colour(self):
        col = QColorDialog.getColor()
        if col.isValid() and self.current_lines:
            self.current_lines.c(col.name())
            self.plotter.render()

    # ------------------- Point Selection -------------------
    def toggle_select_points(self, state):
        interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        if state == Qt.Checked:
            self.hover_obs_id = interactor.AddObserver(
                "MouseMoveEvent", self._on_hover)
            self.click_obs_id = interactor.AddObserver(
                "LeftButtonPressEvent", self._on_click)
        else:
            if self.hover_obs_id is not None:
                interactor.RemoveObserver(self.hover_obs_id)
            if self.click_obs_id is not None:
                interactor.RemoveObserver(self.click_obs_id)

    def _on_hover(self, caller, event):
        x, y = caller.GetEventPosition()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pid = self.picker.GetPointId()
        if pid >= 0 and self.vertex_coords is not None:
            coord = self.vertex_coords[pid]
            temp = vd.Point(coord, c="yellow", r=15)
            self.plotter.add(temp, resetcam=False)
            self.plotter.render()
            self.plotter.remove(temp)

    def _on_click(self, caller, event):
        x, y = caller.GetEventPosition()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pid = self.picker.GetPointId()
        if pid >= 0 and self.vertex_coords is not None:
            coord = self.vertex_coords[pid]
            marker = vd.Point(coord, c="blue", r=20)
            self.selected_points.append(marker)
            self.plotter.add(marker)
            self.plotter.render()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
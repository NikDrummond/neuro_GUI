import os
# Suppress Qt plugin debug output
os.environ['QT_DEBUG_PLUGINS'] = '0'

import sys
import pathlib
import pandas as pd
import numpy as np
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QAction, QWidget, QVBoxLayout, QColorDialog, QPushButton,
    QDockWidget, QCheckBox
)
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import vtkPointPicker
import Neurosetta as nr
import vedo as vd
import warnings

warnings.filterwarnings("ignore")  # suppress warnings in output

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("Neurosetta Viewer")

        # Container for main view
        self.frame = QWidget()
        self.main_layout = QVBoxLayout(self.frame)
        self.setCentralWidget(self.frame)

        # VTK rendering widget & Vedo plotter
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.plotter = vd.Plotter(qt_widget=self.vtkWidget, bg="white")
        self.main_layout.addWidget(self.vtkWidget)

        # Picker for selecting points
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        interactor.SetPicker(self.picker)
        interactor.Initialize()
        interactor.Start()

        # State
        self.files = []  # list of .nr/.swc/.csv files
        self.current_index = 0
        self.current_lines = None  # current neuron line object
        self.current_object = None
        self.vertex_coords = None  # numpy array of current vertices
        self.selected_points = []  # markers for permanently selected points
        self.hover_obs_id = None
        self.click_obs_id = None

        # Build UI
        self._init_menu_bar()
        self._init_navigation_buttons()
        self._init_sidebar()

    # ------------------- UI Setup Methods -------------------
    def _init_menu_bar(self):
        menu_bar = self.menuBar()
        # File menu
        file_menu = menu_bar.addMenu("File")
        load_action = QAction("Load File…", self)
        load_action.triggered.connect(self.read_file)
        file_menu.addAction(load_action)

        load_folder_action = QAction("Load Folder…", self)
        load_folder_action.triggered.connect(self.read_folder)
        file_menu.addAction(load_folder_action)

        save_action = QAction("Save…", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu (placeholder)
        tools_menu = menu_bar.addMenu("Tools")

        # Viewer menu
        viewer_menu = menu_bar.addMenu("Viewer")
        color_action = QAction("Set Neuron Colour…", self)
        color_action.triggered.connect(self.set_neuron_colour)
        viewer_menu.addAction(color_action)

    def _init_navigation_buttons(self):
        prev_btn = QPushButton("Previous")
        prev_btn.clicked.connect(self.show_previous)
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.show_next)
        self.main_layout.addWidget(prev_btn)
        self.main_layout.addWidget(next_btn)

    def _init_sidebar(self):
        # Dock widget on right for "Select Points" toggle
        dock = QDockWidget("Selection", self)
        sel_widget = QWidget()
        v = QVBoxLayout(sel_widget)
        self.select_toggle = QCheckBox("Select Points")
        self.select_toggle.stateChanged.connect(self.toggle_select_points)
        v.addWidget(self.select_toggle)
        sel_widget.setLayout(v)
        dock.setWidget(sel_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    # ------------------- File/Folder Handling -------------------
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
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder"
        )
        if folder:
            self.files = [
                str(p) for p in pathlib.Path(folder).glob("*")
                if p.suffix.lower() in [".nr", ".swc"]
            ]
            self.current_index = 0
            if self.files:
                self.load_current_file()

    def load_current_file(self):
        fname = self.files[self.current_index]
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

    # ------------------- Rendering Methods -------------------
    def render_point_cloud(self, points):
        # show CSV points as small cyan spheres
        pts = vd.Points(points, r=5, c="cyan")
        self._display_object(pts)

    def render_nr(self, n):
        # render neuron: lines + soma
        lns = nr.plotting._vd_tree_lines(n, c="red")
        soma_coords = nr.g_vert_coords(n, nr.g_root_ind(n))[0]
        soma = vd.Point(soma_coords, c="red", r=10)
        self.current_lines = lns
        self._display_object(vd.Assembly([lns, soma]))

    def _display_object(self, obj):
        # clear previous selections
        self.selected_points.clear()
        # show object in Vedo plotter
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
        # open color dialog and apply to line object
        col = QColorDialog.getColor()
        if col.isValid() and self.current_lines:
            self.current_lines.c(col.name())
            self.plotter.render()

    # ------------------- Point Selection -------------------
    def toggle_select_points(self, state):
        interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        if state == Qt.Checked:
            # enable hover and click callbacks
            self.hover_obs_id = interactor.AddObserver(
                "MouseMoveEvent", self._on_hover)
            self.click_obs_id = interactor.AddObserver(
                "LeftButtonPressEvent", self._on_click)
        else:
            # disable callbacks
            if self.hover_obs_id is not None:
                interactor.RemoveObserver(self.hover_obs_id)
            if self.click_obs_id is not None:
                interactor.RemoveObserver(self.click_obs_id)

    def _on_hover(self, caller, event):
        # highlight nearest vertex under cursor
        x, y = caller.GetEventPosition()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pid = self.picker.GetPointId()
        if pid >= 0 and self.vertex_coords is not None:
            coord = self.vertex_coords[pid]
            # temporary highlight: small yellow sphere
            temp = vd.Point(coord, c="yellow", r=15)
            self.plotter.add(temp, resetcam=False)
            self.plotter.render()
            # remove temporary after draw
            self.plotter.remove(temp)

    def _on_click(self, caller, event):
        # permanently mark selected vertex
        x, y = caller.GetEventPosition()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pid = self.picker.GetPointId()
        if pid >= 0 and self.vertex_coords is not None:
            coord = self.vertex_coords[pid]
            # create a red sphere marker
            marker = vd.Point(coord, c="blue", r=20)
            self.selected_points.append(marker)
            self.plotter.add(marker)
            self.plotter.render()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

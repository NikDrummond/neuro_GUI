import os
# Suppress Qt plugin debug messages
os.environ['QT_DEBUG_PLUGINS'] = '0'
# Point to system GObject typelib
os.environ['GI_TYPELIB_PATH'] = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
# Ensure system libs are preferred
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
    QPushButton, QLabel
)
from PySide2.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import vtkPointPicker
import vedo as vd
import Neurosetta as nr
import warnings
warnings.filterwarnings("ignore")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neurosetta Viewer")

        # ------- Environment & State -------
        self.files = []
        self.current_index = 0
        self.current_lines = None
        self.current_object = None
        self.vertex_coords = None
        self.selected_points = []
        self.hover_obs = None
        self.click_obs = None

        # units & scale bar settings
        self.units = 'nm'  # 'nm' or 'µm'
        self.scale_length_nm = 1000  # world units
        self.scale_visible = True
        self.scale_bar_elems = []

        # ------- Layout Widgets -------
        main = QWidget()
        main_layout = QVBoxLayout(main)
        self.setCentralWidget(main)

        # VTK & Plotter
        self.vtkWidget = QVTKRenderWindowInteractor(main)
        self.plotter = vd.Plotter(qt_widget=self.vtkWidget, bg='white')

        # Side panel (right)
        self.side_panel = QWidget()
        side_layout = QVBoxLayout(self.side_panel)
        side_layout.setContentsMargins(5,5,5,5)
        side_layout.addWidget(QLabel('Current File:'))
        self.filename_label = QLabel('')
        self.filename_label.setStyleSheet('font-weight: bold;')
        side_layout.addWidget(self.filename_label)
        side_layout.addSpacing(10)
        self.select_btn = QPushButton('Select Points')
        self.select_btn.setCheckable(True)
        self.select_btn.toggled.connect(self.toggle_select_points)
        side_layout.addWidget(self.select_btn)
        side_layout.addStretch(1)
        self.side_panel.setFixedWidth(180)

        # Navigation buttons under viewer
        prev_btn = QPushButton()
        prev_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowLeft))
        prev_btn.clicked.connect(self.show_previous)
        next_btn = QPushButton()
        next_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowRight))
        next_btn.clicked.connect(self.show_next)
        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0,0,0,0)
        nav_layout.addWidget(prev_btn)
        nav_layout.addStretch(1)
        nav_layout.addWidget(next_btn)

        # Viewer container: VTK + nav
        viewer_area = QWidget()
        va_layout = QVBoxLayout(viewer_area)
        va_layout.setContentsMargins(0,0,0,0)
        va_layout.setSpacing(5)
        va_layout.addWidget(self.vtkWidget)
        va_layout.addWidget(nav_container)

        # Combine viewer and side panel
        container = QWidget()
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0,0,0,0)
        c_layout.addWidget(viewer_area, stretch=1)
        c_layout.addWidget(self.side_panel)
        main_layout.addWidget(container)

        # ------- Picker Setup -------
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        iren.SetPicker(self.picker)
        iren.Initialize()
        iren.Start()

        # ------- Menu -------
        self._init_menu()

    def _init_menu(self):
        mb = self.menuBar()
        # File
        fm = mb.addMenu('File')
        fm.addAction('Load File…', triggered=self.read_file)
        fm.addAction('Load Folder…', triggered=self.read_folder)
        fm.addAction('Save…', triggered=self.save_file)
        fm.addAction('Exit', triggered=self.close)
        # Tools placeholder
        mb.addMenu('Tools')
        # Viewer
        vm = mb.addMenu('Viewer')
        # Units submenu
        um = vm.addMenu('Units')
        nm_act = QAction('Nanometers', self, checkable=True, checked=True)
        um_act = QAction('Micrometers', self, checkable=True)
        um.addActions([nm_act, um_act])
        nm_act.triggered.connect(lambda: self.set_units('nm', nm_act, um_act))
        um_act.triggered.connect(lambda: self.set_units('µm', um_act, nm_act))
        # Toggle scale
        self.toggle_scale_act = QAction('Toggle Scale Bar', self, checkable=True, checked=True)
        self.toggle_scale_act.triggered.connect(self.toggle_scale_bar)
        vm.addAction(self.toggle_scale_act)
        # Colour
        vm.addAction('Set Neuron Colour…', triggered=self.set_neuron_colour)

    # ------- File Methods -------
    def read_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'CSV (*.csv);;Neurosetta (*.nr);;SWC (*.swc)')
        if fname:
            self.files = [fname]; self.current_index = 0; self.load_current_file()

    def read_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folder:
            self.files = [str(p) for p in pathlib.Path(folder).glob('*') if p.suffix.lower() in ['.nr','.swc']]
            self.current_index = 0
            if self.files: self.load_current_file()

    def load_current_file(self):
        f = self.files[self.current_index]
        self.filename_label.setText(pathlib.Path(f).name)
        try:
            suf = pathlib.Path(f).suffix.lower()
            if suf == '.csv':
                df = pd.read_csv(f)
                if not all(c in df.columns for c in ['x','y','z']): raise ValueError('CSV must have x,y,z')
                pts = df[['x','y','z']].to_numpy(); self.vertex_coords = pts; self.render_point_cloud(pts)
            else:
                n = nr.load(f); coords=nr.g_vert_coords(n)
                self.vertex_coords = np.array(coords); self.render_nr(n)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load: {e}')

    def save_file(self):
        if not self.current_object:
            return QMessageBox.warning(self, 'Warning', 'Nothing to save.')
        sp, _ = QFileDialog.getSaveFileName(self, 'Save As', '', 'Neurosetta (*.nr)')
        if sp: nr.save(self.current_object, sp)

    # ------- Rendering -------
    def render_point_cloud(self, pts): self._display(vd.Points(pts, r=5, c='cyan'))
    def render_nr(self, n):
        ln = nr.plotting._vd_tree_lines(n, c='red'); soma=vd.Point(nr.g_vert_coords(n,nr.g_root_ind(n))[0], c='red', r=10)
        self.current_lines=ln; self._display(vd.Assembly([ln,soma]))

    def _display(self, obj):
        # Clear old
        self.selected_points.clear(); self.current_object=obj
        self.plotter.clear(); self.plotter.add(obj)
        # Draw scale bar
        if self.scale_visible: self._draw_scale_bar()
        self.plotter.show(resetcam=True); self.vtkWidget.update()

    # ------- Navigation -------
    def show_previous(self):
        if self.current_index>0: self.current_index-=1; self.load_current_file()
    def show_next(self):
        if self.current_index<len(self.files)-1: self.current_index+=1; self.load_current_file()

    # ------- Units & Scale Bar -------
    def set_units(self, unit, this_act, other_act):
        self.units = unit
        this_act.setChecked(True); other_act.setChecked(False)
        # redraw
        self._remove_scale_bar()
        if self.scale_visible: self._draw_scale_bar(); self.plotter.render()

    def toggle_scale_bar(self):
        self.scale_visible = self.toggle_scale_act.isChecked()
        if self.scale_visible: self._draw_scale_bar()
        else: self._remove_scale_bar()
        self.plotter.render()

    def _draw_scale_bar(self):
        self._remove_scale_bar()
        # Define pixel length and position
        px_len = 100
        bar_y = 30
        # Create 2D elements
        line2d = vd.Line2D([20,bar_y],[20+px_len,bar_y], lw=4, c='black')
        txt = f"{self.scale_length_nm if self.units=='nm' else self.scale_length_nm/1000:.0f} {self.units}"
        text2d = vd.Text2D(txt, pos=(20,bar_y+10))
        # Add and store
        for el in (line2d, text2d): self.plotter.add(el)
        self.scale_bar_elems = [line2d, text2d]

    def _remove_scale_bar(self):
        for el in self.scale_bar_elems: self.plotter.remove(el)
        self.scale_bar_elems = []

    # ------- Viewer Actions -------
    def set_neuron_colour(self):
        col = QColorDialog.getColor()
        if col.isValid() and self.current_lines:
            self.current_lines.c(col.name()); self.plotter.render()

    # ------- Point Selection -------
    def toggle_select_points(self, on):
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        if on:
            self.hover_obs = iren.AddObserver('MouseMoveEvent', self._on_hover)
            self.click_obs = iren.AddObserver('LeftButtonPressEvent', self._on_click)
        else:
            if self.hover_obs: iren.RemoveObserver(self.hover_obs)
            if self.click_obs: iren.RemoveObserver(self.click_obs)

    def _on_hover(self, caller, event):
        x,y=caller.GetEventPosition(); self.picker.Pick(x,y,0,self.plotter.renderer)
        pid=self.picker.GetPointId()
        if pid>=0 and self.vertex_coords is not None:
            coord=self.vertex_coords[pid]; tmp=vd.Point(coord,c='yellow',r=15)
            self.plotter.add(tmp,resetcam=False); self.plotter.render(); self.plotter.remove(tmp)

    def _on_click(self, caller, event):
        x,y=caller.GetEventPosition(); self.picker.Pick(x,y,0,self.plotter.renderer)
        pid=self.picker.GetPointId()
        if pid>=0 and self.vertex_coords is not None:
            coord=self.vertex_coords[pid]; mk=vd.Point(coord,c='blue',r=20)
            self.selected_points.append(mk); self.plotter.add(mk); self.plotter.render()

if __name__=='__main__':
    app=QApplication(sys.argv); win=MainWindow(); win.show(); sys.exit(app.exec_())

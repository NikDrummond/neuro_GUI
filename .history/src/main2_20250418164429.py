import os
# suppress Qt plugin debug messages
os.environ['QT_DEBUG_PLUGINS'] = '0'
# GTK typelib path
os.environ['GI_TYPELIB_PATH'] = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
# prefer system libraries
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH','')
# Graphviz plugin path
os.environ['GV_PLUGIN_PATH'] = '/usr/lib/graphviz'

import sys
import pathlib
import pandas as pd
import numpy as np
from PySide2.QtWidgets import (  # added QCheckBox import
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QAction, QFileDialog, QMessageBox, QColorDialog,
    QPushButton, QLabel, QFrame, QInputDialog
)
from PySide2.QtCore import Qt, QEvent
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import vtkPointPicker
import vedo as vd
import Neurosetta as nr
import warnings
warnings.filterwarnings('ignore')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Neurosetta Viewer')

        # State
        self.files = []
        self.current_index = 0
        self.current_lines = None
        self.current_object = None
        self.vertex_coords = None
        self.selected_points = []
        # scale settings
        self.units = 'nm'
        self.scale_length_nm = 5000
        self.scale_visible = False  # start with scale bar hidden

        # Central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        hl_main = QHBoxLayout(central)
        hl_main.setContentsMargins(0,0,0,0)

        # VTK viewer setup
        self.vtkWidget = QVTKRenderWindowInteractor(central)
        self.plotter = vd.Plotter(qt_widget=self.vtkWidget, bg='white')
        # use parallel projection for consistent scale bar
        cam = self.plotter.renderer.GetActiveCamera()
        cam.SetParallelProjection(True)

        # Overlay scale bar widget
        self.scale_widget = QWidget(self.vtkWidget)
        sw_layout = QVBoxLayout(self.scale_widget)
        sw_layout.setContentsMargins(2,2,2,2)
        sw_layout.setSpacing(0)
        self.bar_line = QFrame(self.scale_widget)
        self.bar_line.setFrameShape(QFrame.HLine)
        self.bar_line.setLineWidth(2)
        sw_layout.addWidget(self.bar_line, alignment=Qt.AlignCenter)
        self.scale_label = QLabel(self.scale_widget)
        sw_layout.addWidget(self.scale_label, alignment=Qt.AlignCenter)
        self.scale_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.scale_widget.raise_()
        # ensure scale bar hidden by default
        self.scale_widget.setVisible(self.scale_visible)

        # Navigation buttons overlaid
        self.prev_btn = QPushButton(self.vtkWidget)
        self.prev_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowLeft))
        self.prev_btn.clicked.connect(self.show_previous)
        self.prev_btn.raise_()
        self.next_btn = QPushButton(self.vtkWidget)
        self.next_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowRight))
        self.next_btn.clicked.connect(self.show_next)
        self.next_btn.raise_()

        # Side panel
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(5,5,5,5)
        side_layout.addWidget(QLabel('Current File:'))
        self.filename_label = QLabel('')
        self.filename_label.setStyleSheet('font-weight: bold;')
        side_layout.addWidget(self.filename_label)
        side_layout.addSpacing(10)
        # toggle checkbox for point selection
        self.select_checkbox = QCheckBox('Select Points')
        self.select_checkbox.toggled.connect(self.toggle_select_points)
        side_layout.addWidget(self.select_checkbox)  # replaced QPushButton with QCheckBox
        self.select_btn.setCheckable(True)
        self.select_btn.toggled.connect(self.toggle_select_points)
        side_layout.addWidget(self.select_btn)
        side_layout.addStretch(1)
        side_panel.setFixedWidth(180)

        # Assemble main layout
        hl_main.addWidget(self.vtkWidget, stretch=1)
        hl_main.addWidget(side_panel)

        # Picker for point selection
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        iren.SetPicker(self.picker)
        # update scale on zoom
        iren.AddObserver('MouseWheelForwardEvent', self._update_scale_overlay)
        iren.AddObserver('MouseWheelBackwardEvent', self._update_scale_overlay)
        iren.Initialize()

        # listen for resize to reposition overlays
        self.vtkWidget.installEventFilter(self)

        # Menu setup
        self._init_menu()

        # Initial draw
        self.load_current_file() if self.files else None
        self._update_scale_overlay()
        self._position_overlays()

    def _init_menu(self):
        mb = self.menuBar()
        # File menu
        fm = mb.addMenu('File')
        fm.addAction(QAction('Load File…', self, triggered=self.read_file))
        fm.addAction(QAction('Load Folder…', self, triggered=self.read_folder))
        fm.addAction(QAction('Save…', self, triggered=self.save_file))
        fm.addAction(QAction('Exit', self, triggered=self.close))
        # Tools placeholder
        mb.addMenu('Tools')
        # Viewer menu
        vm = mb.addMenu('Viewer')
        # Units submenu
        um = vm.addMenu('Units')
        self.nm_act = QAction('Nanometers', self, checkable=True, checked=True)
        self.um_act = QAction('Micrometers', self, checkable=True)
        um.addActions([self.nm_act, self.um_act])
        self.nm_act.triggered.connect(lambda: self.set_units('nm'))
        self.um_act.triggered.connect(lambda: self.set_units('µm'))
        # Toggle scale bar
        self.scale_act = QAction('Toggle Scale Bar', self, checkable=True, checked=False)  # default off
        self.scale_act.triggered.connect(lambda: self.scale_widget.setVisible(self.scale_act.isChecked()))
        vm.addAction(self.scale_act)
        # Set scale size
        vm.addAction(QAction('Set Scale Bar Size…', self, triggered=self.set_scale_size))
        # Set neuron colour
        vm.addAction(QAction('Set Neuron Colour…', self, triggered=self.set_neuron_colour))

    def eventFilter(self, obj, event):
        if obj is self.vtkWidget and event.type() == QEvent.Resize:
            self._position_overlays()
        return super().eventFilter(obj, event)

    def _position_overlays(self):
        w = self.vtkWidget.width()
        h = self.vtkWidget.height()
        # center-bottom for scale bar
        sw = self.scale_widget.sizeHint()
        self.scale_widget.move((w - sw.width()) // 2, h - sw.height() - 10)
        # nav buttons
        pb = self.prev_btn.sizeHint()
        self.prev_btn.move(10, h - pb.height() - 10)
        nb = self.next_btn.sizeHint()
        self.next_btn.move(w - nb.width() - 10, h - nb.height() - 10)

    def _update_scale_overlay(self, *args):
        ren = self.plotter.renderer
        cam = ren.GetActiveCamera()
        fp = cam.GetFocalPoint()
        # world points separated along X by scale_length_nm
        p1 = (*fp, 1);
        p2 = (fp[0] + self.scale_length_nm, fp[1], fp[2], 1)
        ren.SetWorldPoint(*p1); ren.WorldToDisplay(); d1 = ren.GetDisplayPoint()
        ren.SetWorldPoint(*p2); ren.WorldToDisplay(); d2 = ren.GetDisplayPoint()
        px = abs(d2[0] - d1[0])
        self.bar_line.setFixedWidth(max(1, int(px)))
        val = int(self.scale_length_nm if self.units == 'nm' else self.scale_length_nm / 1000)
        self.scale_label.setText(f'{val} {self.units}')
        self._position_overlays()

    # File I/O
    def read_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open File', '',
            'CSV (*.csv);;Neurosetta (*.nr);;SWC (*.swc)')
        if fname:
            self.files = [fname]; self.current_index = 0; self.load_current_file()

    def read_folder(self):
        fld = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if fld:
            self.files = [str(p) for p in pathlib.Path(fld).glob('*') if p.suffix.lower() in ['.nr','.swc']]
            self.current_index = 0
            if self.files: self.load_current_file()

    def load_current_file(self):
        if not self.files:
            return
        f = self.files[self.current_index]
        self.filename_label.setText(pathlib.Path(f).name)
        try:
            suf = pathlib.Path(f).suffix.lower()
            if suf == '.csv':
                df = pd.read_csv(f)
                if not all(c in df.columns for c in ['x','y','z']): raise ValueError('CSV must have x,y,z')
                pts = df[['x','y','z']].to_numpy(); self.vertex_coords = pts; self.render_point_cloud(pts)
            else:
                n = nr.load(f); coords = nr.g_vert_coords(n)
                self.vertex_coords = np.array(coords); self.render_nr(n)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load: {e}')

    def save_file(self):
        if not self.current_object:
            QMessageBox.warning(self, 'Warning', 'Nothing to save.'); return
        sp, _ = QFileDialog.getSaveFileName(self, 'Save As', '', 'Neurosetta (*.nr)')
        if sp: nr.save(self.current_object, sp)

    # Rendering
    def render_point_cloud(self, pts):
        self._display(vd.Points(pts, r=5, c='cyan'))

    def render_nr(self, n):
        ln = nr.plotting._vd_tree_lines(n, c='red')
        soma = vd.Point(nr.g_vert_coords(n, nr.g_root_ind(n))[0], c='red', r=10)
        self.current_lines = ln
        self._display(vd.Assembly([ln, soma]))

    def _display(self, obj):
        self.selected_points.clear(); self.current_object = obj
        self.plotter.clear(); self.plotter.add(obj)
        self.plotter.show(resetcam=True); self.vtkWidget.update()
        self._update_scale_overlay()

    # Navigation
    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1; self.load_current_file()

    def show_next(self):
        if self.current_index < len(self.files) - 1:
            self.current_index += 1; self.load_current_file()

    # Units & scale size
    def set_units(self, unit):
        self.units = unit
        self.nm_act.setChecked(unit == 'nm')
        self.um_act.setChecked(unit == 'µm')
        self._update_scale_overlay()

    def set_scale_size(self):
        default = int(self.scale_length_nm if self.units == 'nm' else self.scale_length_nm / 1000)
        val, ok = QInputDialog.getInt(self, 'Scale Bar Size', f'Enter size in {self.units}:', default, 1)
        if ok:
            self.scale_length_nm = val if self.units == 'nm' else val * 1000
            self._update_scale_overlay()

    # Viewer actions
    def set_neuron_colour(self):
        col = QColorDialog.getColor()
        if col.isValid() and self.current_lines:
            self.current_lines.c(col.name()); self.plotter.render()

    # Point selection
    def toggle_select_points(self, on):
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        if on:
            self.hover_obs = iren.AddObserver('MouseMoveEvent', self._on_hover)
            self.click_obs = iren.AddObserver('LeftButtonPressEvent', self._on_click)
        else:
            if hasattr(self, 'hover_obs'): iren.RemoveObserver(self.hover_obs)
            if hasattr(self, 'click_obs'): iren.RemoveObserver(self.click_obs)

    def _on_hover(self, caller, event):
        # highlight nearest vertex under cursor with bounds checking
        x, y = caller.GetEventPosition()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pid = self.picker.GetPointId()
        # guard out-of-bounds
        if pid < 0 or self.vertex_coords is None or pid >= len(self.vertex_coords):
            return
        coord = self.vertex_coords[pid]
        # temporary highlight
        tmp = vd.Point(coord, c='yellow', r=15)
        self.plotter.add(tmp)
        self.plotter.render()
        self.plotter.remove(tmp)(self, caller, event):
        x, y = caller.GetEventPosition()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pid = self.picker.GetPointId()
        if pid >= 0 and self.vertex_coords is not None:
            coord = self.vertex_coords[pid]
            tmp = vd.Point(coord, c='yellow', r=15)
            self.plotter.add(tmp, resetcam=False); self.plotter.render(); self.plotter.remove(tmp)

    def _on_click(self, caller, event):
        # permanently mark selected vertex under cursor
        x, y = caller.GetEventPosition()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pid = self.picker.GetPointId()
        if pid < 0 or self.vertex_coords is None or pid >= len(self.vertex_coords):
            return
        coord = self.vertex_coords[pid]
        marker = vd.Point(coord, c='blue', r=20)
        self.selected_points.append(marker)
        self.plotter.add(marker)
        self.plotter.render()(self, caller, event):
        x, y = caller.GetEventPosition()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pid = self.picker.GetPointId()
        if pid >= 0 and self.vertex_coords is not None:
            coord = self.vertex_coords[pid]
            mk = vd.Point(coord, c='blue', r=20)
            self.selected_points.append(mk)
            self.plotter.add(mk); self.plotter.render()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

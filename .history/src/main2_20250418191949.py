import os
# Suppress Qt plugin debug messages
os.environ['QT_DEBUG_PLUGINS'] = '0'
# GTK+ typelib path
os.environ['GI_TYPELIB_PATH'] = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
# Prefer system libraries
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH', '')
# Graphviz plugin path
os.environ['GV_PLUGIN_PATH'] = '/usr/lib/graphviz'

import sys
import pathlib
import pandas as pd
import numpy as np
import warnings
import logging

from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QAction, QFileDialog, QMessageBox, QColorDialog,
    QPushButton, QCheckBox, QLabel, QFrame, QInputDialog,
    QTextEdit, QDockWidget
)
from PySide2.QtCore import Qt, QEvent, QMetaObject
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import vtkPointPicker
import vedo as vd
import Neurosetta as nr

warnings.filterwarnings('ignore')

### Helper functions for point selection ###
def n_pnt_coords(N):
    # get lead & branch points
    return nr.g_vert_coords(N)[nr.g_lb_inds(N)]

def make_pnts(coords, mask):
    in_pnts  = vd.Points(coords[mask],  c='b', r=8)
    out_pnts = vd.Points(coords[~mask], c='r', r=8)
    return in_pnts, out_pnts

### Logging handler to embed in QTextEdit ###
class QTextEditLogger(logging.Handler):
    """A logging handler that sends output to a QTextEdit."""
    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.widget = text_edit
        fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s',
                                datefmt='%H:%M:%S')
        self.setFormatter(fmt)
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.widget.append(msg)
            sb = self.widget.verticalScrollBar()
            sb.setValue(sb.maximum())
        QMetaObject.invokeMethod(self.widget, append, Qt.QueuedConnection)

### Main application window ###
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Neurosetta Viewer')

        # --- State ---
        self.files = []
        self.current_index = 0
        self.current_lines = None
        self.current_object = None
        self.current_neuron = None
        self.vertex_coords = None
        # Point selection state
        self.pnt_coords = None
        self.pnt_mask = None
        self.pnt_in = None
        self.pnt_out = None
        self.hover_marker = None
        # Scale bar settings
        self.units = 'nm'
        self.scale_length_nm = 5000
        self.scale_visible = False  # hidden by default

        # --- Central Layout ---
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)

        # --- VTK Viewer ---
        self.vtkWidget = QVTKRenderWindowInteractor(central)
        self.plotter = vd.Plotter(qt_widget=self.vtkWidget, bg='white')
        cam = self.plotter.renderer.GetActiveCamera()
        cam.SetParallelProjection(True)

        # overlay: scale bar
        self.scale_widget = QWidget(self.vtkWidget)
        sw_layout = QVBoxLayout(self.scale_widget)
        sw_layout.setContentsMargins(2,2,2,2)
        sw_layout.setSpacing(2)
        self.bar_line = QFrame(self.scale_widget)
        self.bar_line.setFrameShape(QFrame.HLine)
        self.bar_line.setLineWidth(2)
        sw_layout.addWidget(self.bar_line, alignment=Qt.AlignCenter)
        self.scale_label = QLabel(self.scale_widget)
        sw_layout.addWidget(self.scale_label, alignment=Qt.AlignCenter)
        self.scale_widget.setVisible(self.scale_visible)
        self.scale_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.scale_widget.raise_()

        # navigation buttons
        self.prev_btn = QPushButton(self.vtkWidget)
        self.prev_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowLeft))
        self.prev_btn.clicked.connect(self.show_previous)
        self.prev_btn.raise_()
        self.next_btn = QPushButton(self.vtkWidget)
        self.next_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowRight))
        self.next_btn.clicked.connect(self.show_next)
        self.next_btn.raise_()

        # --- Side Panel ---
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(5,5,5,5)
        side_layout.addWidget(QLabel('Current File:'))
        self.filename_label = QLabel('')
        self.filename_label.setStyleSheet('font-weight: bold;')
        side_layout.addWidget(self.filename_label)
        side_layout.addSpacing(10)
        self.select_checkbox = QCheckBox('Select Points')
        self.select_checkbox.toggled.connect(self.toggle_select_points)
        side_layout.addWidget(self.select_checkbox)
        side_layout.addStretch(1)
        side_panel.setFixedWidth(180)

        # assemble central layout
        main_layout.addWidget(self.vtkWidget, stretch=1)
        main_layout.addWidget(side_panel)

        # --- Picker & Interactor ---
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        iren.SetPicker(self.picker)
        iren.AddObserver('MouseWheelForwardEvent', self._update_scale_overlay)
        iren.AddObserver('MouseWheelBackwardEvent', self._update_scale_overlay)
        iren.Initialize()
        self.vtkWidget.installEventFilter(self)

        # --- Menu & Logging Dock ---
        self._init_menu()

        # initial positioning
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

        # Tools menu → Show Log
        tools_menu = mb.addMenu('Tools')
        self.log_dock = QDockWidget("Console Log", self)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.log_console = QTextEdit(self)
        self.log_console.setReadOnly(True)
        self.log_dock.setWidget(self.log_console)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.log_dock.hide()
        show_log_act = QAction("Show Log", self, checkable=True)
        show_log_act.toggled.connect(self._toggle_log_dock)
        tools_menu.addAction(show_log_act)
        qt_logger = QTextEditLogger(self.log_console)
        logging.getLogger().addHandler(qt_logger)
        logging.getLogger().setLevel(logging.DEBUG)

        # Viewer menu
        vm = mb.addMenu('Viewer')
        # Units submenu
        um = vm.addMenu('Units')
        self.nm_act = QAction('Nanometers', self, checkable=True, checked=True)
        self.um_act = QAction('Micrometers', self, checkable=True)
        um.addActions([self.nm_act, self.um_act])
        self.nm_act.triggered.connect(lambda: self.set_units('nm'))
        self.um_act.triggered.connect(lambda: self.set_units('µm'))
        # Scale toggle & size
        self.scale_act = QAction('Toggle Scale Bar', self, checkable=True, checked=False)
        self.scale_act.triggered.connect(lambda v: self.scale_widget.setVisible(v))
        vm.addAction(self.scale_act)
        vm.addAction(QAction('Set Scale Bar Size…', self, triggered=self.set_scale_size))
        # Neuron colour
        vm.addAction(QAction('Set Neuron Colour…', self, triggered=self.set_neuron_colour))

    def _toggle_log_dock(self, visible: bool):
        if visible:
            self.log_dock.show()
        else:
            self.log_dock.hide()

    def eventFilter(self, obj, event):
        if obj is self.vtkWidget and event.type() == QEvent.Resize:
            self._position_overlays()
        return super().eventFilter(obj, event)

    def _position_overlays(self):
        w, h = self.vtkWidget.width(), self.vtkWidget.height()
        sw = self.scale_widget.sizeHint()
        self.scale_widget.move((w - sw.width()) // 2, h - sw.height() - 10)
        pb = self.prev_btn.sizeHint()
        self.prev_btn.move(10, h - pb.height() - 10)
        nb = self.next_btn.sizeHint()
        self.next_btn.move(w - nb.width() - 10, h - nb.height() - 10)

    def _update_scale_overlay(self, *args):
        ren = self.plotter.renderer
        cam = ren.GetActiveCamera()
        fp = cam.GetFocalPoint()
        p1 = (*fp, 1); p2 = (fp[0] + self.scale_length_nm, fp[1], fp[2], 1)
        ren.SetWorldPoint(*p1); ren.WorldToDisplay(); d1 = ren.GetDisplayPoint()
        ren.SetWorldPoint(*p2); ren.WorldToDisplay(); d2 = ren.GetDisplayPoint()
        px = abs(d2[0] - d1[0])
        self.bar_line.setFixedWidth(max(1, int(px)))
        val = int(self.scale_length_nm if self.units == 'nm' else self.scale_length_nm / 1000)
        self.scale_label.setText(f'{val} {self.units}')
        self._position_overlays()

    # --- File I/O ---
    def read_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open File', '',
            'CSV (*.csv);;Neurosetta (*.nr);;SWC (*.swc)')
        if fname:
            self.files = [fname]; self.current_index = 0; self.load_current_file()

    def read_folder(self):
        fld = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if fld:
            self.files = [str(p) for p in pathlib.Path(fld).glob('*')
                          if p.suffix.lower() in ['.nr','.swc']]
            self.current_index = 0
            if self.files:
                self.load_current_file()

    def load_current_file(self):
        f = self.files[self.current_index]
        self.filename_label.setText(pathlib.Path(f).name)
        try:
            if f.lower().endswith('.csv'):
                df = pd.read_csv(f)
                if not all(c in df.columns for c in ['x','y','z']):
                    raise ValueError('CSV must have x,y,z')
                pts = df[['x','y','z']].to_numpy()
                self.vertex_coords = pts
                self.render_point_cloud(pts)
            else:
                n = nr.load(f)
                self.current_neuron = n
                coords = nr.g_vert_coords(n)
                self.vertex_coords = np.array(coords)
                self.render_nr(n)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load: {e}')

    def save_file(self):
        if not self.current_object:
            QMessageBox.warning(self, 'Warning', 'Nothing to save.')
            return
        sp, _ = QFileDialog.getSaveFileName(self, 'Save As', '', 'Neurosetta (*.nr)')
        if sp:
            nr.save(self.current_object, sp)

    # --- Rendering ---
    def render_point_cloud(self, pts):
        self._display(vd.Points(pts, r=5, c='cyan'))

    def render_nr(self, n):
        ln = nr.plotting._vd_tree_lines(n, c='red')
        soma = vd.Point(nr.g_vert_coords(n, nr.g_root_ind(n))[0], c='red', r=10)
        self.current_lines = ln
        self.soma = soma
        self._display(vd.Assembly([ln, soma]))

    def _display(self, obj):
        self.current_object = obj
        # clear any old selection overlays
        for attr in ('pnt_in','pnt_out','hover_marker'):
            if hasattr(self, attr):
                self.plotter.remove(getattr(self, attr))
        self.plotter.clear(); self.plotter.add(obj)
        self.plotter.show(resetcam=True)
        self.vtkWidget.update()
        self._update_scale_overlay()

    # --- Navigation ---
    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_file()

    def show_next(self):
        if self.current_index < len(self.files) - 1:
            self.current_index += 1
            self.load_current_file()

    # --- Units & Scale Size ---
    def set_units(self, unit):
        self.units = unit
        self.nm_act.setChecked(unit == 'nm')
        self.um_act.setChecked(unit == 'µm')
        self._update_scale_overlay()

    def set_scale_size(self):
        default = int(self.scale_length_nm if self.units == 'nm'
                      else self.scale_length_nm / 1000)
        val, ok = QInputDialog.getInt(self, 'Scale Bar Size',
                                      f'Enter size in {self.units}:', default, 1)
        if ok:
            self.scale_length_nm = val if self.units == 'nm' else val * 1000
            self._update_scale_overlay()

    # --- Viewer Color ---
    def set_neuron_colour(self):
        col = QColorDialog.getColor()
        if col.isValid() and self.current_lines:
            self.current_lines.c(col.name())
            self.soma.c(col.name())
            self.plotter.render()

    # --- Point Selection ---
    def toggle_select_points(self, on):
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        if on:
            if self.pnt_mask is None:
                self._init_point_selection()
            else:
                self._update_point_overlays()
            self.vtkWidget.installEventFilter(self)
        else:
            self.vtkWidget.removeEventFilter(self)
            for attr in ('pnt_in','pnt_out','hover_marker'):
                if hasattr(self, attr):
                    self.plotter.remove(getattr(self, attr))
            self.plotter.render()

    def _init_point_selection(self):
        self.pnt_coords = n_pnt_coords(self.current_neuron)
        self.pnt_mask   = np.zeros(len(self.pnt_coords), dtype=bool)
        self.pnt_in, self.pnt_out = make_pnts(self.pnt_coords, self.pnt_mask)
        self.plotter.add(self.pnt_out).add(self.pnt_in)
        self.hover_marker = vd.Point([0,0,0], c='yellow', r=15, alpha=0.6)
        self.plotter.add(self.hover_marker)
        self.plotter.render()

    def _update_point_overlays(self):
        if hasattr(self, 'pnt_in'):
            self.plotter.remove(self.pnt_in)
        if hasattr(self, 'pnt_out'):
            self.plotter.remove(self.pnt_out)
        self.pnt_in, self.pnt_out = make_pnts(self.pnt_coords, self.pnt_mask)
        self.plotter.add(self.pnt_out).add(self.pnt_in)
        self.plotter.render()

    def eventFilter(self, obj, event):
        if obj is self.vtkWidget:
            if event.type() == QEvent.MouseMove:
                self._on_hover(event)
                return False
            if (event.type() == QEvent.MouseButtonPress and
                event.modifiers() & Qt.ShiftModifier):
                self._on_shift_click(event)
                return True
            if event.type() == QEvent.Resize:
                self._position_overlays()
                return False
        return super().eventFilter(obj, event)

    def _on_hover(self, event):
        x = event.x()
        y = self.vtkWidget.height() - event.y()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pick_pos = self.picker.GetPickPosition()
        dists = np.linalg.norm(self.pnt_coords - pick_pos, axis=1)
        idx = dists.argmin()
        if dists[idx] > 20:
            self.hover_marker.alpha(0)
        else:
            self.hover_marker.pos(self.pnt_coords[idx])
            self.hover_marker.alpha(0.6)
        self.plotter.render()

    def _on_shift_click(self, event):
        x = event.x()
        y = self.vtkWidget.height() - event.y()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pick_pos = self.picker.GetPickPosition()
        dists = np.linalg.norm(self.pnt_coords - pick_pos, axis=1)
        idx = dists.argmin()
        if dists[idx] > 20:
            return
        self.pnt_mask[idx] = not self.pnt_mask[idx]
        self.plotter.remove(self.pnt_in)
        self.plotter.remove(self.pnt_out)
        self.pnt_in, self.pnt_out = make_pnts(self.pnt_coords, self.pnt_mask)
        self.plotter.add(self.pnt_out).add(self.pnt_in)
        self.plotter.render()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

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
from PySide2.QtCore import Qt, QEvent, QTimer
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import vtkPointPicker
import vedo as vd
import Neurosetta as nr

warnings.filterwarnings('ignore')

### Helper functions for point selection ###
def n_pnt_coords(N):
    return nr.g_vert_coords(N)[nr.g_lb_inds(N)]

def make_pnts(coords, mask):
    in_pnts  = vd.Points(coords[mask],  c='b', r=8)
    out_pnts = vd.Points(coords[~mask], c='r', r=8)
    return in_pnts, out_pnts

### Logging handler for embedded console ###
class QTextEditLogger(logging.Handler):
    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.widget = text_edit
        fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s',
                                datefmt='%H:%M:%S')
        self.setFormatter(fmt)
    def emit(self, record):
        msg = self.format(record)
        # queue append on GUI thread
        def append():
            self.widget.append(msg)
            sb = self.widget.verticalScrollBar()
            sb.setValue(sb.maximum())
        QTimer.singleShot(0, append)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Neurosetta Viewer')

        # State
        self.files = []
        self.current_index = 0
        self.current_lines = None
        self.current_object = None
        self.current_neuron = None
        self.pnt_coords = None
        self.pnt_mask = None
        self.pnt_in = None
        self.pnt_out = None
        self.hover_marker = None
        self.units = 'nm'
        self.scale_length_nm = 5000
        self.scale_visible = False

        # Central UI
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)

        # VTK viewer
        self.vtkWidget = QVTKRenderWindowInteractor(central)
        self.plotter = vd.Plotter(qt_widget=self.vtkWidget, bg='white')
        cam = self.plotter.renderer.GetActiveCamera()
        cam.SetParallelProjection(True)

        # Scale overlay
        self.scale_widget = QWidget(self.vtkWidget)
        sw_layout = QVBoxLayout(self.scale_widget)
        sw_layout.setContentsMargins(2,2,2,2)
        self.bar_line = QFrame(self.scale_widget)
        self.bar_line.setFrameShape(QFrame.HLine)
        self.bar_line.setLineWidth(2)
        sw_layout.addWidget(self.bar_line, alignment=Qt.AlignCenter)
        self.scale_label = QLabel(self.scale_widget)
        sw_layout.addWidget(self.scale_label, alignment=Qt.AlignCenter)
        self.scale_widget.setVisible(self.scale_visible)
        self.scale_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.scale_widget.raise_()

        # Navigation buttons
        self.prev_btn = QPushButton(self.vtkWidget)
        self.prev_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowLeft))
        self.prev_btn.clicked.connect(self.show_previous)
        self.prev_btn.raise_()
        self.next_btn = QPushButton(self.vtkWidget)
        self.next_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowRight))
        self.next_btn.clicked.connect(self.show_next)
        self.next_btn.raise_()

        # Side panel
        side = QWidget()
        side_layout = QVBoxLayout(side)
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
        side.setFixedWidth(180)

        main_layout.addWidget(self.vtkWidget, stretch=1)
        main_layout.addWidget(side)

        # Picker & interactor
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        iren.SetPicker(self.picker)
        iren.AddObserver('MouseWheelForwardEvent', self._update_scale_overlay)
        iren.AddObserver('MouseWheelBackwardEvent', self._update_scale_overlay)
        iren.Initialize()
        self.vtkWidget.installEventFilter(self)

        # Menus + log dock
        self._init_menu()

        # Initial positioning
        self._update_scale_overlay()
        self._position_overlays()

    def _init_menu(self):
        mb = self.menuBar()
        # File
        fm = mb.addMenu('File')
        fm.addAction(QAction('Load File…', self, triggered=self.read_file))
        fm.addAction(QAction('Load Folder…', self, triggered=self.read_folder))
        fm.addAction(QAction('Save…', self, triggered=self.save_file))
        fm.addAction(QAction('Exit', self, triggered=self.close))
        # Tools & log
        tools = mb.addMenu('Tools')
        self.log_dock = QDockWidget("Console Log", self)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.log_console = QTextEdit(self)
        self.log_console.setReadOnly(True)
        self.log_dock.setWidget(self.log_console)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.log_dock.hide()
        show_log = QAction("Show Log", self, checkable=True)
        show_log.toggled.connect(self._toggle_log_dock)
        tools.addAction(show_log)
        qt_logger = QTextEditLogger(self.log_console)
        logging.getLogger().addHandler(qt_logger)
        logging.getLogger().setLevel(logging.DEBUG)
        # Viewer
        vm = mb.addMenu('Viewer')
        # Units
        um = vm.addMenu('Units')
        self.nm_act = QAction('Nanometers', self, checkable=True, checked=True)
        self.um_act = QAction('Micrometers', self, checkable=True)
        um.addActions([self.nm_act, self.um_act])
        self.nm_act.triggered.connect(lambda: self.set_units('nm'))
        self.um_act.triggered.connect(lambda: self.set_units('µm'))
        # Scale
        self.scale_act = QAction('Toggle Scale Bar', self, checkable=True, checked=False)
        self.scale_act.triggered.connect(lambda v: self.scale_widget.setVisible(v))
        vm.addAction(self.scale_act)
        vm.addAction(QAction('Set Scale Bar Size…', self, triggered=self.set_scale_size))
        # Colour
        vm.addAction(QAction('Set Neuron Colour…', self, triggered=self.set_neuron_colour))

    def _toggle_log_dock(self, vis):
        if vis: self.log_dock.show()
        else:   self.log_dock.hide()

    def eventFilter(self, obj, event):
        if obj is self.vtkWidget:
            if event.type() == QEvent.Resize:
                self._position_overlays()
            # hover: guard until coords exist
            if event.type() == QEvent.MouseMove and self.pnt_coords is not None:
                self._on_hover(event)
                return False
            # shift-click for selection
            if (event.type() == QEvent.MouseButtonPress and
                event.modifiers() & Qt.ShiftModifier and
                self.pnt_coords is not None):
                self._on_shift_click(event)
                return True
        return super().eventFilter(obj, event)

    def _position_overlays(self):
        w, h = self.vtkWidget.width(), self.vtkWidget.height()
        sw = self.scale_widget.sizeHint()
        self.scale_widget.move((w-sw.width())//2, h-sw.height()-10)
        pb = self.prev_btn.sizeHint()
        nb = self.next_btn.sizeHint()
        self.prev_btn.move(10, h-pb.height()-10)
        self.next_btn.move(w-nb.width()-10, h-nb.height()-10)

    def _update_scale_overlay(self, *a):
        ren = self.plotter.renderer; cam = ren.GetActiveCamera()
        fp = cam.GetFocalPoint()
        p1 = (*fp,1); p2 = (fp[0]+self.scale_length_nm, fp[1], fp[2],1)
        ren.SetWorldPoint(*p1); ren.WorldToDisplay(); d1=ren.GetDisplayPoint()
        ren.SetWorldPoint(*p2); ren.WorldToDisplay(); d2=ren.GetDisplayPoint()
        px = abs(d2[0]-d1[0])
        self.bar_line.setFixedWidth(max(1,int(px)))
        val = (self.scale_length_nm if self.units=='nm'
               else self.scale_length_nm//1000)
        self.scale_label.setText(f'{val} {self.units}')
        self._position_overlays()

    # File I/O, rendering, navigation, units, colour omitted for brevity...
    # They remain as in prior code.

    def _on_hover(self, event):
        x = event.x(); y = self.vtkWidget.height() - event.y()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pick_pos = np.array(self.picker.GetPickPosition())
        dists = np.linalg.norm(self.pnt_coords - pick_pos, axis=1)
        idx = dists.argmin()
        if dists[idx] > 20:
            self.hover_marker.alpha(0)
        else:
            self.hover_marker.pos(self.pnt_coords[idx])
            self.hover_marker.alpha(0.6)
        self.plotter.render()

    def _on_shift_click(self, event):
        x = event.x(); y = self.vtkWidget.height() - event.y()
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        pick_pos = np.array(self.picker.GetPickPosition())
        dists = np.linalg.norm(self.pnt_coords - pick_pos, axis=1)
        idx = dists.argmin()
        if dists[idx] <= 20:
            self.pnt_mask[idx] = not self.pnt_mask[idx]
            self.plotter.remove(self.pnt_in); self.plotter.remove(self.pnt_out)
            self.pnt_in, self.pnt_out = make_pnts(self.pnt_coords, self.pnt_mask)
            self.plotter.add(self.pnt_out).add(self.pnt_in)
            self.plotter.render()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

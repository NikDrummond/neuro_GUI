import os
# Suppress Qt plugin debug messages
os.environ['QT_DEBUG_PLUGINS'] = '0'
# GTK typelib path
ios.environ['GI_TYPELIB_PATH'] = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
# prefer system libraries
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH','')
# Graphviz plugin path
os.environ['GV_PLUGIN_PATH'] = '/usr/lib/graphviz'

import sys
import pathlib
import pandas as pd
import numpy as np
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QAction,
    QFileDialog, QMessageBox, QColorDialog, QPushButton, QLabel,
    QFrame, QInputDialog
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
        self.scale_visible = True

        # Central widget and layout
        central = QWidget()
        central.setContentsMargins(0,0,0,0)
        self.setCentralWidget(central)
        hl = QHBoxLayout(central)
        hl.setContentsMargins(0,0,0,0)

        # VTK viewer
        self.vtkWidget = QVTKRenderWindowInteractor(central)
        self.plotter = vd.Plotter(qt_widget=self.vtkWidget, bg='white')
        # parallel projection for consistent scale
        cam = self.plotter.renderer.GetActiveCamera()
        cam.SetParallelProjection(True)

        # Overlay widgets parented to VTK
        self.scale_widget = QWidget(self.vtkWidget)
        swl = QHBoxLayout(self.scale_widget)
        swl.setContentsMargins(2,2,2,2)
        self.bar_line = QFrame(self.scale_widget)
        self.bar_line.setFrameShape(QFrame.HLine)
        self.bar_line.setLineWidth(2)
        swl.addWidget(self.bar_line)
        self.scale_label = QLabel(self.scale_widget)
        swl.addWidget(self.scale_label)
        self.scale_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.scale_widget.raise_()

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
        sl = QHBoxLayout(side)
        sl.setContentsMargins(5,5,5,5)
        # Actually use QVBoxLayout inside, omitted for brevity
        sl = QHBoxLayout(side)
        # ... existing file info and select points buttons here ...

        hl.addWidget(self.vtkWidget, stretch=1)
        hl.addWidget(side)

        # Picker
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        iren.SetPicker(self.picker)
        # zoom events
        iren.AddObserver('MouseWheelForwardEvent', self._update_scale_overlay)
        iren.AddObserver('MouseWheelBackwardEvent', self._update_scale_overlay)
        iren.Initialize()
        self.vtkWidget.installEventFilter(self)

        # Menu
        self._init_menu()

        # Initial placement and draw
        self._update_scale_overlay()
        self._position_overlays()

    def _init_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu('File')
        fm.addAction(QAction('Load File…', self, triggered=self.read_file))
        fm.addAction(QAction('Load Folder…', self, triggered=self.read_folder))
        fm.addAction(QAction('Save…', self, triggered=self.save_file))
        fm.addAction(QAction('Exit', self, triggered=self.close))
        mb.addMenu('Tools')
        vm = mb.addMenu('Viewer')
        um = vm.addMenu('Units')
        self.nm_act = QAction('Nanometers', self, checkable=True, checked=True)
        self.um_act = QAction('Micrometers', self, checkable=True)
        um.addActions([self.nm_act, self.um_act])
        self.nm_act.triggered.connect(lambda: self.set_units('nm'))
        self.um_act.triggered.connect(lambda: self.set_units('µm'))
        self.scale_act = QAction('Toggle Scale Bar', self, checkable=True, checked=True)
        self.scale_act.triggered.connect(lambda: self.scale_widget.setVisible(self.scale_act.isChecked()))
        vm.addAction(self.scale_act)
        vm.addAction(QAction('Set Scale Bar Size…', self, triggered=self.set_scale_size))
        vm.addAction(QAction('Set Neuron Colour…', self, triggered=self.set_neuron_colour))

    def eventFilter(self, obj, event):
        if obj is self.vtkWidget and event.type() == QEvent.Resize:
            self._position_overlays()
        return super().eventFilter(obj, event)

    def _position_overlays(self):
        w, h = self.vtkWidget.size().width(), self.vtkWidget.size().height()
        sw = self.scale_widget.sizeHint()
        # center bottom
        self.scale_widget.move((w-sw.width())//2, h - sw.height() - 10)
        pb = self.prev_btn.sizeHint()
        self.prev_btn.move(10, h - pb.height() - 10)
        nb = self.next_btn.sizeHint()
        self.next_btn.move(w - nb.width() - 10, h - nb.height() - 10)

    def _update_scale_overlay(self, *args):
        ren = self.plotter.renderer
        cam = ren.GetActiveCamera()
        # focal plane
        fp = cam.GetFocalPoint()
        # two world pts separated in X by scale_length_nm
        p1 = (*fp, 1); p2 = (fp[0] + self.scale_length_nm, fp[1], fp[2], 1)
        ren.SetWorldPoint(*p1); ren.WorldToDisplay(); d1 = ren.GetDisplayPoint()
        ren.SetWorldPoint(*p2); ren.WorldToDisplay(); d2 = ren.GetDisplayPoint()
        px = abs(d2[0] - d1[0])
        self.bar_line.setFixedWidth(max(1, int(px)))
        val = int(self.scale_length_nm if self.units=='nm' else self.scale_length_nm/1000)
        self.scale_label.setText(f'{val} {self.units}')
        self._position_overlays()

    # ... remaining methods unchanged ...

if __name__=='__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

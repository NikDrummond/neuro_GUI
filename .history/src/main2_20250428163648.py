import os
# — Environment tweaks to suppress warnings —
os.environ['QT_DEBUG_PLUGINS'] = '0'
os.environ['GI_TYPELIB_PATH'] = '/usr/lib/x86_64-linux-gnu/girepository-1.0'
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu:' + os.environ.get('LD_LIBRARY_PATH','')
os.environ['GV_PLUGIN_PATH'] = '/usr/lib/graphviz'

import sys, pathlib, warnings, logging
import numpy as np, pandas as pd
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

# ——— Helpers for point-selection —————————————————————
def n_pnt_coords(N):
    return nr.g_vert_coords(N)[nr.g_lb_inds(N)]

def make_pnts(coords, mask):
    return (vd.Points(coords[mask],  c='b', r=8),
            vd.Points(coords[~mask], c='r', r=8))

def get_mask_node_ind(N, mask):
    return nr.g_lb_inds(N)[mask]

# ——— Logging handler to embed into a QTextEdit —————————
class QTextEditLogger(logging.Handler):
    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.widget = text_edit
        fmt = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s',
                                datefmt='%H:%M:%S')
        self.setFormatter(fmt)
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.widget.append(msg)
            bar = self.widget.verticalScrollBar()
            bar.setValue(bar.maximum())
        QTimer.singleShot(0, append)

# ——— MainWindow ———————————————————————————————————————
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Neurosetta Viewer')

        # — State —————————————————————————————————————
        self.files = []
        self.current_index = 0
        self.current_lines = None
        self.current_object = None
        self.current_neuron = None
        self.vertex_coords = None

        # selection state
        self.pnt_coords = None
        self.pnt_mask   = None
        self.pnt_in     = None
        self.pnt_out    = None
        self.hover_marker = None

        self.selected_points = []

        # scale-bar
        self.units = 'nm'
        self.scale_length_nm = 5000

        # — Central UI —————————————————————————————————
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)

        # VTK viewer
        self.vtkWidget = QVTKRenderWindowInteractor(central)
        self.plotter   = vd.Plotter(qt_widget=self.vtkWidget, bg='white')
        cam = self.plotter.renderer.GetActiveCamera()
        cam.SetParallelProjection(True)

        # scale overlay
        self.scale_widget = QWidget(self.vtkWidget)
        swl = QVBoxLayout(self.scale_widget)
        swl.setContentsMargins(2,2,2,2)
        self.bar_line  = QFrame(self.scale_widget)
        self.bar_line.setFrameShape(QFrame.HLine)
        self.bar_line.setLineWidth(2)
        swl.addWidget(self.bar_line, alignment=Qt.AlignCenter)
        self.scale_label = QLabel(self.scale_widget)
        swl.addWidget(self.scale_label, alignment=Qt.AlignCenter)
        self.scale_widget.setVisible(False)
        self.scale_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.scale_widget.raise_()

        # nav buttons
        self.prev_btn = QPushButton(self.vtkWidget)
        self.prev_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowLeft))
        self.prev_btn.clicked.connect(self.show_previous)
        self.prev_btn.raise_()
        self.next_btn = QPushButton(self.vtkWidget)
        self.next_btn.setIcon(self.style().standardIcon(QApplication.style().SP_ArrowRight))
        self.next_btn.clicked.connect(self.show_next)
        self.next_btn.raise_()

        # side panel
        side = QWidget()
        sl = QVBoxLayout(side)
        sl.setContentsMargins(5,5,5,5)
        sl.addWidget(QLabel('Current File:'))
        self.filename_label = QLabel('')
        self.filename_label.setStyleSheet('font-weight: bold;')
        sl.addWidget(self.filename_label)
        sl.addSpacing(10)

        self.select_checkbox = QCheckBox('Select Points')
        self.select_checkbox.toggled.connect(self.toggle_select_points)
        sl.addWidget(self.select_checkbox)

        self.mask_down_btn = QPushButton('Mask Downstream')
        self.mask_down_btn.setEnabled(False)
        self.mask_down_btn.clicked.connect(self.mask_downstream)
        sl.addWidget(self.mask_down_btn)

        sl.addStretch(1)
        side.setFixedWidth(180)

        main_layout.addWidget(self.vtkWidget, stretch=1)
        main_layout.addWidget(side)

        # picker & interactor
        self.picker = vtkPointPicker()
        self.picker.SetTolerance(0.005)
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        iren.SetPicker(self.picker)
        iren.AddObserver('MouseWheelForwardEvent',  self._update_scale_overlay)
        iren.AddObserver('MouseWheelBackwardEvent', self._update_scale_overlay)
        iren.Initialize()
        self.vtkWidget.installEventFilter(self)

        # menus + logging dock
        self._init_menu()

        # initial overlay positions
        self._update_scale_overlay()
        self._position_overlays()


    def _init_menu(self):
        mb = self.menuBar()

        # File menu
        fm = mb.addMenu('File')
        fm.addAction(QAction('Load File…',   self, triggered=self.read_file))
        fm.addAction(QAction('Load Folder…', self, triggered=self.read_folder))
        fm.addAction(QAction('Save…',        self, triggered=self.save_file))
        fm.addAction(QAction('Exit',         self, triggered=self.close))

        # Tools menu
        tm = mb.addMenu('Tools')
        # Show log
        self.log_dock = QDockWidget("Console Log", self)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.log_console = QTextEdit(self)
        self.log_console.setReadOnly(True)
        self.log_dock.setWidget(self.log_console)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.log_dock.hide()
        act_log = QAction("Show Log", self, checkable=True)
        act_log.toggled.connect(lambda v: self.log_dock.setVisible(v))
        tm.addAction(act_log)
        logging.getLogger().addHandler(QTextEditLogger(self.log_console))
        logging.getLogger().setLevel(logging.DEBUG)
        # Show subtree
        tm.addAction(QAction('Show Current Subtree', self, triggered=self.show_subtree))

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
        self.scale_act = QAction('Toggle Scale Bar', self, checkable=True)
        self.scale_act.toggled.connect(lambda v: self.scale_widget.setVisible(v))
        vm.addAction(self.scale_act)
        vm.addAction(QAction('Set Scale Bar Size…', self, triggered=self.set_scale_size))
        # Colour
        vm.addAction(QAction('Set Neuron Colour…', self, triggered=self.set_neuron_colour))


    def eventFilter(self, obj, event):
        if obj is self.vtkWidget:
            if event.type() == QEvent.Resize:
                self._position_overlays()
            if (event.type() == QEvent.MouseMove and
                self.pnt_coords is not None):
                self._on_hover(event)
                return False
            if (event.type() == QEvent.MouseButtonPress and
                event.modifiers() & Qt.ShiftModifier and
                self.pnt_coords is not None):
                self._on_shift_click(event)
                return True
        return super().eventFilter(obj, event)


    def _position_overlays(self):
        w,h = self.vtkWidget.width(), self.vtkWidget.height()
        sw  = self.scale_widget.sizeHint()
        self.scale_widget.move((w-sw.width())//2, h-sw.height()-10)
        pb = self.prev_btn.sizeHint()
        self.prev_btn.move(10, h-pb.height()-10)
        nb = self.next_btn.sizeHint()
        self.next_btn.move(w-nb.width()-10, h-nb.height()-10)


    def _update_scale_overlay(self, *args):
        ren = self.plotter.renderer
        cam = ren.GetActiveCamera()
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


    # — File I/O & rendering ——————————————————————————————
    def read_file(self):
        fn, _ = QFileDialog.getOpenFileName(self, 'Open File','','CSV (*.csv);;Neurosetta (*.nr);;SWC (*.swc)')
        if fn:
            self.files=[fn]; self.current_index=0; self.load_current_file()

    def read_folder(self):
        fld = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if fld:
            self.files=[str(p) for p in pathlib.Path(fld).glob('*')
                        if p.suffix.lower() in ['.nr','.swc']]
            self.current_index=0
            if self.files: self.load_current_file()

    def load_current_file(self):
        f = self.files[self.current_index]
        self.filename_label.setText(pathlib.Path(f).name)
        try:
            if f.lower().endswith('.csv'):
                df = pd.read_csv(f)
                if not all(c in df.columns for c in ['x','y','z']):
                    raise ValueError('CSV needs x,y,z')
                pts = df[['x','y','z']].to_numpy()
                self.vertex_coords = pts
                self.render_point_cloud(pts)
            else:
                n = nr.load(f); self.current_neuron = n
                coords = nr.g_vert_coords(n)
                self.vertex_coords = np.array(coords)
                self.render_nr(n)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load: {e}')

    def save_file(self):
        if not self.current_object:
            QMessageBox.warning(self, 'Warning','Nothing to save.'); return
        sp, _ = QFileDialog.getSaveFileName(self,'Save As','','Neurosetta (*.nr)')
        if sp: nr.save(self.current_object, sp)

    def render_point_cloud(self, pts):
        self._display(vd.Points(pts, r=5, c='cyan'))

    def render_nr(self, n):
        ln   = nr.plotting._vd_tree_lines(n, c='red')
        soma = vd.Point(nr.g_vert_coords(n,nr.g_root_ind(n))[0], c='red', r=10)
        self.current_lines = ln
        self.soma = soma
        self._display(vd.Assembly([ln,soma]))


    def _display(self, obj):
        # clear prior selection overlays
        self.selected_points.clear()
        for a in ('pnt_in','pnt_out','hover_marker'):
            if getattr(self,a,None):
                self.plotter.remove(getattr(self,a))
        self.current_object = obj
        self.plotter.clear(); self.plotter.add(obj)
        self.plotter.show(resetcam=True)
        self.vtkWidget.update()
        self._update_scale_overlay()


    # — Navigation —————————————————————————————————————
    def show_previous(self):
        if self.current_index>0:
            self.current_index-=1; self.load_current_file()

    def show_next(self):
        if self.current_index<len(self.files)-1:
            self.current_index+=1; self.load_current_file()


    # — Viewer actions —————————————————————————————————
    def set_units(self, u):
        self.units = u
        self.nm_act.setChecked(u=='nm')
        self.um_act.setChecked(u=='µm')
        self._update_scale_overlay()

    def set_scale_size(self):
        default = (self.scale_length_nm if self.units=='nm'
                   else self.scale_length_nm//1000)
        v,ok = QInputDialog.getInt(self,'Scale Bar Size',f'Enter size in {self.units}:',default,1)
        if ok:
            self.scale_length_nm = (v if self.units=='nm' else v*1000)
            self._update_scale_overlay()

    def set_neuron_colour(self):
        col = QColorDialog.getColor()
        if col.isValid() and self.current_lines:
            self.current_lines.c(col.name())
            self.soma.c(col.name())
            self.plotter.render()

    # def show_subtree(self):
    #     ln = nr.plotting._vd_subtree_lns(self.current_neuron)
    #     self._display(vd.Assembly([ln,self.soma]))
    #     # self.plotter.render()
    def show_subtree(self):
        """Display only the subtree under the current neuron root."""
        if not self.current_neuron:
            return

        # Call the Neurosetta helper
        res = nr.plotting._vd_subtree_lns(self.current_neuron)

        # Normalize to a list of actors
        if isinstance(res, (tuple, list)):
            actors = list(res)
        else:
            actors = [res]

        # Always include the soma marker as well
        actors.append(self.soma)

        # Display them
        self._display(vd.Assembly(actors))


    # — Point Selection ——————————————————————————————————
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
            for a in ('pnt_in','pnt_out','hover_marker'):
                if getattr(self,a,None):
                    self.plotter.remove(getattr(self,a))
            self.plotter.render()
        self._update_mask_button_state()

    def _init_point_selection(self):
        if not self.current_neuron:
            return
        self.pnt_coords = n_pnt_coords(self.current_neuron)
        self.pnt_mask   = np.zeros(len(self.pnt_coords),dtype=bool)
        self._update_point_overlays()
        self.hover_marker = vd.Point([0,0,0],c='yellow',r=15,alpha=0.6)
        self.plotter.add(self.hover_marker)
        self.plotter.render()

    def _update_point_overlays(self):
        if self.pnt_in: self.plotter.remove(self.pnt_in)
        if self.pnt_out: self.plotter.remove(self.pnt_out)
        self.pnt_in, self.pnt_out = make_pnts(self.pnt_coords, self.pnt_mask)
        self.plotter.add(self.pnt_out).add(self.pnt_in)
        self.plotter.render()

    def _on_hover(self, event):
        if self.pnt_coords is None: return
        x = event.x(); y = self.vtkWidget.height() - event.y()
        self.picker.Pick(x,y,0,self.plotter.renderer)
        pos = np.array(self.picker.GetPickPosition())
        d = np.linalg.norm(self.pnt_coords - pos, axis=1)
        i = d.argmin()
        if d[i]>20:
            self.hover_marker.alpha(0)
        else:
            self.hover_marker.pos(self.pnt_coords[i])
            self.hover_marker.alpha(0.6)
        self.plotter.render()

    def _on_shift_click(self, event):
        if self.pnt_coords is None: return
        x = event.x(); y = self.vtkWidget.height() - event.y()
        self.picker.Pick(x,y,0,self.plotter.renderer)
        pos = np.array(self.picker.GetPickPosition())
        d = np.linalg.norm(self.pnt_coords - pos, axis=1)
        i = d.argmin()
        if d[i] <= 20:
            self.pnt_mask[i] = not self.pnt_mask[i]
            self._update_point_overlays()
            self._update_mask_button_state()

    def _update_mask_button_state(self):
        ok = (self.select_checkbox.isChecked() and
              self.pnt_mask is not None and
              np.sum(self.pnt_mask)==1)
        self.mask_down_btn.setEnabled(ok)

    def mask_downstream(self):
        idx = get_mask_node_ind(self.current_neuron, self.pnt_mask)[0]
        nr.g_subtree_mask(self.current_neuron, idx)
        logging.info(f"Masking downstream from node {idx}")
        # … downstream logic …

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

"""Shared test configuration and fixtures."""

import pytest
import sys
import os
import numpy as np
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Mock external dependencies at import level to prevent import errors
sys.modules['vedo'] = MagicMock()
sys.modules['Neurosetta'] = MagicMock()
sys.modules['graph_tool'] = MagicMock()
sys.modules['graph_tool.all'] = MagicMock()
sys.modules['vtk'] = MagicMock()
sys.modules['PySide2'] = MagicMock()
sys.modules['PySide2.QtWidgets'] = MagicMock()
sys.modules['PySide2.QtCore'] = MagicMock()
sys.modules['PySide2.QtGui'] = MagicMock()

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock VTK and GUI components for headless testing
@pytest.fixture(autouse=True)
def mock_gui_components(monkeypatch):
    """Mock GUI components for headless testing."""
    # Mock VTK components
    mock_vtk = MagicMock()
    monkeypatch.setattr('vtk.vtkPointPicker', lambda: mock_vtk)
    monkeypatch.setattr('vtk.qt.QVTKRenderWindowInteractor.QVTKRenderWindowInteractor', MagicMock)
    
    # Mock vedo components
    mock_vedo = MagicMock()
    monkeypatch.setattr('vedo.Plotter', lambda **kwargs: mock_vedo)
    monkeypatch.setattr('vedo.Points', lambda *args, **kwargs: mock_vedo)
    monkeypatch.setattr('vedo.Point', lambda *args, **kwargs: mock_vedo)
    monkeypatch.setattr('vedo.Assembly', lambda *args, **kwargs: mock_vedo)

@pytest.fixture
def sample_coordinates():
    """Sample 3D coordinates for testing."""
    return np.array([
        [0.0, 0.0, 0.0],
        [1.0, 1.0, 1.0],
        [2.0, 2.0, 2.0],
        [3.0, 3.0, 3.0],
        [4.0, 4.0, 4.0]
    ])

@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    import pandas as pd
    return pd.DataFrame({
        'x': [0.0, 1.0, 2.0, 3.0, 4.0],
        'y': [0.0, 1.0, 2.0, 3.0, 4.0],
        'z': [0.0, 1.0, 2.0, 3.0, 4.0]
    })

@pytest.fixture
def mock_neuron():
    """Mock Neurosetta neuron object for testing."""
    neuron = MagicMock()
    neuron.vertices = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]])
    return neuron

@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test_data.csv"
    test_file.write_text("x,y,z\n0,0,0\n1,1,1\n2,2,2\n")
    return str(test_file)

@pytest.fixture
def mock_plotter():
    """Mock vedo plotter for testing."""
    plotter = MagicMock()
    plotter.renderer = MagicMock()
    plotter.renderer.GetActiveCamera = MagicMock()
    return plotter

@pytest.fixture
def mock_picker():
    """Mock VTK picker for testing."""
    picker = MagicMock()
    picker.Pick = MagicMock()
    picker.GetPickPosition = MagicMock(return_value=[0, 0, 0])
    return picker

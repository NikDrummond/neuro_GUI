"""Integration tests for the Neurosetta GUI application."""

import pytest
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


@pytest.mark.integration
class TestFileLoadingIntegration:
    """Integration tests for file loading workflow."""
    
    def test_csv_loading_workflow(self, tmp_path):
        """Test complete CSV loading workflow."""
        # Create test CSV file
        csv_file = tmp_path / "test_data.csv"
        csv_content = "x,y,z\n0.0,0.0,0.0\n1.0,1.0,1.0\n2.0,2.0,2.0\n"
        csv_file.write_text(csv_content)
        
        # Mock GUI components
        with patch('src.core.application.AppSettings'), \
             patch('src.core.application.NeuronRenderer'), \
             patch('src.core.application.PointSelector'), \
             patch('src.core.application.NeuronTools'):
            
            from core.application import NeuroGUIApplication
            
            app = NeuroGUIApplication(Mock(), Mock())
            
            # Test loading the file
            result = app.load_file(str(csv_file))
            
            assert result is True
            assert app.vertex_coords is not None
            assert app.vertex_coords.shape == (3, 3)
            assert app.current_neuron is None  # CSV doesn't create neuron
    
    @patch('file_io.file_manager.nr.load')
    @patch('file_io.file_manager.nr.g_vert_coords')
    def test_neuron_loading_workflow(self, mock_g_vert_coords, mock_nr_load, tmp_path):
        """Test complete neuron file loading workflow."""
        # Create test neuron file
        neuron_file = tmp_path / "test_neuron.nr"
        neuron_file.write_text("dummy neuron data")
        
        # Mock Neurosetta functions
        mock_neuron = Mock()
        mock_nr_load.return_value = mock_neuron
        mock_g_vert_coords.return_value = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
        
        with patch('src.core.application.AppSettings'), \
             patch('src.core.application.NeuronRenderer'), \
             patch('src.core.application.PointSelector'), \
             patch('src.core.application.NeuronTools'), \
             patch('src.core.application.FileManager'), \
             patch('src.file_io.file_manager.n_pnt_coords') as mock_n_pnt_coords:
            
            mock_n_pnt_coords.return_value = np.array([[0, 0, 0], [1, 1, 1]])
            
            from core.application import NeuroGUIApplication
            
            app = NeuroGUIApplication(Mock(), Mock())
            
            # Test loading the file
            result = app.load_file(str(neuron_file))
            
            assert result is True
            assert app.current_neuron is mock_neuron
            assert app.vertex_coords is not None
            assert app.point_coords is not None


@pytest.mark.integration
class TestNeuronManipulationIntegration:
    """Integration tests for neuron manipulation workflows."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('src.core.application.AppSettings'), \
             patch('src.core.application.FileManager'), \
             patch('src.core.application.NeuronRenderer'), \
             patch('src.core.application.PointSelector'), \
             patch('src.core.application.NeuronTools'):
            
            from core.application import NeuroGUIApplication
            
            self.app = NeuroGUIApplication(Mock(), Mock())
            
            # Set up mock neuron
            self.mock_neuron = Mock()
            self.app.current_neuron = self.mock_neuron
            self.app.point_coords = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]])
    
    def test_reroot_workflow(self):
        """Test complete rerooting workflow."""
        # Mock point selection
        self.app.point_selector.get_selected_indices.return_value = np.array([1])
        self.app.neuron_tools.validate_selection_for_reroot.return_value = True
        
        # Mock rerooting result
        new_neuron = Mock()
        new_vertex_coords = np.array([[1, 1, 1], [0, 0, 0], [2, 2, 2]])
        new_point_coords = np.array([[1, 1, 1], [0, 0, 0]])
        
        self.app.neuron_tools.reroot_neuron.return_value = (
            new_neuron, new_vertex_coords, new_point_coords
        )
        
        with patch('src.core.application.nr') as mock_nr:
            mock_nr.g_lb_inds.return_value = np.array([0, 1])
            
            # Perform rerooting
            result = self.app.reroot_neuron()
            
            assert result is True
            assert self.app.current_neuron is new_neuron
            assert np.array_equal(self.app.vertex_coords, new_vertex_coords)
            assert np.array_equal(self.app.point_coords, new_point_coords)
            
            # Verify workflow steps
            self.app.neuron_tools.reroot_neuron.assert_called_once()
            self.app.point_selector.deactivate.assert_called_once()
            self.app.renderer.render_neuron.assert_called_once_with(new_neuron)
    
    def test_subtree_workflow(self):
        """Test complete subtree creation workflow."""
        # Mock point selection
        self.app.point_selector.get_selected_indices.return_value = np.array([0])
        self.app.neuron_tools.validate_selection_for_subtree.return_value = True
        
        # Perform subtree creation
        result = self.app.create_subtree()
        
        assert result is True
        
        # Verify workflow steps
        self.app.neuron_tools.create_subtree_mask.assert_called_once()
        self.app.point_selector.deactivate.assert_called_once()
        self.app.renderer.render_subtree.assert_called_once_with(self.mock_neuron)


@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration management."""
    
    def test_settings_environment_integration(self):
        """Test settings and environment configuration integration."""
        with patch.dict(os.environ, {}, clear=True):
            from config.settings import AppSettings
            
            settings = AppSettings()
            
            # Verify environment variables were set
            assert os.environ.get('QT_DEBUG_PLUGINS') == '0'
            assert '/usr/lib/x86_64-linux-gnu' in os.environ.get('LD_LIBRARY_PATH', '')
            
            # Test units conversion
            settings.set_units('µm')
            settings.set_scale_length(5, 'µm')
            
            assert settings.scale_length_nm == 5000
            assert settings.get_scale_length('nm') == 5000
            assert settings.get_scale_length('µm') == 5


@pytest.mark.integration 
class TestFileManagerIntegration:
    """Integration tests for file manager operations."""
    
    def test_file_scanning_and_loading(self, tmp_path):
        """Test file scanning and loading integration."""
        from file_io.file_manager import FileManager
        
        # Create test files
        (tmp_path / "neuron1.nr").write_text("neuron data 1")
        (tmp_path / "neuron2.swc").write_text("neuron data 2")
        (tmp_path / "data.csv").write_text("x,y,z\n0,0,0\n1,1,1\n")
        (tmp_path / "readme.txt").write_text("readme")
        
        file_manager = FileManager()
        
        # Test folder scanning
        files = file_manager.scan_folder_for_files(str(tmp_path))
        
        # Should find .nr and .swc files, but not .csv or .txt
        assert len(files) == 2
        assert any('neuron1.nr' in f for f in files)
        assert any('neuron2.swc' in f for f in files)
        
        # Test file format detection
        assert file_manager.is_supported_file(str(tmp_path / "neuron1.nr"))
        assert file_manager.is_supported_file(str(tmp_path / "data.csv"))
        assert not file_manager.is_supported_file(str(tmp_path / "readme.txt"))


@pytest.mark.integration
@pytest.mark.slow
class TestRenderingIntegration:
    """Integration tests for rendering components."""
    
    def test_renderer_point_selector_integration(self):
        """Test renderer and point selector integration."""
        from rendering.renderer import NeuronRenderer
        from rendering.point_selector import PointSelector
        
        mock_plotter = Mock()
        mock_picker = Mock()
        
        renderer = NeuronRenderer(mock_plotter)
        point_selector = PointSelector(mock_plotter, mock_picker)
        
        # Test point cloud rendering
        coordinates = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]])
        
        with patch('rendering.renderer.vd.Points') as mock_points:
            renderer.render_point_cloud(coordinates)
            mock_points.assert_called_once()
        
        # Test point selection activation
        point_selector.activate(coordinates)
        
        assert point_selector.is_active
        assert np.array_equal(point_selector.point_coords, coordinates)
        assert len(point_selector.point_mask) == 3

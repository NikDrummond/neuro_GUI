"""Unit tests for the core module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from core.application import NeuroGUIApplication


class TestNeuroGUIApplication:
    """Test NeuroGUIApplication class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_plotter = Mock()
        self.mock_picker = Mock()
        
        # Create instance mocks
        self.mock_settings = Mock()
        self.mock_file_manager = Mock()
        self.mock_renderer = Mock()
        self.mock_point_selector = Mock()
        self.mock_neuron_tools = Mock()
        
        # Mock all the component classes to return our instance mocks
        with patch('src.core.application.AppSettings', return_value=self.mock_settings), \
             patch('src.core.application.FileManager', return_value=self.mock_file_manager), \
             patch('src.core.application.NeuronRenderer', return_value=self.mock_renderer), \
             patch('src.core.application.PointSelector', return_value=self.mock_point_selector), \
             patch('src.core.application.NeuronTools', return_value=self.mock_neuron_tools):
            
            self.app = NeuroGUIApplication(self.mock_plotter, self.mock_picker)
    
    def test_initialization(self):
        """Test NeuroGUIApplication initialization."""
        assert self.app.files == []
        assert self.app.current_file_index == 0
        assert self.app.current_neuron is None
        assert self.app.vertex_coords is None
        assert self.app.point_coords is None
        assert self.app.neuron_indices is None
    
    def test_set_callbacks(self):
        """Test setting callbacks."""
        selection_callback = Mock()
        file_callback = Mock()
        
        self.app.set_selection_changed_callback(selection_callback)
        self.app.set_file_loaded_callback(file_callback)
        
        assert self.app.selection_changed_callback is selection_callback
        assert self.app.file_loaded_callback is file_callback
    
    def test_load_file_success(self):
        """Test successful file loading."""
        filepath = "/test/neuron.nr"
        
        # Mock file manager load_file to return neuron data
        mock_neuron = Mock()
        vertex_coords = np.array([[0, 0, 0], [1, 1, 1]])
        point_coords = np.array([[0, 0, 0], [1, 1, 1]])
        
        self.mock_file_manager.load_file.return_value = (mock_neuron, vertex_coords, point_coords)
        
        with patch.object(self.app, '_load_current_file', return_value=True) as mock_load:
            result = self.app.load_file(filepath)
            
            assert result is True
            assert self.app.files == [filepath]
            assert self.app.current_file_index == 0
            mock_load.assert_called_once()
    
    def test_load_file_failure(self):
        """Test file loading failure."""
        filepath = "/test/nonexistent.nr"
        
        with patch.object(self.app, '_load_current_file', side_effect=Exception("Load failed")):
            result = self.app.load_file(filepath)
            
            assert result is False
    
    def test_load_folder_success(self):
        """Test successful folder loading."""
        folder_path = "/test/folder"
        files = ["/test/folder/neuron1.nr", "/test/folder/neuron2.swc"]
        
        self.mock_file_manager.scan_folder_for_files.return_value = files
        
        with patch.object(self.app, '_load_current_file', return_value=True) as mock_load:
            result = self.app.load_folder(folder_path)
            
            assert result is True
            assert self.app.files == files
            assert self.app.current_file_index == 0
            mock_load.assert_called_once()
    
    def test_load_folder_no_files(self):
        """Test folder loading with no files found."""
        folder_path = "/test/empty_folder"
        
        self.mock_file_manager.scan_folder_for_files.return_value = []
        
        result = self.app.load_folder(folder_path)
        
        assert result is False
    
    def test_save_current_file_success(self):
        """Test successful current file saving."""
        self.app.current_neuron = Mock()
        self.app.files = ["/test/neuron.nr"]
        self.app.current_file_index = 0
        
        self.mock_file_manager.get_directory_from_path.return_value = "/test"
        self.mock_file_manager.save_neuron_to_directory.return_value = None
        
        result = self.app.save_current_file()
        
        assert result is True
        self.mock_file_manager.save_neuron_to_directory.assert_called_once()
    
    def test_save_current_file_no_neuron(self):
        """Test saving current file with no neuron loaded."""
        self.app.current_neuron = None
        
        result = self.app.save_current_file()
        
        assert result is False
    
    def test_save_file_as_success(self):
        """Test successful save as operation."""
        self.app.current_neuron = Mock()
        filepath = "/test/new_neuron.nr"
        
        self.mock_file_manager.save_neuron.return_value = None
        
        result = self.app.save_file_as(filepath)
        
        assert result is True
        self.mock_file_manager.save_neuron.assert_called_once_with(self.app.current_neuron, filepath)
    
    def test_save_file_as_no_neuron(self):
        """Test save as with no neuron loaded."""
        self.app.current_neuron = None
        
        result = self.app.save_file_as("/test/neuron.nr")
        
        assert result is False
    
    def test_navigate_previous_success(self):
        """Test successful previous navigation."""
        self.app.files = ["/test/1.nr", "/test/2.nr", "/test/3.nr"]
        self.app.current_file_index = 2
        
        with patch.object(self.app, '_load_current_file', return_value=True) as mock_load:
            result = self.app.navigate_previous()
            
            assert result is True
            assert self.app.current_file_index == 1
            mock_load.assert_called_once()
    
    def test_navigate_previous_at_start(self):
        """Test previous navigation at start of list."""
        self.app.files = ["/test/1.nr", "/test/2.nr"]
        self.app.current_file_index = 0
        
        result = self.app.navigate_previous()
        
        assert result is False
        assert self.app.current_file_index == 0
    
    def test_navigate_next_success(self):
        """Test successful next navigation."""
        self.app.files = ["/test/1.nr", "/test/2.nr", "/test/3.nr"]
        self.app.current_file_index = 0
        
        with patch.object(self.app, '_load_current_file', return_value=True) as mock_load:
            result = self.app.navigate_next()
            
            assert result is True
            assert self.app.current_file_index == 1
            mock_load.assert_called_once()
    
    def test_navigate_next_at_end(self):
        """Test next navigation at end of list."""
        self.app.files = ["/test/1.nr", "/test/2.nr"]
        self.app.current_file_index = 1
        
        result = self.app.navigate_next()
        
        assert result is False
        assert self.app.current_file_index == 1
    
    def test_can_navigate_previous(self):
        """Test can_navigate_previous method."""
        self.app.current_file_index = 0
        assert self.app.can_navigate_previous() is False
        
        self.app.current_file_index = 1
        assert self.app.can_navigate_previous() is True
    
    def test_can_navigate_next(self):
        """Test can_navigate_next method."""
        self.app.files = ["/test/1.nr", "/test/2.nr"]
        
        self.app.current_file_index = 0
        assert self.app.can_navigate_next() is True
        
        self.app.current_file_index = 1
        assert self.app.can_navigate_next() is False
    
    def test_get_current_filename(self):
        """Test get_current_filename method."""
        # No files
        assert self.app.get_current_filename() == ""
        
        # With files
        self.app.files = ["/test/path/neuron.nr"]
        self.app.current_file_index = 0
        
        filename = self.app.get_current_filename()
        assert filename == "neuron.nr"
    
    def test_activate_point_selection_success(self):
        """Test successful point selection activation."""
        self.app.point_coords = np.array([[0, 0, 0], [1, 1, 1]])
        
        result = self.app.activate_point_selection()
        
        assert result is True
        self.mock_point_selector.activate.assert_called_once_with(self.app.point_coords)
    
    def test_activate_point_selection_no_coords(self):
        """Test point selection activation with no coordinates."""
        self.app.point_coords = None
        
        result = self.app.activate_point_selection()
        
        assert result is False
    
    def test_deactivate_point_selection(self):
        """Test point selection deactivation."""
        self.app.deactivate_point_selection()
        
        self.mock_point_selector.deactivate.assert_called_once()
    
    def test_reroot_neuron_success(self):
        """Test successful neuron rerooting."""
        mock_neuron = Mock()
        self.app.current_neuron = mock_neuron
        
        # Mock point selector and neuron tools
        self.mock_point_selector.get_selected_indices.return_value = np.array([0])
        self.mock_neuron_tools.validate_selection_for_reroot.return_value = True
        self.mock_neuron_tools.reroot_neuron.return_value = (
            mock_neuron, 
            np.array([[0, 0, 0]]), 
            np.array([[0, 0, 0]])
        )
        
        with patch('src.core.application.Neurosetta') as mock_nr:
            mock_nr.g_lb_inds.return_value = np.array([0])
            
            result = self.app.reroot_neuron()
            
            assert result is True
            self.mock_neuron_tools.reroot_neuron.assert_called_once()
            self.mock_point_selector.deactivate.assert_called_once()
            self.mock_renderer.render_neuron.assert_called_once()
    
    def test_reroot_neuron_invalid_selection(self):
        """Test neuron rerooting with invalid selection."""
        self.mock_point_selector.get_selected_indices.return_value = np.array([])
        self.mock_neuron_tools.validate_selection_for_reroot.return_value = False
        
        result = self.app.reroot_neuron()
        
        assert result is False
    
    def test_create_subtree_success(self):
        """Test successful subtree creation."""
        self.mock_point_selector.get_selected_indices.return_value = np.array([0])
        self.mock_neuron_tools.validate_selection_for_subtree.return_value = True
        
        result = self.app.create_subtree()
        
        assert result is True
        self.mock_neuron_tools.create_subtree_mask.assert_called_once()
        self.mock_point_selector.deactivate.assert_called_once()
        self.mock_renderer.render_subtree.assert_called_once()
    
    def test_show_subtree(self):
        """Test show_subtree method."""
        self.app.current_neuron = Mock()
        
        self.app.show_subtree()
        
        self.mock_renderer.render_subtree.assert_called_once_with(self.app.current_neuron)
    
    def test_set_neuron_color(self):
        """Test set_neuron_color method."""
        color = "#ff0000"
        
        self.app.set_neuron_color(color)
        
        self.mock_renderer.set_neuron_color.assert_called_once_with(color)
    
    def test_get_selection_count(self):
        """Test get_selection_count method."""
        # Mock the point selector's get_selection_count method
        self.mock_point_selector.get_selection_count = Mock(return_value=3)
        
        count = self.app.get_selection_count()
        
        assert count == 3
    
    def test_is_selection_valid_for_reroot(self):
        """Test is_selection_valid_for_reroot method."""
        # Mock the point selector's get_selected_indices method
        self.mock_point_selector.get_selected_indices = Mock(return_value=np.array([0]))
        
        result = self.app.is_selection_valid_for_reroot()
        
        assert result is True
    
    def test_is_selection_valid_for_subtree(self):
        """Test is_selection_valid_for_subtree method."""
        # Mock the point selector's get_selected_indices method
        self.mock_point_selector.get_selected_indices = Mock(return_value=np.array([0]))
        # Mock the neuron tools validation
        self.mock_neuron_tools.validate_selection_for_subtree = Mock(return_value=True)
        
        result = self.app.is_selection_valid_for_subtree()
        
        assert result is True

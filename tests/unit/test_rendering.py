"""Unit tests for the rendering module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from rendering.renderer import NeuronRenderer
from rendering.point_selector import PointSelector


class TestNeuronRenderer:
    """Test NeuronRenderer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_plotter = Mock()
        self.mock_plotter.renderer = Mock()
        self.mock_plotter.renderer.GetActiveCamera = Mock()
        self.renderer = NeuronRenderer(self.mock_plotter)
    
    def test_initialization(self):
        """Test NeuronRenderer initialization."""
        assert self.renderer.plotter is self.mock_plotter
        assert self.renderer.current_object is None
        assert self.renderer.current_lines is None
        assert self.renderer.soma is None
        assert self.renderer.neuron_color == 'red'
    
    @patch('rendering.renderer.vd.Points')
    def test_render_point_cloud(self, mock_points):
        """Test render_point_cloud method."""
        coordinates = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]])
        mock_points_obj = Mock()
        mock_points.return_value = mock_points_obj
        
        self.renderer.render_point_cloud(coordinates)
        
        # Verify Points was created with correct parameters
        mock_points.assert_called_once_with(coordinates, r=5, c='cyan')
        
        # Verify display was called
        assert self.renderer.current_object is mock_points_obj
    
    @patch('rendering.renderer.nr.plotting._vd_tree_lines')
    @patch('rendering.renderer.nr.g_vert_coords')
    @patch('rendering.renderer.nr.g_root_ind')
    @patch('rendering.renderer.vd.Point')
    @patch('rendering.renderer.vd.Assembly')
    def test_render_neuron(self, mock_assembly, mock_point, mock_g_root_ind, 
                          mock_g_vert_coords, mock_vd_tree_lines):
        """Test render_neuron method."""
        mock_neuron = Mock()
        mock_lines = Mock()
        mock_soma = Mock()
        mock_assembly_obj = Mock()
        
        mock_vd_tree_lines.return_value = mock_lines
        mock_g_vert_coords.return_value = [[0, 0, 0]]
        mock_g_root_ind.return_value = 0
        mock_point.return_value = mock_soma
        mock_assembly.return_value = mock_assembly_obj
        
        self.renderer.render_neuron(mock_neuron)
        
        # Verify neuron lines were created
        mock_vd_tree_lines.assert_called_once_with(mock_neuron, c='red')
        
        # Verify soma was created
        mock_point.assert_called_once_with([0, 0, 0], c='red', r=10)
        
        # Verify assembly was created
        mock_assembly.assert_called_once_with([mock_lines, mock_soma])
        
        # Verify references were stored
        assert self.renderer.current_lines is mock_lines
        assert self.renderer.soma is mock_soma
    
    @patch('rendering.renderer.nr.plotting._vd_subtree_lns')
    @patch('rendering.renderer.vd.Assembly')
    def test_render_subtree(self, mock_assembly, mock_vd_subtree_lns):
        """Test render_subtree method."""
        mock_neuron = Mock()
        mock_subtree = Mock()
        mock_assembly_obj = Mock()
        
        # Set up soma
        self.renderer.soma = Mock()
        
        mock_vd_subtree_lns.return_value = mock_subtree
        mock_assembly.return_value = mock_assembly_obj
        
        self.renderer.render_subtree(mock_neuron)
        
        # Verify subtree was created
        mock_vd_subtree_lns.assert_called_once_with(mock_neuron)
        
        # Verify assembly includes subtree and soma
        mock_assembly.assert_called_once_with([mock_subtree, self.renderer.soma])
    
    def test_render_subtree_no_neuron(self):
        """Test render_subtree with no neuron."""
        # Should not raise exception
        self.renderer.render_subtree(None)
    
    def test_set_neuron_color(self):
        """Test set_neuron_color method."""
        # Set up current lines and soma
        mock_lines = Mock()
        mock_soma = Mock()
        self.renderer.current_lines = mock_lines
        self.renderer.soma = mock_soma
        
        self.renderer.set_neuron_color('#ff0000')
        
        # Verify color was set
        assert self.renderer.neuron_color == '#ff0000'
        mock_lines.c.assert_called_once_with('#ff0000')
        mock_soma.c.assert_called_once_with('#ff0000')
        self.mock_plotter.render.assert_called_once()
    
    def test_clear(self):
        """Test clear method."""
        self.renderer.current_object = Mock()
        self.renderer.current_lines = Mock()
        self.renderer.soma = Mock()
        
        self.renderer.clear()
        
        self.mock_plotter.clear.assert_called_once()
        assert self.renderer.current_object is None
        assert self.renderer.current_lines is None
        assert self.renderer.soma is None
    
    def test_get_current_object(self):
        """Test get_current_object method."""
        mock_obj = Mock()
        self.renderer.current_object = mock_obj
        
        assert self.renderer.get_current_object() is mock_obj
    
    def test_has_neuron_lines(self):
        """Test has_neuron_lines method."""
        assert self.renderer.has_neuron_lines() is False
        
        self.renderer.current_lines = Mock()
        assert self.renderer.has_neuron_lines() is True
    
    def test_update_display(self):
        """Test update_display method."""
        self.renderer.update_display()
        self.mock_plotter.render.assert_called_once()


class TestPointSelector:
    """Test PointSelector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_plotter = Mock()
        self.mock_picker = Mock()
        self.point_selector = PointSelector(self.mock_plotter, self.mock_picker)
    
    def test_initialization(self):
        """Test PointSelector initialization."""
        assert self.point_selector.plotter is self.mock_plotter
        assert self.point_selector.picker is self.mock_picker
        assert self.point_selector.point_coords is None
        assert self.point_selector.point_mask is None
        assert self.point_selector.is_active is False
    
    def test_set_selection_changed_callback(self):
        """Test set_selection_changed_callback method."""
        callback = Mock()
        self.point_selector.set_selection_changed_callback(callback)
        assert self.point_selector.selection_changed_callback is callback
    
    @patch('rendering.point_selector.vd.Point')
    def test_activate(self, mock_point):
        """Test activate method."""
        coordinates = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]])
        mock_hover_marker = Mock()
        mock_point.return_value = mock_hover_marker
        
        with patch.object(self.point_selector, '_update_point_overlays') as mock_update:
            self.point_selector.activate(coordinates)
            
            assert self.point_selector.is_active is True
            assert np.array_equal(self.point_selector.point_coords, coordinates)
            assert len(self.point_selector.point_mask) == 3
            assert not any(self.point_selector.point_mask)  # All False initially
            
            # Verify hover marker was created and added
            mock_point.assert_called_once()
            self.mock_plotter.add.assert_called_with(mock_hover_marker)
            mock_update.assert_called_once()
    
    def test_deactivate(self):
        """Test deactivate method."""
        # Set up active state
        self.point_selector.is_active = True
        self.point_selector.point_coords = np.array([[0, 0, 0]])
        self.point_selector.point_mask = np.array([False])
        
        with patch.object(self.point_selector, '_remove_overlays') as mock_remove:
            self.point_selector.deactivate()
            
            assert self.point_selector.is_active is False
            assert self.point_selector.point_coords is None
            assert self.point_selector.point_mask is None
            mock_remove.assert_called_once()
    
    def test_handle_hover_inactive(self):
        """Test handle_hover when inactive."""
        mock_event = Mock()
        mock_event.x.return_value = 100
        mock_event.y.return_value = 200
        
        # Should do nothing when inactive
        self.point_selector.handle_hover(mock_event, 400)
        
        # Picker should not be called
        self.mock_picker.Pick.assert_not_called()
    
    def test_handle_hover_active(self):
        """Test handle_hover when active."""
        # Set up active state
        self.point_selector.is_active = True
        self.point_selector.point_coords = np.array([[0, 0, 0], [10, 10, 10]])
        self.point_selector.hover_marker = Mock()
        
        mock_event = Mock()
        mock_event.x.return_value = 100
        mock_event.y.return_value = 200
        
        # Mock picker to return position close to first point
        self.mock_picker.GetPickPosition.return_value = [1, 1, 1]
        
        self.point_selector.handle_hover(mock_event, 400)
        
        # Verify picker was called
        self.mock_picker.Pick.assert_called_once_with(100, 200, 0, self.mock_plotter.renderer)
        
        # Verify hover marker was positioned (close to first point)
        self.point_selector.hover_marker.pos.assert_called_once()
        self.point_selector.hover_marker.alpha.assert_called_with(0.6)
    
    def test_handle_click_inactive(self):
        """Test handle_click when inactive."""
        mock_event = Mock()
        result = self.point_selector.handle_click(mock_event, 400)
        
        assert result is False
        self.mock_picker.Pick.assert_not_called()
    
    def test_handle_click_active_success(self):
        """Test handle_click when active and successful."""
        # Set up active state
        self.point_selector.is_active = True
        self.point_selector.point_coords = np.array([[0, 0, 0], [10, 10, 10]])
        self.point_selector.point_mask = np.array([False, False])
        self.point_selector.selection_changed_callback = Mock()
        
        mock_event = Mock()
        mock_event.x.return_value = 100
        mock_event.y.return_value = 200
        
        # Mock picker to return position close to first point
        self.mock_picker.GetPickPosition.return_value = [1, 1, 1]
        
        with patch.object(self.point_selector, '_update_point_overlays') as mock_update:
            result = self.point_selector.handle_click(mock_event, 400)
            
            assert result is True
            assert self.point_selector.point_mask[0] == True  # First point selected
            mock_update.assert_called_once()
            self.point_selector.selection_changed_callback.assert_called_once()
    
    def test_get_selected_indices(self):
        """Test get_selected_indices method."""
        # No mask set
        indices = self.point_selector.get_selected_indices()
        assert len(indices) == 0
        
        # With mask
        self.point_selector.point_mask = np.array([True, False, True, False])
        indices = self.point_selector.get_selected_indices()
        expected = np.array([0, 2])
        np.testing.assert_array_equal(indices, expected)
    
    def test_get_selection_count(self):
        """Test get_selection_count method."""
        # No mask set
        assert self.point_selector.get_selection_count() == 0
        
        # With mask
        self.point_selector.point_mask = np.array([True, False, True, False])
        assert self.point_selector.get_selection_count() == 2
    
    def test_clear_selection(self):
        """Test clear_selection method."""
        self.point_selector.point_mask = np.array([True, False, True])
        self.point_selector.selection_changed_callback = Mock()
        
        with patch.object(self.point_selector, '_update_point_overlays') as mock_update:
            self.point_selector.clear_selection()
            
            assert not any(self.point_selector.point_mask)  # All False
            mock_update.assert_called_once()
            self.point_selector.selection_changed_callback.assert_called_once()

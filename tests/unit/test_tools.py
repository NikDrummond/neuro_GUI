"""Unit tests for the tools module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from tools.neuron_tools import NeuronTools


class TestNeuronTools:
    """Test NeuronTools class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.neuron_tools = NeuronTools()
    
    def test_initialization(self):
        """Test NeuronTools initialization."""
        assert self.neuron_tools.current_neuron is None
    
    def test_set_neuron(self):
        """Test set_neuron method."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        assert self.neuron_tools.current_neuron is mock_neuron
    
    def test_reroot_neuron_no_neuron_set(self):
        """Test reroot_neuron with no neuron set."""
        selected_indices = np.array([0])
        
        with pytest.raises(ValueError, match="No neuron set for rerooting"):
            self.neuron_tools.reroot_neuron(selected_indices)
    
    def test_reroot_neuron_invalid_selection_count(self):
        """Test reroot_neuron with invalid selection count."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        # Test with no selection
        with pytest.raises(ValueError, match="Exactly one point must be selected"):
            self.neuron_tools.reroot_neuron(np.array([]))
        
        # Test with multiple selections
        with pytest.raises(ValueError, match="Exactly one point must be selected"):
            self.neuron_tools.reroot_neuron(np.array([0, 1]))
    
    @patch('tools.neuron_tools.nr.reroot_tree')
    @patch('tools.neuron_tools.nr.g_vert_coords')
    @patch('tools.neuron_tools.n_pnt_coords')
    @patch('tools.neuron_tools.get_mask_node_ind')
    def test_reroot_neuron_success(self, mock_get_mask, mock_n_pnt_coords, 
                                   mock_g_vert_coords, mock_reroot_tree):
        """Test successful neuron rerooting."""
        # Set up mocks
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        mock_n_pnt_coords.return_value = np.array([[0, 0, 0], [1, 1, 1]])
        mock_get_mask.return_value = np.array([5])  # Node index 5
        mock_g_vert_coords.return_value = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
        
        selected_indices = np.array([0])
        
        # Call reroot_neuron
        neuron, vertex_coords, point_coords = self.neuron_tools.reroot_neuron(selected_indices)
        
        # Verify results
        assert neuron is mock_neuron
        assert isinstance(vertex_coords, np.ndarray)
        assert isinstance(point_coords, np.ndarray)
        
        # Verify reroot_tree was called with correct parameters
        mock_reroot_tree.assert_called_once_with(mock_neuron, root=5, inplace=True, prune=False)
    
    def test_create_subtree_mask_no_neuron_set(self):
        """Test create_subtree_mask with no neuron set."""
        selected_indices = np.array([0])
        
        with pytest.raises(ValueError, match="No neuron set for subtree operation"):
            self.neuron_tools.create_subtree_mask(selected_indices)
    
    def test_create_subtree_mask_invalid_selection_count(self):
        """Test create_subtree_mask with invalid selection count."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        # Test with no selection
        with pytest.raises(ValueError, match="Exactly one point must be selected"):
            self.neuron_tools.create_subtree_mask(np.array([]))
        
        # Test with multiple selections
        with pytest.raises(ValueError, match="Exactly one point must be selected"):
            self.neuron_tools.create_subtree_mask(np.array([0, 1]))
    
    @patch('tools.neuron_tools.nr.g_subtree_mask')
    @patch('tools.neuron_tools.n_pnt_coords')
    @patch('tools.neuron_tools.get_mask_node_ind')
    def test_create_subtree_mask_success(self, mock_get_mask, mock_n_pnt_coords, mock_g_subtree_mask):
        """Test successful subtree mask creation."""
        # Set up mocks
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        mock_n_pnt_coords.return_value = np.array([[0, 0, 0], [1, 1, 1]])
        mock_get_mask.return_value = np.array([3])  # Node index 3
        
        selected_indices = np.array([1])
        
        # Call create_subtree_mask
        self.neuron_tools.create_subtree_mask(selected_indices)
        
        # Verify g_subtree_mask was called with correct parameters
        mock_g_subtree_mask.assert_called_once_with(mock_neuron, 3)
    
    def test_get_neuron_info_no_neuron(self):
        """Test get_neuron_info with no neuron set."""
        info = self.neuron_tools.get_neuron_info()
        assert info["status"] == "No neuron loaded"
    
    @patch('tools.neuron_tools.nr.g_vert_coords')
    @patch('tools.neuron_tools.nr.g_root_ind')
    def test_get_neuron_info_with_neuron(self, mock_g_root_ind, mock_g_vert_coords):
        """Test get_neuron_info with neuron set."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        mock_g_vert_coords.return_value = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
        mock_g_root_ind.return_value = 0
        
        info = self.neuron_tools.get_neuron_info()
        
        assert info["status"] == "Loaded"
        assert info["num_vertices"] == 3
        assert info["root_index"] == 0
        assert "has_subtree_mask" in info
    
    @patch('tools.neuron_tools.nr.g_vert_coords')
    def test_get_neuron_info_error(self, mock_g_vert_coords):
        """Test get_neuron_info with error."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        mock_g_vert_coords.side_effect = Exception("Test error")
        
        info = self.neuron_tools.get_neuron_info()
        assert "Error: Test error" in info["status"]
    
    def test_validate_selection_for_reroot_no_neuron(self):
        """Test validate_selection_for_reroot with no neuron."""
        selected_indices = np.array([0])
        assert self.neuron_tools.validate_selection_for_reroot(selected_indices) is False
    
    def test_validate_selection_for_reroot_invalid_count(self):
        """Test validate_selection_for_reroot with invalid selection count."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        # No selection
        assert self.neuron_tools.validate_selection_for_reroot(np.array([])) is False
        
        # Multiple selections
        assert self.neuron_tools.validate_selection_for_reroot(np.array([0, 1])) is False
    
    def test_validate_selection_for_reroot_valid(self):
        """Test validate_selection_for_reroot with valid selection."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        selected_indices = np.array([0])
        assert self.neuron_tools.validate_selection_for_reroot(selected_indices) is True
    
    def test_validate_selection_for_subtree_no_neuron(self):
        """Test validate_selection_for_subtree with no neuron."""
        selected_indices = np.array([0])
        assert self.neuron_tools.validate_selection_for_subtree(selected_indices) is False
    
    def test_validate_selection_for_subtree_invalid_count(self):
        """Test validate_selection_for_subtree with invalid selection count."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        # No selection
        assert self.neuron_tools.validate_selection_for_subtree(np.array([])) is False
        
        # Multiple selections
        assert self.neuron_tools.validate_selection_for_subtree(np.array([0, 1])) is False
    
    def test_validate_selection_for_subtree_valid(self):
        """Test validate_selection_for_subtree with valid selection."""
        mock_neuron = Mock()
        self.neuron_tools.set_neuron(mock_neuron)
        
        selected_indices = np.array([0])
        assert self.neuron_tools.validate_selection_for_subtree(selected_indices) is True

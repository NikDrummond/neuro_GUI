"""Unit tests for the utils module."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from utils.helpers import (
    n_pnt_coords, make_pnts, get_mask_node_ind, 
    validate_csv_data, extract_coordinates_from_csv
)
from utils.logging_utils import QTextEditLogger, setup_logging


class TestHelpers:
    """Test helper functions."""
    
    def test_n_pnt_coords(self):
        """Test n_pnt_coords function."""
        # Mock neuron object
        mock_neuron = Mock()
        
        # Mock Neurosetta functions
        with patch('utils.helpers.nr') as mock_nr:
            mock_nr.g_vert_coords.return_value = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]])
            mock_nr.g_lb_inds.return_value = np.array([0, 2])
            
            result = n_pnt_coords(mock_neuron)
            
            # Should return coordinates at indices [0, 2]
            expected = np.array([[0, 0, 0], [2, 2, 2]])
            np.testing.assert_array_equal(result, expected)
    
    def test_make_pnts(self, sample_coordinates):
        """Test make_pnts function."""
        coords = sample_coordinates
        mask = np.array([True, False, True, False, False])
        
        with patch('utils.helpers.vd') as mock_vd:
            mock_vd.Points.return_value = Mock()
            
            selected, unselected = make_pnts(coords, mask)
            
            # Should create two Points objects
            assert mock_vd.Points.call_count == 2
            
            # Check that selected points are called with masked coordinates
            selected_coords = coords[mask]
            unselected_coords = coords[~mask]
            
            calls = mock_vd.Points.call_args_list
            np.testing.assert_array_equal(calls[0][0][0], selected_coords)
            np.testing.assert_array_equal(calls[1][0][0], unselected_coords)
    
    def test_get_mask_node_ind(self):
        """Test get_mask_node_ind function."""
        mock_neuron = Mock()
        mask = np.array([True, False, True])
        
        with patch('utils.helpers.nr') as mock_nr:
            mock_nr.g_lb_inds.return_value = np.array([10, 20, 30])
            
            result = get_mask_node_ind(mock_neuron, mask)
            
            # Should return indices where mask is True
            expected = np.array([10, 30])
            np.testing.assert_array_equal(result, expected)
    
    def test_validate_csv_data_valid(self, sample_csv_data):
        """Test validate_csv_data with valid data."""
        assert validate_csv_data(sample_csv_data) is True
    
    def test_validate_csv_data_missing_columns(self):
        """Test validate_csv_data with missing required columns."""
        # Missing 'z' column
        df = pd.DataFrame({'x': [1, 2], 'y': [3, 4]})
        assert validate_csv_data(df) is False
        
        # Missing 'x' column
        df = pd.DataFrame({'y': [1, 2], 'z': [3, 4]})
        assert validate_csv_data(df) is False
    
    def test_extract_coordinates_from_csv(self, sample_csv_data):
        """Test extract_coordinates_from_csv function."""
        result = extract_coordinates_from_csv(sample_csv_data)
        
        expected = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
            [2.0, 2.0, 2.0],
            [3.0, 3.0, 3.0],
            [4.0, 4.0, 4.0]
        ])
        
        np.testing.assert_array_equal(result, expected)


class TestLoggingUtils:
    """Test logging utilities."""
    
    def test_qtextedit_logger_initialization(self):
        """Test QTextEditLogger initialization."""
        mock_text_edit = Mock()
        logger = QTextEditLogger(mock_text_edit)
        
        assert logger.widget is mock_text_edit
        assert logger.formatter is not None
    
    def test_qtextedit_logger_emit(self):
        """Test QTextEditLogger emit method."""
        mock_text_edit = Mock()
        logger = QTextEditLogger(mock_text_edit)
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        with patch('utils.logging_utils.QTimer') as mock_timer:
            logger.emit(record)
            
            # Should call QTimer.singleShot
            mock_timer.singleShot.assert_called_once()
    
    def test_setup_logging_with_text_edit(self):
        """Test setup_logging with text edit widget."""
        mock_text_edit = Mock()
        
        with patch('utils.logging_utils.logging') as mock_logging:
            mock_logger = Mock()
            mock_logging.getLogger.return_value = mock_logger
            mock_logging.StreamHandler.return_value = Mock()
            mock_logging.Formatter.return_value = Mock()
            
            setup_logging(mock_text_edit)
            
            # Should add handlers to logger
            assert mock_logger.addHandler.call_count == 2  # QTextEdit + Console
            mock_logger.setLevel.assert_called_once()
    
    def test_setup_logging_without_text_edit(self):
        """Test setup_logging without text edit widget."""
        with patch('utils.logging_utils.logging') as mock_logging:
            mock_logger = Mock()
            mock_logging.getLogger.return_value = mock_logger
            mock_logging.StreamHandler.return_value = Mock()
            mock_logging.Formatter.return_value = Mock()
            
            setup_logging()
            
            # Should only add console handler
            assert mock_logger.addHandler.call_count == 1  # Console only
            mock_logger.setLevel.assert_called_once()

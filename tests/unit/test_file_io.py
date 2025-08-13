"""Unit tests for the file_io module."""

import pytest
import os
import tempfile
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
from file_io.file_manager import FileManager


class TestFileManager:
    """Test FileManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_manager = FileManager()
    
    def test_initialization(self):
        """Test FileManager initialization."""
        assert self.file_manager.supported_extensions == ['.nr', '.swc', '.csv']
        assert isinstance(self.file_manager.file_filters, dict)
    
    def test_get_file_filter_string(self):
        """Test get_file_filter_string method."""
        filter_string = self.file_manager.get_file_filter_string()
        assert 'CSV (*.csv)' in filter_string
        assert 'Neurosetta (*.nr)' in filter_string
        assert 'SWC (*.swc)' in filter_string
    
    def test_get_save_filter_string(self):
        """Test get_save_filter_string method."""
        filter_string = self.file_manager.get_save_filter_string()
        assert filter_string == 'Neurosetta (*.nr)'
    
    def test_is_supported_file_valid(self):
        """Test is_supported_file with valid extensions."""
        assert self.file_manager.is_supported_file('test.nr') is True
        assert self.file_manager.is_supported_file('test.swc') is True
        assert self.file_manager.is_supported_file('test.csv') is True
        assert self.file_manager.is_supported_file('/path/to/test.NR') is True  # Case insensitive
    
    def test_is_supported_file_invalid(self):
        """Test is_supported_file with invalid extensions."""
        assert self.file_manager.is_supported_file('test.txt') is False
        assert self.file_manager.is_supported_file('test.json') is False
        assert self.file_manager.is_supported_file('test') is False
    
    def test_scan_folder_for_files(self, tmp_path):
        """Test scan_folder_for_files method."""
        # Create test files
        (tmp_path / "neuron1.nr").touch()
        (tmp_path / "neuron2.swc").touch()
        (tmp_path / "data.csv").touch()  # Should be excluded
        (tmp_path / "other.txt").touch()  # Should be excluded
        
        files = self.file_manager.scan_folder_for_files(str(tmp_path))
        
        # Should only include .nr and .swc files
        assert len(files) == 2
        assert any('neuron1.nr' in f for f in files)
        assert any('neuron2.swc' in f for f in files)
        assert not any('data.csv' in f for f in files)
        assert not any('other.txt' in f for f in files)
    
    def test_load_file_not_found(self):
        """Test load_file with non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.file_manager.load_file('nonexistent.nr')
    
    def test_load_file_unsupported_format(self, tmp_path):
        """Test load_file with unsupported file format."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("some content")
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            self.file_manager.load_file(str(test_file))
    
    def test_load_csv_valid(self, tmp_path):
        """Test loading valid CSV file."""
        # Create valid CSV file
        csv_file = tmp_path / "test.csv"
        csv_content = "x,y,z\n0,0,0\n1,1,1\n2,2,2\n"
        csv_file.write_text(csv_content)
        
        neuron, vertex_coords, point_coords = self.file_manager.load_file(str(csv_file))
        
        assert neuron is None  # CSV doesn't create neuron object
        assert point_coords is None  # CSV doesn't have point coords
        assert isinstance(vertex_coords, np.ndarray)
        assert vertex_coords.shape == (3, 3)  # 3 points, 3 coordinates each
    
    def test_load_csv_invalid_columns(self, tmp_path):
        """Test loading CSV file with missing required columns."""
        # Create CSV file missing 'z' column
        csv_file = tmp_path / "test.csv"
        csv_content = "x,y\n0,0\n1,1\n"
        csv_file.write_text(csv_content)
        
        with pytest.raises(ValueError, match="CSV file must contain columns"):
            self.file_manager.load_file(str(csv_file))
    
    @patch('src.file_io.file_manager.nr.load')
    @patch('src.file_io.file_manager.nr.g_vert_coords')
    def test_load_neuron_file(self, mock_g_vert_coords, mock_nr_load, tmp_path):
        """Test loading neuron file (.nr or .swc)."""
        # Create test file
        neuron_file = tmp_path / "test.nr"
        neuron_file.write_text("dummy neuron data")
        
        # Mock Neurosetta functions
        mock_neuron = Mock()
        mock_nr_load.return_value = mock_neuron
        mock_g_vert_coords.return_value = [[0, 0, 0], [1, 1, 1]]
        
        with patch('src.utils.helpers.n_pnt_coords') as mock_n_pnt_coords:
            mock_n_pnt_coords.return_value = np.array([[0, 0, 0], [1, 1, 1]])
            
            neuron, vertex_coords, point_coords = self.file_manager.load_file(str(neuron_file))
            
            assert neuron is mock_neuron
            assert isinstance(vertex_coords, np.ndarray)
            assert isinstance(point_coords, np.ndarray)
            mock_nr_load.assert_called_once_with(str(neuron_file))
    
    def test_save_neuron_none(self):
        """Test saving None neuron raises error."""
        with pytest.raises(ValueError, match="Cannot save: neuron object is None"):
            self.file_manager.save_neuron(None, "test.nr")
    
    @patch('file_io.file_manager.nr.save')
    def test_save_neuron_success(self, mock_nr_save):
        """Test successful neuron saving."""
        mock_neuron = Mock()
        filepath = "test.nr"
        
        self.file_manager.save_neuron(mock_neuron, filepath)
        
        mock_nr_save.assert_called_once_with(mock_neuron, filepath)
    
    @patch('file_io.file_manager.nr.save')
    def test_save_neuron_failure(self, mock_nr_save):
        """Test neuron saving failure."""
        mock_neuron = Mock()
        mock_nr_save.side_effect = Exception("Save failed")
        
        with pytest.raises(Exception, match="Save failed"):
            self.file_manager.save_neuron(mock_neuron, "test.nr")
    
    def test_save_neuron_to_directory_none(self):
        """Test saving None neuron to directory raises error."""
        with pytest.raises(ValueError, match="Cannot save: neuron object is None"):
            self.file_manager.save_neuron_to_directory(None, "/tmp")
    
    @patch('file_io.file_manager.nr.save')
    def test_save_neuron_to_directory_success(self, mock_nr_save):
        """Test successful neuron saving to directory."""
        mock_neuron = Mock()
        directory = "/tmp/test"
        
        self.file_manager.save_neuron_to_directory(mock_neuron, directory)
        
        # Should append '/' if not present
        mock_nr_save.assert_called_once_with(mock_neuron, directory + '/')
    
    @patch('file_io.file_manager.nr.save')
    def test_save_neuron_to_directory_with_slash(self, mock_nr_save):
        """Test neuron saving to directory that already ends with slash."""
        mock_neuron = Mock()
        directory = "/tmp/test/"
        
        self.file_manager.save_neuron_to_directory(mock_neuron, directory)
        
        # Should not add extra slash
        mock_nr_save.assert_called_once_with(mock_neuron, directory)
    
    def test_get_directory_from_path(self):
        """Test get_directory_from_path method."""
        filepath = "/home/user/data/neuron.nr"
        directory = self.file_manager.get_directory_from_path(filepath)
        assert directory == "/home/user/data"
        
        # Test with relative path
        filepath = "data/neuron.nr"
        directory = self.file_manager.get_directory_from_path(filepath)
        assert directory == "data"

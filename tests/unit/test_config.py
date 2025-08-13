"""Unit tests for the config module."""

import pytest
import os
from unittest.mock import patch
from config.settings import AppSettings
from config.constants import (
    UI_CONSTANTS, RENDERING_CONSTANTS, FILE_CONSTANTS, 
    SCALE_CONSTANTS, ENV_CONFIG, LOGGING_CONFIG
)


class TestConstants:
    """Test configuration constants."""
    
    def test_ui_constants_structure(self):
        """Test UI constants have expected keys and types."""
        assert isinstance(UI_CONSTANTS, dict)
        assert 'WINDOW_TITLE' in UI_CONSTANTS
        assert 'SIDE_PANEL_WIDTH' in UI_CONSTANTS
        assert isinstance(UI_CONSTANTS['SIDE_PANEL_WIDTH'], int)
        assert UI_CONSTANTS['SIDE_PANEL_WIDTH'] > 0
    
    def test_rendering_constants_structure(self):
        """Test rendering constants have expected keys and types."""
        assert isinstance(RENDERING_CONSTANTS, dict)
        assert 'BACKGROUND_COLOR' in RENDERING_CONSTANTS
        assert 'DEFAULT_NEURON_COLOR' in RENDERING_CONSTANTS
        assert 'SOMA_RADIUS' in RENDERING_CONSTANTS
        assert isinstance(RENDERING_CONSTANTS['SOMA_RADIUS'], int)
    
    def test_file_constants_structure(self):
        """Test file constants have expected keys and types."""
        assert isinstance(FILE_CONSTANTS, dict)
        assert 'SUPPORTED_EXTENSIONS' in FILE_CONSTANTS
        assert 'FILE_FILTERS' in FILE_CONSTANTS
        assert 'REQUIRED_CSV_COLUMNS' in FILE_CONSTANTS
        
        # Test supported extensions
        extensions = FILE_CONSTANTS['SUPPORTED_EXTENSIONS']
        assert '.nr' in extensions
        assert '.swc' in extensions
        assert '.csv' in extensions
        
        # Test required CSV columns
        csv_cols = FILE_CONSTANTS['REQUIRED_CSV_COLUMNS']
        assert 'x' in csv_cols
        assert 'y' in csv_cols
        assert 'z' in csv_cols
    
    def test_scale_constants_structure(self):
        """Test scale constants have expected keys and types."""
        assert isinstance(SCALE_CONSTANTS, dict)
        assert 'DEFAULT_SCALE_LENGTH_NM' in SCALE_CONSTANTS
        assert 'UNITS' in SCALE_CONSTANTS
        assert 'CONVERSION_FACTOR' in SCALE_CONSTANTS
        assert isinstance(SCALE_CONSTANTS['DEFAULT_SCALE_LENGTH_NM'], int)
        assert SCALE_CONSTANTS['CONVERSION_FACTOR'] == 1000


class TestAppSettings:
    """Test AppSettings class."""
    
    def test_initialization(self):
        """Test AppSettings initialization."""
        settings = AppSettings()
        assert settings.scale_length_nm == SCALE_CONSTANTS['DEFAULT_SCALE_LENGTH_NM']
        assert settings.units == 'nm'
        assert settings.window_title == UI_CONSTANTS['WINDOW_TITLE']
    
    @patch.dict(os.environ, {}, clear=True)
    def test_environment_setup(self):
        """Test environment variable setup."""
        settings = AppSettings()
        
        # Check that environment variables are set
        for key, value in ENV_CONFIG.items():
            if key == 'LD_LIBRARY_PATH':
                assert value in os.environ.get(key, '')
            else:
                assert os.environ.get(key) == value
    
    def test_set_units_valid(self):
        """Test setting valid units."""
        settings = AppSettings()
        
        settings.set_units('nm')
        assert settings.units == 'nm'
        
        settings.set_units('µm')
        assert settings.units == 'µm'
    
    def test_set_units_invalid(self):
        """Test setting invalid units raises error."""
        settings = AppSettings()
        
        with pytest.raises(ValueError, match="Unsupported units"):
            settings.set_units('invalid')
    
    def test_set_scale_length_nm(self):
        """Test setting scale length in nanometers."""
        settings = AppSettings()
        
        settings.set_scale_length(1000, 'nm')
        assert settings.scale_length_nm == 1000
    
    def test_set_scale_length_um(self):
        """Test setting scale length in micrometers."""
        settings = AppSettings()
        
        settings.set_scale_length(5, 'µm')
        assert settings.scale_length_nm == 5000
    
    def test_set_scale_length_invalid_units(self):
        """Test setting scale length with invalid units."""
        settings = AppSettings()
        
        with pytest.raises(ValueError, match="Unsupported units"):
            settings.set_scale_length(1000, 'invalid')
    
    def test_get_scale_length_nm(self):
        """Test getting scale length in nanometers."""
        settings = AppSettings()
        settings.scale_length_nm = 2000
        
        length = settings.get_scale_length('nm')
        assert length == 2000
    
    def test_get_scale_length_um(self):
        """Test getting scale length in micrometers."""
        settings = AppSettings()
        settings.scale_length_nm = 3000
        
        length = settings.get_scale_length('µm')
        assert length == 3
    
    def test_get_scale_length_current_units(self):
        """Test getting scale length in current units."""
        settings = AppSettings()
        settings.units = 'µm'
        settings.scale_length_nm = 4000
        
        length = settings.get_scale_length()
        assert length == 4
    
    def test_get_scale_display_text(self):
        """Test getting formatted scale display text."""
        settings = AppSettings()
        settings.units = 'nm'
        settings.scale_length_nm = 5000
        
        text = settings.get_scale_display_text()
        assert text == "5000 nm"
        
        settings.units = 'µm'
        text = settings.get_scale_display_text()
        assert text == "5 µm"

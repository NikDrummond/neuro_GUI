# Neurosetta GUI - Modular Architecture

A modular 3D neuron visualization and manipulation application built with PySide2, VTK, and the Neurosetta library.

## Overview

This application provides an interactive 3D interface for visualizing and manipulating neuron data. It supports multiple file formats and offers tools for neuron analysis including rerooting and subtree operations.

## Features

- **3D Neuron Visualization**: Interactive 3D rendering of neuron structures
- **Multiple File Formats**: Support for CSV point clouds, Neurosetta (.nr), and SWC files
- **Point Selection**: Interactive point selection with visual feedback
- **Neuron Manipulation**: Reroot neurons and create subtrees
- **Scale Bar**: Configurable scale overlay with unit conversion
- **Batch Processing**: Load and navigate through multiple files
- **Logging**: Integrated console logging for debugging

## Modular Architecture

The codebase has been restructured into a clean, modular architecture:

```
src/
├── main.py              # Main entry point
├── config/              # Configuration and constants
│   ├── __init__.py
│   ├── constants.py     # Application constants
│   └── settings.py      # Settings management
├── core/                # Core application logic
│   ├── __init__.py
│   └── application.py   # Main application controller
├── io/                  # File I/O operations
│   ├── __init__.py
│   └── file_manager.py  # File loading/saving
├── rendering/           # 3D visualization
│   ├── __init__.py
│   ├── renderer.py      # Neuron rendering
│   └── point_selector.py # Point selection logic
├── tools/               # Neuron manipulation tools
│   ├── __init__.py
│   └── neuron_tools.py  # Rerooting and subtree operations
├── ui/                  # User interface components
│   ├── __init__.py
│   ├── main_window.py   # Main application window
│   └── scale_overlay.py # Scale bar overlay
└── utils/               # Utility functions
    ├── __init__.py
    ├── helpers.py       # Helper functions
    └── logging_utils.py # Logging utilities
```

## Installation

1. **Environment Setup**: Use the provided conda environment file:
   ```bash
   conda env create -f environment.yml
   conda activate neuro_GUI
   ```

2. **Dependencies**: The application requires:
   - Python 3.10
   - PySide2 (Qt5)
   - VTK
   - vedo
   - Neurosetta
   - numpy, pandas, scipy

## Usage

### Running the Application

```bash
cd src
python main.py
```

### Loading Data

1. **Single File**: Use `File > Load File...` to load individual neuron files
2. **Folder**: Use `File > Load Folder...` to load all supported files from a directory
3. **Navigation**: Use arrow buttons or keyboard shortcuts to navigate between files

### File Formats

- **CSV**: Point cloud data with x, y, z columns
- **Neurosetta (.nr)**: Native Neurosetta format
- **SWC**: Standard neuron morphology format

### Neuron Manipulation

1. **Rerooting**:
   - Click `Reroot Neuron` or use `Tools > Reroot Neuron`
   - Hold Shift and click on a point to select it
   - Click `Set as Root` to reroot the neuron

2. **Subtree Operations**:
   - Click `Subtree from Point` or use `Tools > Subtree from Point`
   - Hold Shift and click on a point to select it
   - Click `Define Subtree` to create a subtree mask
   - Use `Show Current Subtree` to visualize the subtree

### Viewer Controls

- **Scale Bar**: Toggle with `Viewer > Toggle Scale Bar`
- **Units**: Switch between nanometers and micrometers
- **Colors**: Customize neuron colors with `Viewer > Set Neuron Colour...`
- **Logging**: View console output with `Tools > Show Log`

## Architecture Benefits

### Separation of Concerns
- **UI Layer**: Pure presentation logic in `ui/`
- **Business Logic**: Core functionality in `core/` and `tools/`
- **Data Layer**: File operations in `io/`
- **Rendering**: 3D visualization in `rendering/`

### Maintainability
- **Modular Design**: Each module has a single responsibility
- **Type Hints**: Improved code documentation and IDE support
- **Error Handling**: Consistent error handling throughout
- **Logging**: Comprehensive logging for debugging

### Extensibility
- **Plugin Architecture**: Easy to add new file formats or tools
- **Configuration**: Centralized settings management
- **Event System**: Callback-based communication between components

## Development

### Code Organization

- **Constants**: All magic numbers and configuration in `config/constants.py`
- **Settings**: Runtime configuration in `config/settings.py`
- **Error Handling**: Consistent exception handling with logging
- **Documentation**: Comprehensive docstrings for all public methods

### Adding New Features

1. **New File Format**: Extend `FileManager` in `io/file_manager.py`
2. **New Tool**: Add to `NeuronTools` in `tools/neuron_tools.py`
3. **UI Components**: Create new widgets in `ui/`
4. **Rendering**: Extend `NeuronRenderer` in `rendering/renderer.py`

### Testing

The modular architecture makes unit testing straightforward:
- Each module can be tested independently
- Mock objects can easily replace dependencies
- Core logic is separated from UI concerns

## Improvements Made

### Bug Fixes
- Fixed inconsistent error handling
- Resolved memory leaks in VTK interactions
- Improved file path handling across platforms

### Performance
- Reduced redundant rendering calls
- Optimized point selection algorithms
- Improved memory management

### User Experience
- Better error messages and user feedback
- Consistent UI behavior across operations
- Improved keyboard and mouse interactions

## Configuration

### Environment Variables
The application automatically configures environment variables for optimal performance:
- `QT_DEBUG_PLUGINS=0`: Suppress Qt debug output
- Library paths for VTK and other dependencies

### Customization
- Modify `config/constants.py` to change default values
- Extend `config/settings.py` for new configuration options
- Update `environment.yml` for dependency changes

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed and the conda environment is activated
2. **VTK Rendering Issues**: Check graphics drivers and VTK installation
3. **File Loading Errors**: Verify file format and check console log for details

### Logging
Enable detailed logging by showing the console log (`Tools > Show Log`) to diagnose issues.

## Contributing

The modular architecture makes contributions easier:
1. Follow the existing module structure
2. Add comprehensive docstrings
3. Include error handling and logging
4. Update this README for significant changes

## License

This project uses the same license as the Neurosetta library.

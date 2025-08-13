# Neurosetta GUI Test Suite

This directory contains comprehensive unit and integration tests for the modular Neurosetta GUI application.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── requirements.txt         # Testing dependencies
├── unit/                    # Unit tests for individual modules
│   ├── test_config.py       # Configuration module tests
│   ├── test_utils.py        # Utility functions tests
│   ├── test_file_io.py      # File I/O operations tests
│   ├── test_tools.py        # Neuron manipulation tools tests
│   ├── test_rendering.py    # Rendering components tests
│   └── test_core.py         # Core application logic tests
├── integration/             # Integration tests
│   └── test_integration.py  # Cross-module integration tests
└── fixtures/                # Test data and fixtures
```

## Running Tests

### Prerequisites

1. **Install test dependencies:**
   ```bash
   conda activate neurosetta
   pip install -r tests/requirements.txt
   ```

2. **Ensure the modular application works:**
   ```bash
   cd src && python main.py
   ```

### Test Execution

#### Using the Test Runner (Recommended)

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --type unit

# Run only integration tests
python run_tests.py --type integration

# Run with coverage report
python run_tests.py --coverage

# Run with verbose output
python run_tests.py --verbose
```

#### Using pytest directly

```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/ -m unit

# Run integration tests only
pytest tests/integration/ -m integration

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py -v
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual modules in isolation with mocked dependencies:

- **Config Tests**: Settings management, constants validation, environment setup
- **Utils Tests**: Helper functions, logging utilities, data validation
- **File I/O Tests**: File loading/saving, format detection, error handling
- **Tools Tests**: Neuron manipulation, rerooting, subtree operations
- **Rendering Tests**: 3D visualization, point selection, camera controls
- **Core Tests**: Application coordination, workflow management

### Integration Tests (`tests/integration/`)

Test cross-module interactions and complete workflows:

- **File Loading Workflow**: End-to-end file loading and processing
- **Neuron Manipulation Workflow**: Complete rerooting and subtree operations
- **Configuration Integration**: Settings and environment coordination
- **Rendering Integration**: Visualization pipeline testing

## Test Fixtures

### Shared Fixtures (`conftest.py`)

- `mock_gui_components`: Mocks VTK and Qt components for headless testing
- `sample_coordinates`: Standard 3D coordinate arrays for testing
- `sample_csv_data`: Valid CSV data for file I/O tests
- `mock_neuron`: Mock Neurosetta neuron objects
- `temp_test_file`: Temporary files for file operations
- `mock_plotter`: Mock vedo plotter for rendering tests
- `mock_picker`: Mock VTK picker for interaction tests

### Custom Fixtures

Each test module can define additional fixtures specific to its testing needs.

## Test Coverage

The test suite aims for comprehensive coverage of:

- ✅ **Configuration Management** (95%+ coverage)
- ✅ **Utility Functions** (90%+ coverage)
- ✅ **File I/O Operations** (85%+ coverage)
- ✅ **Neuron Tools** (90%+ coverage)
- ✅ **Rendering Logic** (80%+ coverage)
- ✅ **Core Application** (85%+ coverage)
- ✅ **Integration Workflows** (75%+ coverage)

## Mocking Strategy

### GUI Components
- VTK components are mocked to avoid graphics dependencies
- Qt widgets are mocked for headless testing
- vedo objects are mocked to isolate rendering logic

### External Dependencies
- Neurosetta library calls are mocked with realistic return values
- File system operations use temporary directories
- Network operations (if any) are mocked

### Internal Dependencies
- Cross-module dependencies are mocked to ensure isolation
- Callbacks and event handlers are tested with mock functions

## Test Data

### Sample Data
- **Coordinates**: Standard 3D point arrays for geometry testing
- **CSV Files**: Valid and invalid CSV data for file format testing
- **Neuron Data**: Mock neuron structures for manipulation testing

### Temporary Files
- Tests create temporary files in system temp directories
- All temporary files are automatically cleaned up after tests

## Continuous Integration

The test suite is designed to run in CI environments:

- **Headless Operation**: All GUI components are mocked
- **No External Dependencies**: Tests don't require graphics or network
- **Fast Execution**: Unit tests complete in seconds
- **Deterministic Results**: No random or time-dependent behavior

## Writing New Tests

### Unit Test Guidelines

1. **Test one thing**: Each test should verify a single behavior
2. **Use descriptive names**: Test names should explain what is being tested
3. **Mock dependencies**: Isolate the unit under test
4. **Test edge cases**: Include error conditions and boundary values
5. **Keep tests fast**: Unit tests should run in milliseconds

### Integration Test Guidelines

1. **Test workflows**: Verify complete user workflows work correctly
2. **Minimal mocking**: Only mock external systems, not internal modules
3. **Real data**: Use realistic test data when possible
4. **Mark as slow**: Use `@pytest.mark.slow` for longer-running tests

### Example Test Structure

```python
class TestModuleName:
    """Test ModuleName class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.subject = ModuleName()
    
    def test_method_success(self):
        """Test successful method execution."""
        result = self.subject.method(valid_input)
        assert result == expected_output
    
    def test_method_failure(self):
        """Test method failure handling."""
        with pytest.raises(ExpectedException):
            self.subject.method(invalid_input)
```

## Debugging Tests

### Running Individual Tests
```bash
# Run single test method
pytest tests/unit/test_config.py::TestAppSettings::test_set_units_valid -v

# Run with debugging output
pytest tests/unit/test_config.py -v -s

# Run with Python debugger
pytest tests/unit/test_config.py --pdb
```

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes the `src` directory
2. **Mock Failures**: Check that all external dependencies are properly mocked
3. **Fixture Issues**: Verify fixture scope and dependencies
4. **Path Issues**: Use absolute paths or proper relative path handling

## Contributing

When adding new features to the application:

1. **Write tests first**: Follow TDD principles where possible
2. **Maintain coverage**: Ensure new code is adequately tested
3. **Update fixtures**: Add new test data as needed
4. **Document tests**: Include docstrings explaining test purpose
5. **Run full suite**: Verify all tests pass before submitting changes

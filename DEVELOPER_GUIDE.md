# Neurosetta GUI Developer Guide

## Adding GUI Elements: Step-by-Step Instructions

This guide provides clear, step-by-step instructions for adding new GUI elements to the modular Neurosetta GUI application. Follow these instructions to maintain consistency with the existing architecture.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Adding Simple UI Elements](#adding-simple-ui-elements)
3. [Adding Complex UI Components](#adding-complex-ui-components)
4. [Adding Menu Items](#adding-menu-items)
5. [Adding Tool Buttons](#adding-tool-buttons)
6. [Adding Configuration Options](#adding-configuration-options)
7. [Adding Event Handlers](#adding-event-handlers)
8. [Testing Your Changes](#testing-your-changes)
9. [Best Practices](#best-practices)
10. [Common Patterns](#common-patterns)

---

## Architecture Overview

The modular GUI follows this structure:

```
src/
├── ui/
│   ├── main_window.py      # Main window and layout
│   ├── scale_overlay.py    # Scale bar overlay
│   └── __init__.py
├── core/
│   └── application.py      # Business logic coordination
├── config/
│   ├── constants.py        # UI constants and settings
│   └── settings.py         # Application settings
└── [other modules...]
```

**Key Principle**: UI code goes in `ui/`, business logic goes in `core/`, constants go in `config/`.

---

## Adding Simple UI Elements

### Step 1: Define UI Constants

Add any new constants to `src/config/constants.py`:

```python
# In UI_CONSTANTS dictionary
UI_CONSTANTS = {
    # ... existing constants ...
    'NEW_BUTTON_TEXT': 'My New Button',
    'NEW_WIDGET_SIZE': (200, 30),
    'NEW_TOOLTIP': 'This is my new button tooltip',
}
```

### Step 2: Add UI Element to Main Window

Edit `src/ui/main_window.py` in the `setup_ui()` method:

```python
def setup_ui(self):
    # ... existing setup code ...
    
    # Add your new UI element
    self.my_new_button = QPushButton(UI_CONSTANTS['NEW_BUTTON_TEXT'])
    self.my_new_button.setToolTip(UI_CONSTANTS['NEW_TOOLTIP'])
    self.my_new_button.clicked.connect(self.handle_my_new_button)
    
    # Add to appropriate layout
    self.side_layout.addWidget(self.my_new_button)
```

### Step 3: Add Event Handler

Add the event handler method in `src/ui/main_window.py`:

```python
def handle_my_new_button(self):
    """Handle my new button click."""
    try:
        # Delegate to core application logic
        result = self.app.perform_my_new_action()
        if result:
            self.show_status_message("Action completed successfully")
        else:
            self.show_status_message("Action failed", error=True)
    except Exception as e:
        self.logger.error(f"Error in my new button handler: {e}")
        self.show_status_message(f"Error: {e}", error=True)
```

### Step 4: Add Business Logic

Add the actual functionality to `src/core/application.py`:

```python
def perform_my_new_action(self) -> bool:
    """Perform the new action logic.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Implement your business logic here
        self.logger.info("Performing new action")
        
        # Example: interact with other components
        if self.current_neuron is None:
            self.logger.warning("No neuron loaded")
            return False
        
        # Your logic here...
        
        return True
    except Exception as e:
        self.logger.error(f"Error performing new action: {e}")
        return False
```

---

## Adding Complex UI Components

### Step 1: Create New UI Component File

Create `src/ui/my_new_widget.py`:

```python
"""My new custom widget."""

from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide2.QtCore import Signal
from config import UI_CONSTANTS


class MyNewWidget(QWidget):
    """Custom widget for specific functionality."""
    
    # Define signals for communication
    action_triggered = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        
        # Add components
        self.label = QLabel("My New Widget")
        self.button = QPushButton("Action")
        
        layout.addWidget(self.label)
        layout.addWidget(self.button)
    
    def connect_signals(self):
        """Connect internal signals."""
        self.button.clicked.connect(self.handle_button_click)
    
    def handle_button_click(self):
        """Handle button click."""
        self.action_triggered.emit("button_clicked")
    
    def update_display(self, data):
        """Update widget with new data."""
        self.label.setText(f"Data: {data}")
```

### Step 2: Update UI Module Init

Add to `src/ui/__init__.py`:

```python
from .main_window import MainWindow
from .scale_overlay import ScaleOverlay
from .my_new_widget import MyNewWidget  # Add this line

__all__ = ['MainWindow', 'ScaleOverlay', 'MyNewWidget']
```

### Step 3: Integrate into Main Window

In `src/ui/main_window.py`:

```python
from .my_new_widget import MyNewWidget

class MainWindow(QMainWindow):
    def setup_ui(self):
        # ... existing setup ...
        
        # Add new widget
        self.my_new_widget = MyNewWidget()
        self.my_new_widget.action_triggered.connect(self.handle_widget_action)
        
        # Add to layout
        self.side_layout.addWidget(self.my_new_widget)
    
    def handle_widget_action(self, action_type):
        """Handle action from custom widget."""
        if action_type == "button_clicked":
            self.app.perform_widget_action()
```

---

## Adding Menu Items

### Step 1: Add Menu Constants

In `src/config/constants.py`:

```python
UI_CONSTANTS = {
    # ... existing constants ...
    'MENU_MY_ACTION': 'My New Action',
    'MENU_MY_ACTION_SHORTCUT': 'Ctrl+M',
    'MENU_MY_ACTION_TOOLTIP': 'Perform my new action',
}
```

### Step 2: Add Menu Item

In `src/ui/main_window.py`, modify `setup_menus()`:

```python
def setup_menus(self):
    # ... existing menu setup ...
    
    # Add to Tools menu (or create new menu)
    tools_menu = self.menuBar().addMenu('Tools')
    
    # Create action
    my_action = QAction(UI_CONSTANTS['MENU_MY_ACTION'], self)
    my_action.setShortcut(UI_CONSTANTS['MENU_MY_ACTION_SHORTCUT'])
    my_action.setStatusTip(UI_CONSTANTS['MENU_MY_ACTION_TOOLTIP'])
    my_action.triggered.connect(self.handle_my_menu_action)
    
    # Add to menu
    tools_menu.addAction(my_action)
```

### Step 3: Add Menu Handler

```python
def handle_my_menu_action(self):
    """Handle menu action."""
    try:
        result = self.app.perform_menu_action()
        if result:
            self.show_status_message("Menu action completed")
    except Exception as e:
        self.logger.error(f"Menu action error: {e}")
        self.show_status_message(f"Error: {e}", error=True)
```

---

## Adding Tool Buttons

### Step 1: Add Button to Tools Section

In `src/ui/main_window.py`, modify the tools section setup:

```python
def setup_ui(self):
    # ... existing setup ...
    
    # In the tools section
    tools_label = QLabel('Tools:')
    tools_label.setStyleSheet('font-weight: bold;')
    self.side_layout.addWidget(tools_label)
    
    # Add your new tool button
    self.my_tool_btn = QPushButton('My Tool')
    self.my_tool_btn.setToolTip('Description of what this tool does')
    self.my_tool_btn.clicked.connect(self.handle_my_tool)
    self.side_layout.addWidget(self.my_tool_btn)
```

### Step 2: Add Tool Logic

In `src/core/application.py`:

```python
def perform_my_tool_action(self) -> bool:
    """Perform tool-specific action.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check prerequisites
        if not self.current_neuron:
            self.logger.warning("No neuron loaded for tool")
            return False
        
        # Perform tool action
        # Example: interact with neuron_tools
        result = self.neuron_tools.perform_custom_operation(
            self.current_neuron, 
            self.point_selector.get_selected_indices()
        )
        
        if result:
            # Update visualization
            self.renderer.update_display()
            self.logger.info("Tool action completed")
            return True
        
        return False
    except Exception as e:
        self.logger.error(f"Tool action failed: {e}")
        return False
```

---

## Adding Configuration Options

### Step 1: Add Configuration Constants

In `src/config/constants.py`:

```python
# Add new configuration section
MY_FEATURE_CONFIG = {
    'DEFAULT_VALUE': 10,
    'MIN_VALUE': 1,
    'MAX_VALUE': 100,
    'ENABLED_BY_DEFAULT': True,
}
```

### Step 2: Add to Settings

In `src/config/settings.py`:

```python
class AppSettings:
    def __init__(self):
        # ... existing settings ...
        self.my_feature_value = MY_FEATURE_CONFIG['DEFAULT_VALUE']
        self.my_feature_enabled = MY_FEATURE_CONFIG['ENABLED_BY_DEFAULT']
    
    def set_my_feature_value(self, value: int) -> bool:
        """Set my feature value with validation."""
        if MY_FEATURE_CONFIG['MIN_VALUE'] <= value <= MY_FEATURE_CONFIG['MAX_VALUE']:
            self.my_feature_value = value
            return True
        return False
```

### Step 3: Add UI Controls

In `src/ui/main_window.py`:

```python
def setup_ui(self):
    # ... existing setup ...
    
    # Add configuration controls
    config_label = QLabel('Configuration:')
    config_label.setStyleSheet('font-weight: bold;')
    self.side_layout.addWidget(config_label)
    
    # Add slider/spinbox for value
    self.my_feature_slider = QSlider(Qt.Horizontal)
    self.my_feature_slider.setRange(
        MY_FEATURE_CONFIG['MIN_VALUE'], 
        MY_FEATURE_CONFIG['MAX_VALUE']
    )
    self.my_feature_slider.setValue(self.app.settings.my_feature_value)
    self.my_feature_slider.valueChanged.connect(self.handle_feature_value_change)
    self.side_layout.addWidget(self.my_feature_slider)
    
    # Add checkbox for enable/disable
    self.my_feature_checkbox = QCheckBox('Enable My Feature')
    self.my_feature_checkbox.setChecked(self.app.settings.my_feature_enabled)
    self.my_feature_checkbox.toggled.connect(self.handle_feature_toggle)
    self.side_layout.addWidget(self.my_feature_checkbox)

def handle_feature_value_change(self, value):
    """Handle feature value change."""
    if self.app.settings.set_my_feature_value(value):
        self.show_status_message(f"Feature value set to {value}")

def handle_feature_toggle(self, enabled):
    """Handle feature enable/disable."""
    self.app.settings.my_feature_enabled = enabled
    self.show_status_message(f"Feature {'enabled' if enabled else 'disabled'}")
```

---

## Adding Event Handlers

### Standard Event Handler Pattern

```python
def handle_my_event(self):
    """Handle my custom event.
    
    Standard pattern for event handlers:
    1. Validate state
    2. Delegate to core application
    3. Update UI based on result
    4. Handle errors gracefully
    """
    try:
        # 1. Validate state
        if not self.validate_state_for_action():
            self.show_status_message("Invalid state for action", error=True)
            return
        
        # 2. Delegate to core application
        result = self.app.perform_action()
        
        # 3. Update UI based on result
        if result:
            self.update_ui_after_success()
            self.show_status_message("Action completed successfully")
        else:
            self.show_status_message("Action failed", error=True)
    
    except Exception as e:
        # 4. Handle errors gracefully
        self.logger.error(f"Error in event handler: {e}")
        self.show_status_message(f"Error: {e}", error=True)

def validate_state_for_action(self) -> bool:
    """Validate that the application state allows the action."""
    # Example validations
    if not self.app.current_neuron:
        return False
    if not self.app.point_selector.is_active:
        return False
    return True

def update_ui_after_success(self):
    """Update UI elements after successful action."""
    # Update displays, refresh views, etc.
    self.update_file_info()
    self.refresh_3d_view()
```

---

## Testing Your Changes

### Step 1: Manual Testing

1. **Start the application:**
   ```bash
   cd src && python main.py
   ```

2. **Test your new element:**
   - Verify it appears correctly
   - Test all interactions
   - Check error handling
   - Verify tooltips and status messages

### Step 2: Add Unit Tests

Create test file `tests/unit/test_my_feature.py`:

```python
"""Tests for my new feature."""

import pytest
from unittest.mock import Mock, patch
from ui.main_window import MainWindow
from core.application import NeuroGUIApplication


class TestMyFeature:
    """Test my new feature."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_plotter = Mock()
        self.mock_picker = Mock()
        
        with patch('src.ui.main_window.QApplication'):
            self.window = MainWindow()
            self.window.app = Mock(spec=NeuroGUIApplication)
    
    def test_my_button_click(self):
        """Test my button click handler."""
        # Setup
        self.window.app.perform_my_new_action.return_value = True
        
        # Execute
        self.window.handle_my_new_button()
        
        # Verify
        self.window.app.perform_my_new_action.assert_called_once()
    
    def test_my_button_error_handling(self):
        """Test error handling in button click."""
        # Setup
        self.window.app.perform_my_new_action.side_effect = Exception("Test error")
        
        # Execute (should not raise)
        self.window.handle_my_new_button()
        
        # Verify error was logged
        # (Add assertions based on your logging setup)
```

### Step 3: Run Tests

```bash
# Run your specific tests
python -m pytest tests/unit/test_my_feature.py -v

# Run all tests to ensure no regressions
python run_tests.py
```

---

## Best Practices

### 1. Separation of Concerns

- **UI code** (`src/ui/`): Only handle display and user interaction
- **Business logic** (`src/core/`): Handle application logic and coordination
- **Constants** (`src/config/`): Define all UI strings, sizes, and configuration

### 2. Error Handling

Always wrap event handlers in try-catch blocks:

```python
def handle_action(self):
    """Handle action with proper error handling."""
    try:
        # Your code here
        pass
    except Exception as e:
        self.logger.error(f"Error in action handler: {e}")
        self.show_status_message(f"Error: {e}", error=True)
```

### 3. Logging

Use the application logger for all significant events:

```python
# In UI handlers
self.logger.info("User performed action X")
self.logger.warning("Invalid state for action")
self.logger.error(f"Error occurred: {e}")

# In core application
self.logger.debug("Detailed debug information")
self.logger.info("Action completed successfully")
```

### 4. User Feedback

Always provide user feedback:

```python
# Success feedback
self.show_status_message("Action completed successfully")

# Error feedback
self.show_status_message("Action failed", error=True)

# Progress feedback for long operations
self.show_status_message("Processing...")
```

### 5. Constants Usage

Never hardcode strings or values:

```python
# ❌ Bad
button.setText("My Button")
widget.setSize(200, 100)

# ✅ Good
button.setText(UI_CONSTANTS['MY_BUTTON_TEXT'])
widget.setSize(*UI_CONSTANTS['MY_WIDGET_SIZE'])
```

---

## Common Patterns

### Pattern 1: Tool Button with Validation

```python
# In main_window.py
def handle_tool_action(self):
    """Handle tool button click."""
    try:
        if not self.validate_tool_prerequisites():
            return
        
        result = self.app.perform_tool_action()
        self.update_ui_after_tool_action(result)
    except Exception as e:
        self.handle_tool_error(e)

def validate_tool_prerequisites(self) -> bool:
    """Validate prerequisites for tool."""
    if not self.app.current_neuron:
        self.show_status_message("Please load a neuron first", error=True)
        return False
    return True
```

### Pattern 2: Configuration Widget

```python
# In main_window.py
def setup_config_widget(self):
    """Set up configuration widget."""
    config_group = QGroupBox("Configuration")
    config_layout = QVBoxLayout(config_group)
    
    # Add controls
    self.config_slider = QSlider(Qt.Horizontal)
    self.config_slider.valueChanged.connect(self.handle_config_change)
    config_layout.addWidget(self.config_slider)
    
    return config_group

def handle_config_change(self, value):
    """Handle configuration change."""
    self.app.settings.set_config_value(value)
    self.apply_config_changes()
```

### Pattern 3: Data Display Widget

```python
# In ui/data_display.py
class DataDisplayWidget(QWidget):
    """Widget for displaying data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def update_data(self, data):
        """Update displayed data."""
        if data is None:
            self.show_no_data_message()
        else:
            self.display_data(data)
    
    def show_no_data_message(self):
        """Show message when no data available."""
        self.label.setText("No data available")
    
    def display_data(self, data):
        """Display the actual data."""
        self.label.setText(f"Data: {data}")
```

---

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all new modules are added to `__init__.py` files
   - Use absolute imports: `from config import UI_CONSTANTS`

2. **UI Elements Not Appearing**
   - Check that widgets are added to layouts
   - Verify parent-child relationships
   - Call `show()` on widgets if needed

3. **Event Handlers Not Working**
   - Verify signal-slot connections
   - Check for exceptions in handlers (add logging)
   - Ensure handler methods are defined

4. **Constants Not Found**
   - Add constants to appropriate config files
   - Import constants in modules that use them
   - Check spelling and case sensitivity

### Debugging Tips

1. **Add Logging**
   ```python
   self.logger.debug(f"Button clicked, current state: {self.app.current_state}")
   ```

2. **Use Print Statements** (temporarily)
   ```python
   print(f"DEBUG: Widget size: {widget.size()}")
   ```

3. **Check Qt Designer** for complex layouts

4. **Test Incrementally** - add one element at a time

---

## Example: Complete Feature Addition

Here's a complete example of adding a "Neuron Statistics" feature:

### 1. Add Constants

```python
# In src/config/constants.py
UI_CONSTANTS = {
    # ... existing constants ...
    'STATS_BUTTON_TEXT': 'Show Statistics',
    'STATS_WINDOW_TITLE': 'Neuron Statistics',
    'STATS_TOOLTIP': 'Display neuron statistics',
}
```

### 2. Add UI Element

```python
# In src/ui/main_window.py
def setup_ui(self):
    # ... existing setup ...
    
    # Add statistics button
    self.stats_btn = QPushButton(UI_CONSTANTS['STATS_BUTTON_TEXT'])
    self.stats_btn.setToolTip(UI_CONSTANTS['STATS_TOOLTIP'])
    self.stats_btn.clicked.connect(self.show_neuron_statistics)
    self.side_layout.addWidget(self.stats_btn)

def show_neuron_statistics(self):
    """Show neuron statistics dialog."""
    try:
        if not self.app.current_neuron:
            self.show_status_message("No neuron loaded", error=True)
            return
        
        stats = self.app.get_neuron_statistics()
        self.display_statistics_dialog(stats)
    except Exception as e:
        self.logger.error(f"Error showing statistics: {e}")
        self.show_status_message(f"Error: {e}", error=True)

def display_statistics_dialog(self, stats):
    """Display statistics in a dialog."""
    dialog = QDialog(self)
    dialog.setWindowTitle(UI_CONSTANTS['STATS_WINDOW_TITLE'])
    layout = QVBoxLayout(dialog)
    
    for key, value in stats.items():
        label = QLabel(f"{key}: {value}")
        layout.addWidget(label)
    
    dialog.exec_()
```

### 3. Add Business Logic

```python
# In src/core/application.py
def get_neuron_statistics(self) -> dict:
    """Get statistics for current neuron.
    
    Returns:
        dict: Statistics data
    """
    if not self.current_neuron:
        return {}
    
    try:
        stats = {
            'Total Points': len(self.vertex_coords),
            'Selected Points': self.point_selector.get_selection_count(),
            'Neuron Type': getattr(self.current_neuron, 'type', 'Unknown'),
        }
        
        self.logger.info("Generated neuron statistics")
        return stats
    except Exception as e:
        self.logger.error(f"Error generating statistics: {e}")
        return {}
```

### 4. Add Tests

```python
# In tests/unit/test_statistics.py
def test_neuron_statistics(self):
    """Test neuron statistics generation."""
    # Setup mock neuron
    mock_neuron = Mock()
    self.app.current_neuron = mock_neuron
    self.app.vertex_coords = np.array([[0, 0, 0], [1, 1, 1]])
    self.app.point_selector.get_selection_count.return_value = 1
    
    # Execute
    stats = self.app.get_neuron_statistics()
    
    # Verify
    assert stats['Total Points'] == 2
    assert stats['Selected Points'] == 1
```

This example demonstrates the complete workflow for adding a new feature following the modular architecture principles.

---

## Conclusion

Following these patterns ensures that your GUI additions:

- ✅ **Maintain architectural consistency**
- ✅ **Are properly tested**
- ✅ **Handle errors gracefully**
- ✅ **Provide good user experience**
- ✅ **Are maintainable and extensible**

Remember: **UI handles display, Core handles logic, Config holds constants**. This separation makes the codebase maintainable and testable.

For questions or clarifications, refer to the existing code examples in the modular structure or consult the main README.md file.

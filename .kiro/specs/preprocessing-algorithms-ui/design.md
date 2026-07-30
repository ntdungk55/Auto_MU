# Design Document

## Overview

Thiết kế feature cho phép user cấu hình preprocessing algorithms cho template matching và OCR thông qua settings dialogs. Feature tích hợp ListView read-only để hiển thị algorithms hiện tại và buttons để mở Multi-Image Algorithm Testing Dialog.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────┐
│     Settings Dialogs Layer         │
├─────────────────────────────────────┤
│  ImageDetectSettingsDialog          │
│  ├─ Template Matching ListView      │
│  └─ Configure Button                │
│                                     │
│  PassiveReadSettingsDialog          │
│  ├─ OCR Algorithms ListView         │
│  └─ Configure Button                │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   Multi-Image Testing Dialog       │
├─────────────────────────────────────┤
│  ├─ Apply to Template Matching     │
│  └─ Apply to OCR Mode              │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│        Data Model Layer            │
├─────────────────────────────────────┤
│  AutoAction                         │
│  ├─ template_matching_algorithms    │
│  └─ ocr_algorithms                  │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      Persistence Layer             │
├─────────────────────────────────────┤
│  ToolManager                        │
│  ├─ _action_to_dict()              │
│  └─ from_dict()                    │
└─────────────────────────────────────┘
```

## Components and Interfaces

### 1. AutoAction Data Model Extensions

```python
@dataclass
class AutoAction:
    # Existing fields...
    
    # New fields for preprocessing algorithms
    template_matching_algorithms: list[dict] = field(default_factory=list)
    ocr_algorithms: list[dict] = field(default_factory=list)
```

**Algorithm Format:**
```python
{
    "id": "upscale_2x",
    "name": "Upscale 2x", 
    "config": {"upscale": 2.0},
    "parameters": {
        "upscale": {
            "type": "float",
            "value": 2.0,
            "label": "Scale Factor"
        }
    }
}
```

### 2. Settings Dialog UI Components

#### ImageDetectSettingsDialog Extensions

```python
class ImageDetectSettingsDialog(QDialog):
    def _init_ui(self):
        # Existing UI...
        
        # Template Matching Preprocessing section
        self._add_template_matching_preprocessing_section(layout)
    
    def _add_template_matching_preprocessing_section(self, layout):
        """Add Template Matching Preprocessing section."""
        preprocessing_group = QGroupBox("⚙️ Template Matching Preprocessing")
        preprocessing_layout = QVBoxLayout()
        
        # Algorithm ListView (read-only)
        self.template_algorithms_list = QListWidget()
        self.template_algorithms_list.setMaximumHeight(120)
        self.template_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        preprocessing_layout.addWidget(self.template_algorithms_list)
        
        # Configure button
        configure_btn = QPushButton("⚙️ Cấu hình Template Matching Algorithms")
        configure_btn.clicked.connect(self._open_template_matching_config)
        preprocessing_layout.addWidget(configure_btn)
        
        preprocessing_group.setLayout(preprocessing_layout)
        layout.addWidget(preprocessing_group)
    
    def _open_template_matching_config(self):
        """Open Multi-Image Testing Dialog for template matching."""
        # Implementation details...
    
    def _update_template_algorithms_display(self):
        """Update template algorithms ListView display."""
        # Implementation details...
```

#### PassiveReadSettingsDialog Extensions

```python
class PassiveReadSettingsDialog(QDialog):
    def _add_ocr_preprocessing_section(self, left_column):
        """Add OCR Preprocessing section to left column."""
        ocr_preprocessing_group = QGroupBox("⚙️ OCR Preprocessing")
        ocr_preprocessing_layout = QVBoxLayout()
        
        # Algorithm ListView (read-only)
        self.ocr_algorithms_list = QListWidget()
        self.ocr_algorithms_list.setMaximumHeight(120)
        self.ocr_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        ocr_preprocessing_layout.addWidget(self.ocr_algorithms_list)
        
        # Configure button
        configure_btn = QPushButton("⚙️ Cấu hình OCR Algorithms")
        configure_btn.clicked.connect(self._open_ocr_config)
        ocr_preprocessing_layout.addWidget(configure_btn)
        
        ocr_preprocessing_group.setLayout(ocr_preprocessing_layout)
        left_column.addWidget(ocr_preprocessing_group)
```

### 3. Multi-Image Testing Dialog Extensions

```python
class MultiImageAlgorithmTestingDialog(QDialog):
    def _init_ui(self):
        # Existing UI...
        
        # Add Apply buttons
        self._add_apply_buttons(layout)
    
    def _add_apply_buttons(self, layout):
        """Add Apply buttons for different modes."""
        apply_row = QHBoxLayout()
        
        self.apply_template_btn = QPushButton("📤 Apply to Template Matching")
        self.apply_template_btn.clicked.connect(self._apply_to_template_matching)
        apply_row.addWidget(self.apply_template_btn)
        
        self.apply_ocr_btn = QPushButton("📤 Apply to OCR Mode")
        self.apply_ocr_btn.clicked.connect(self._apply_to_ocr_mode)
        apply_row.addWidget(self.apply_ocr_btn)
        
        apply_row.addStretch()
        layout.addLayout(apply_row)
    
    def _apply_to_template_matching(self):
        """Apply current algorithms to template matching."""
        algorithms = self._get_current_algorithms()
        self.action.template_matching_algorithms = algorithms
        QMessageBox.information(self, "Thành công", 
            f"Đã apply {len(algorithms)} algorithms cho Template Matching!")
    
    def _apply_to_ocr_mode(self):
        """Apply current algorithms to OCR mode."""
        algorithms = self._get_current_algorithms()
        self.action.ocr_algorithms = algorithms
        QMessageBox.information(self, "Thành công", 
            f"Đã apply {len(algorithms)} algorithms cho OCR Mode!")
```

## Data Models

### Algorithm Data Structure

```python
# Single Algorithm
{
    "id": str,           # Unique identifier
    "name": str,         # Display name
    "config": dict,      # Algorithm configuration
    "parameters": dict   # Parameter definitions with values
}

# Parameters Structure
{
    "parameter_name": {
        "type": str,        # "float", "int", "choice"
        "value": Any,       # Current value
        "label": str,       # Display label
        "min": float,       # Min value (for numeric)
        "max": float,       # Max value (for numeric)
        "choices": list     # Available choices (for choice type)
    }
}
```

### AutoAction Extensions

```python
# Template Matching Algorithms (for IMAGE_DETECT, MOUSE_CLICK)
template_matching_algorithms: list[dict] = [
    {
        "id": "upscale_2x",
        "name": "Upscale 2x",
        "config": {"upscale": 2.0},
        "parameters": {
            "upscale": {
                "type": "float",
                "value": 2.0,
                "label": "Scale Factor"
            }
        }
    }
]

# OCR Algorithms (for READ_PASSIVE OCR mode)
ocr_algorithms: list[dict] = [
    {
        "id": "enhance_contrast",
        "name": "Enhance Contrast",
        "config": {"enhance_contrast": True},
        "parameters": {
            "contrast_level": {
                "type": "float", 
                "value": 1.5,
                "label": "Contrast Level"
            }
        }
    }
]
```

## Algorithm Display Logic

### Format Algorithm Display

```python
def format_algorithm_display(algorithm: dict) -> str:
    """Format algorithm for ListView display."""
    name = algorithm.get("name", "Unknown")
    parameters = algorithm.get("parameters", {})
    
    if not parameters:
        return name
    
    # Format parameters
    param_strs = []
    for param_name, param_info in parameters.items():
        value = param_info.get("value")
        label = param_info.get("label", param_name)
        param_strs.append(f"{label}: {value}")
    
    param_text = ", ".join(param_strs)
    return f"{name} ({param_text})"

# Examples:
# "Upscale 2x (Scale Factor: 2.0)"
# "Enhance Contrast (Contrast Level: 1.5)"
# "Sharpen (Sharpen Strength: 1.0)"
# "Grayscale Only"  # No parameters
```

### ListView Population

```python
def update_algorithms_display(list_widget: QListWidget, algorithms: list[dict]):
    """Update algorithms ListView display."""
    list_widget.clear()
    
    if not algorithms:
        item = QListWidgetItem("Không có thuật toán")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)  # Disabled
        list_widget.addItem(item)
        return
    
    for algorithm in algorithms:
        display_text = format_algorithm_display(algorithm)
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, algorithm)  # Store algorithm data
        list_widget.addItem(item)
```

## Error Handling

### Validation Logic

```python
def validate_algorithm(algorithm: dict) -> tuple[bool, str]:
    """Validate algorithm structure."""
    required_fields = ["id", "name", "config"]
    
    for field in required_fields:
        if field not in algorithm:
            return False, f"Missing required field: {field}"
    
    # Validate parameters if present
    if "parameters" in algorithm:
        parameters = algorithm["parameters"]
        if not isinstance(parameters, dict):
            return False, "Parameters must be a dictionary"
        
        for param_name, param_info in parameters.items():
            if not isinstance(param_info, dict):
                return False, f"Parameter {param_name} must be a dictionary"
            
            if "value" not in param_info:
                return False, f"Parameter {param_name} missing value"
    
    return True, ""

def validate_algorithms_list(algorithms: list[dict]) -> tuple[bool, str]:
    """Validate algorithms list."""
    if not isinstance(algorithms, list):
        return False, "Algorithms must be a list"
    
    for i, algorithm in enumerate(algorithms):
        is_valid, error = validate_algorithm(algorithm)
        if not is_valid:
            return False, f"Algorithm {i}: {error}"
    
    return True, ""
```

## Testing Strategy

### Unit Tests

**Test Algorithm Display Formatting:**
```python
def test_format_algorithm_display_with_parameters():
    """Test algorithm display formatting with parameters."""
    algorithm = {
        "name": "Upscale 2x",
        "parameters": {
            "upscale": {"value": 2.0, "label": "Scale Factor"}
        }
    }
    result = format_algorithm_display(algorithm)
    assert result == "Upscale 2x (Scale Factor: 2.0)"

def test_format_algorithm_display_no_parameters():
    """Test algorithm display formatting without parameters."""
    algorithm = {"name": "Grayscale Only"}
    result = format_algorithm_display(algorithm)
    assert result == "Grayscale Only"
```

**Test Data Persistence:**
```python
def test_template_matching_algorithms_persistence():
    """Test template matching algorithms save/load."""
    action = AutoAction(name="test", purpose="test", action_type=ActionType.IMAGE_DETECT, mode=ActionMode.ACTIVE)
    algorithms = [{"id": "test", "name": "Test", "config": {}}]
    action.template_matching_algorithms = algorithms
    
    # Test serialization
    data = tool_manager._action_to_dict(action)
    assert "template_matching_algorithms" in data
    assert data["template_matching_algorithms"] == algorithms
    
    # Test deserialization
    loaded_action = tool_manager.from_dict(data)
    assert loaded_action.template_matching_algorithms == algorithms
```

**Test UI Integration:**
```python
def test_image_detect_dialog_template_section():
    """Test template matching section in Image Detect dialog."""
    action = AutoAction(name="test", purpose="test", action_type=ActionType.IMAGE_DETECT, mode=ActionMode.ACTIVE)
    dialog = ImageDetectSettingsDialog(action)
    
    # Check if template algorithms list exists
    assert hasattr(dialog, 'template_algorithms_list')
    assert isinstance(dialog.template_algorithms_list, QListWidget)
    
    # Check if configure button exists
    configure_buttons = dialog.findChildren(QPushButton, "⚙️ Cấu hình Template Matching Algorithms")
    assert len(configure_buttons) > 0
```

### Manual Test Plan

**Test Case 1: Template Matching Algorithms Configuration**

**Mục đích:** Verify template matching algorithms can be configured and displayed

**Điều kiện tiên quyết:**
- App đã mở
- Có tool với IMAGE_DETECT action

**Các bước thực hiện:**
1. Mở tool editor
2. Click vào IMAGE_DETECT action
3. Click "Cài đặt" để mở Image Detect Settings Dialog
4. Scroll xuống Template Matching Preprocessing section
5. Verify ListView hiển thị "Không có thuật toán"
6. Click "⚙️ Cấu hình Template Matching Algorithms"
7. Multi-Image Testing Dialog mở
8. Add algorithms: Upscale 2x, Enhance Contrast
9. Click "📤 Apply to Template Matching"
10. Close Multi-Image Testing Dialog
11. Verify ListView hiển thị: "Upscale 2x (Scale Factor: 2.0)", "Enhance Contrast (Contrast Level: 1.5)"
12. Click "Lưu" để save settings
13. Close và reopen dialog
14. Verify algorithms vẫn được hiển thị

**Kết quả mong đợi:**
- Template Matching Preprocessing section hiển thị đúng
- ListView hiển thị algorithms với parameters
- Data được persist sau khi save/reload

**Test Case 2: OCR Algorithms Configuration**

**Mục đích:** Verify OCR algorithms can be configured for READ_PASSIVE actions

**Điều kiện tiên quyết:**
- App đã mở  
- Có tool với READ_PASSIVE action

**Các bước thực hiện:**
1. Mở tool editor
2. Click vào READ_PASSIVE action
3. Click "Cài đặt" để mở Passive Read Settings Dialog
4. Set mode = "Đọc dữ liệu"
5. Verify OCR Preprocessing section hiển thị trong left column
6. Verify ListView hiển thị "Không có thuật toán"
7. Click "⚙️ Cấu hình OCR Algorithms"
8. Multi-Image Testing Dialog mở
9. Add algorithms: Sharpen, Denoise
10. Click "📤 Apply to OCR Mode"
11. Close Multi-Image Testing Dialog
12. Verify ListView hiển thị: "Sharpen (Sharpen Strength: 1.0)", "Denoise (Denoise Strength: 5)"

**Kết quả mong đợi:**
- OCR Preprocessing section chỉ hiển thị khi mode = "Đọc dữ liệu"
- ListView hiển thị algorithms với parameters
- Apply functionality hoạt động đúng
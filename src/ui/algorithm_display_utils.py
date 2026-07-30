"""Utility functions for displaying preprocessing algorithms in UI."""

from typing import List, Dict
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt


def format_algorithm_display(algorithm: dict) -> str:
    """Format algorithm for ListView display.
    
    Args:
        algorithm: Algorithm dictionary with id, name, config, parameters
        
    Returns:
        Formatted string for display
        
    Examples:
        - With parameters: "Upscale 2x (Scale Factor: 2.0)"
        - Without parameters: "Grayscale Only"
    """
    name = algorithm.get("name", "Unknown")
    parameters = algorithm.get("parameters", {})
    
    if not parameters:
        return name
    
    # Format parameters
    param_strs = []
    for param_name, param_info in parameters.items():
        if not isinstance(param_info, dict):
            continue
            
        value = param_info.get("value")
        label = param_info.get("label", param_name)
        
        if value is not None:
            param_strs.append(f"{label}: {value}")
    
    if not param_strs:
        return name
        
    param_text = ", ".join(param_strs)
    return f"{name} ({param_text})"


def update_algorithms_display(list_widget: QListWidget, algorithms: List[Dict]) -> None:
    """Update algorithms ListView display.
    
    Args:
        list_widget: QListWidget to update
        algorithms: List of algorithm dictionaries
    """
    list_widget.clear()
    
    if not algorithms:
        # Show "No algorithms" message when empty
        item = QListWidgetItem("Không có thuật toán")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)  # Disabled
        list_widget.addItem(item)
        return
    
    # Add each algorithm
    for algorithm in algorithms:
        display_text = format_algorithm_display(algorithm)
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, algorithm)  # Store algorithm data
        list_widget.addItem(item)


def validate_algorithm(algorithm: dict) -> tuple[bool, str]:
    """Validate algorithm structure.
    
    Args:
        algorithm: Algorithm dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(algorithm, dict):
        return False, "Algorithm must be a dictionary"
    
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


def validate_algorithms_list(algorithms: List[Dict]) -> tuple[bool, str]:
    """Validate algorithms list.
    
    Args:
        algorithms: List of algorithm dictionaries to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(algorithms, list):
        return False, "Algorithms must be a list"
    
    for i, algorithm in enumerate(algorithms):
        is_valid, error = validate_algorithm(algorithm)
        if not is_valid:
            return False, f"Algorithm {i}: {error}"
    
    return True, ""
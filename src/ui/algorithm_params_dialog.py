"""Dialog for editing algorithm parameters with live preview."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QSpinBox, QDoubleSpinBox, QPushButton, QWidget)
from PyQt6.QtCore import Qt
import numpy as np


class AlgorithmParamsDialog(QDialog):
    """Dialog to edit parameters of a preprocessing algorithm."""
    
    def __init__(self, algo_id: str, current_params: dict, algo_params_def: list,
                 original_image: np.ndarray, parent_widget, pipeline_index: int):
        """Initialize the dialog.
        
        Args:
            algo_id: Algorithm ID (e.g., "gaussian_blur")
            current_params: Current parameter values
            algo_params_def: Parameter definitions from ALGORITHMS
            original_image: Original image for preview
            parent_widget: Reference to the teaching algorithm lab widget
            pipeline_index: Index of this algorithm in pipeline
        """
        super().__init__(parent_widget)
        self.algo_id = algo_id
        self.current_params = current_params.copy()
        self.old_params = current_params.copy()  # Backup for Cancel
        self.algo_params_def = algo_params_def
        self.original_image = original_image
        self.parent_widget = parent_widget
        self.pipeline_index = pipeline_index
        self.param_widgets = {}
        
        self.setWindowTitle(f"Algorithm Parameters - {self._get_algo_name()}")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self._init_ui()
    
    def _get_algo_name(self) -> str:
        """Get algorithm display name."""
        from .multi_image_algorithm_testing_dialog import DEFAULT_ALGORITHMS
        algorithm = next((item for item in DEFAULT_ALGORITHMS if item.get("id") == self.algo_id), None)
        return str((algorithm or {}).get("name", self.algo_id))
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(f"<b>{self._get_algo_name()}</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Parameters
        if not self.algo_params_def:
            no_params_label = QLabel("<i>Thuật toán này không có tham số.</i>")
            no_params_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_params_label)
        else:
            params_widget = QWidget()
            params_layout = QVBoxLayout()
            params_widget.setLayout(params_layout)
            
            for param_def in self.algo_params_def:
                param_layout = QHBoxLayout()
                param_name = param_def["name"]
                param_label = param_def["label"]
                param_type = param_def.get("type", "int")
                
                # Label
                label = QLabel(param_label + ":")
                label.setMinimumWidth(150)
                param_layout.addWidget(label)
                
                # Widget
                if param_type == "int":
                    widget = QSpinBox()
                    widget.setMinimum(param_def.get("min", 0))
                    widget.setMaximum(param_def.get("max", 100))
                    widget.setSingleStep(param_def.get("step", 1))
                    widget.setValue(self.current_params.get(param_name, param_def.get("default", 0)))
                    widget.valueChanged.connect(lambda v, pn=param_name: self._on_param_changed(pn, v))
                elif param_type == "float":
                    widget = QDoubleSpinBox()
                    widget.setMinimum(param_def.get("min", 0.0))
                    widget.setMaximum(param_def.get("max", 10.0))
                    widget.setSingleStep(param_def.get("step", 0.1))
                    widget.setDecimals(2)
                    widget.setValue(self.current_params.get(param_name, param_def.get("default", 1.0)))
                    widget.valueChanged.connect(lambda v, pn=param_name: self._on_param_changed(pn, v))
                else:
                    widget = QSpinBox()
                    widget.setValue(self.current_params.get(param_name, param_def.get("default", 0)))
                    widget.valueChanged.connect(lambda v, pn=param_name: self._on_param_changed(pn, v))
                
                self.param_widgets[param_name] = widget
                param_layout.addWidget(widget)
                param_layout.addStretch()
                
                params_layout.addLayout(param_layout)
            
            layout.addWidget(params_widget)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if not self.algo_params_def:
            # No parameters, just Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.reject)
            button_layout.addWidget(close_btn)
        else:
            # OK and Cancel buttons
            ok_btn = QPushButton("OK")
            ok_btn.clicked.connect(self.accept)
            ok_btn.setDefault(True)
            button_layout.addWidget(ok_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_param_changed(self, param_name: str, value):
        """Handle parameter value change - preview immediately."""
        self.current_params[param_name] = value
        self._preview()
    
    def _preview(self):
        """Preview the result with current parameters."""
        if self.original_image is None:
            return
        
        try:
            # Update pipeline with temp params
            self.parent_widget.pipeline[self.pipeline_index]["params"] = self.current_params.copy()
            
            # Process image with updated pipeline
            self.parent_widget.process_image()
        except Exception as e:
            print(f"[Preview Error] {e}")
    
    def accept(self):
        """Save parameters and close."""
        # Parameters already updated in pipeline during preview
        super().accept()
    
    def reject(self):
        """Restore old parameters and close."""
        # Restore old params
        self.parent_widget.pipeline[self.pipeline_index]["params"] = self.old_params.copy()
        
        # Revert preview
        self.parent_widget.process_image()
        
        super().reject()

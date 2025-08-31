"""
Dialog components for ADB Helper application.
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QTabWidget, QWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from adb_tools.adb import ADBDevice
from adb_tools.fastboot import FastbootDevice
from utils.config import Config


class SafetyConfirmationDialog(QDialog):
    """Dialog for confirming dangerous fastboot operations."""
    
    def __init__(
        self,
        parent,
        title: str,
        warning_message: str,
        device_serial: str,
        requires_serial: bool = False,
        requires_typed_confirmation: bool = False
    ):
        super().__init__(parent)
        self.device_serial = device_serial
        self.requires_serial = requires_serial
        self.requires_typed_confirmation = requires_typed_confirmation
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.setup_ui(warning_message)
    
    def setup_ui(self, warning_message: str):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        
        # Warning icon and message
        warning_frame = QFrame()
        warning_frame.setStyleSheet("background-color: #fff3cd; border: 2px solid #ffeaa7; border-radius: 5px;")
        warning_layout = QVBoxLayout(warning_frame)
        
        warning_label = QLabel(warning_message)
        warning_label.setWordWrap(True)
        warning_label.setFont(QFont("", 10))
        warning_layout.addWidget(warning_label)
        
        layout.addWidget(warning_frame)
        
        # Device serial confirmation
        if self.requires_serial:
            serial_group = QGroupBox("Device Confirmation")
            serial_layout = QFormLayout(serial_group)
            
            serial_layout.addRow("Target Device:", QLabel(self.device_serial))
            
            self.serial_input = QLineEdit()
            self.serial_input.setPlaceholderText("Type device serial to confirm")
            self.serial_input.textChanged.connect(self.validate_inputs)
            serial_layout.addRow("Confirm Serial:", self.serial_input)
            
            layout.addWidget(serial_group)
        
        # Typed confirmation
        if self.requires_typed_confirmation:
            confirm_group = QGroupBox("Final Confirmation")
            confirm_layout = QFormLayout(confirm_group)
            
            self.confirmation_input = QLineEdit()
            self.confirmation_input.setPlaceholderText("Type 'I UNDERSTAND' to proceed")
            self.confirmation_input.textChanged.connect(self.validate_inputs)
            confirm_layout.addRow("Type 'I UNDERSTAND':", self.confirmation_input)
            
            layout.addWidget(confirm_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.proceed_btn = QPushButton("Proceed")
        self.proceed_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        self.proceed_btn.setEnabled(False)
        self.proceed_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.proceed_btn)
        
        layout.addLayout(button_layout)
    
    def validate_inputs(self):
        """Validate user inputs and enable/disable proceed button."""
        valid = True
        
        if self.requires_serial:
            if self.serial_input.text().strip() != self.device_serial:
                valid = False
        
        if self.requires_typed_confirmation:
            if self.confirmation_input.text().strip() != "I UNDERSTAND":
                valid = False
        
        self.proceed_btn.setEnabled(valid)


class DeviceInfoDialog(QDialog):
    """Dialog for displaying detailed device information."""
    
    def __init__(self, parent, device_info: Dict[str, Any], device_type: str):
        super().__init__(parent)
        self.device_info = device_info
        self.device_type = device_type
        
        self.setWindowTitle(f"{device_type} Information")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        
        # Create tabs for different info categories
        tab_widget = QTabWidget()
        
        # Basic info tab
        basic_tab = self.create_basic_info_tab()
        tab_widget.addTab(basic_tab, "Basic Info")
        
        # Properties tab
        props_tab = self.create_properties_tab()
        tab_widget.addTab(props_tab, "Properties")
        
        # Battery tab (if available)
        if "battery" in self.device_info:
            battery_tab = self.create_battery_tab()
            tab_widget.addTab(battery_tab, "Battery")
        
        layout.addWidget(tab_widget)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_basic_info_tab(self) -> QWidget:
        """Create basic information tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Display key device information
        key_fields = [
            ("ro.product.model", "Model"),
            ("ro.product.manufacturer", "Manufacturer"),
            ("ro.build.version.release", "Android Version"),
            ("ro.build.version.sdk", "SDK Level"),
            ("ro.serialno", "Serial Number"),
            ("ro.product.cpu.abi", "CPU Architecture"),
            ("ro.build.version.security_patch", "Security Patch"),
        ]
        
        for key, label in key_fields:
            value = self.device_info.get(key, "Unknown")
            layout.addRow(f"{label}:", QLabel(value))
        
        return widget
    
    def create_properties_tab(self) -> QWidget:
        """Create properties tab with all device properties."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Scrollable text area for all properties
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        props_widget = QWidget()
        props_layout = QFormLayout(props_widget)
        
        # Sort and display all properties
        sorted_props = sorted(self.device_info.items())
        for key, value in sorted_props:
            if key != "battery":  # Battery has its own tab
                if isinstance(value, (str, int, float)):
                    props_layout.addRow(f"{key}:", QLabel(str(value)))
        
        scroll_area.setWidget(props_widget)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_battery_tab(self) -> QWidget:
        """Create battery information tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        battery_info = self.device_info.get("battery", {})
        
        for key, value in battery_info.items():
            layout.addRow(f"{key.title()}:", QLabel(str(value)))
        
        return widget


class SettingsDialog(QDialog):
    """Settings configuration dialog."""
    
    def __init__(self, parent, config: Config):
        super().__init__(parent)
        self.config = config
        self.app_config = config.get_config()
        
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        
        # Create tabs
        tab_widget = QTabWidget()
        
        # General settings
        general_tab = self.create_general_tab()
        tab_widget.addTab(general_tab, "General")
        
        # Safety settings
        safety_tab = self.create_safety_tab()
        tab_widget.addTab(safety_tab, "Safety")
        
        # Advanced settings
        advanced_tab = self.create_advanced_tab()
        tab_widget.addTab(advanced_tab, "Advanced")
        
        layout.addWidget(tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Binary paths
        self.adb_path_input = QLineEdit()
        self.adb_path_input.setPlaceholderText("Auto-detect")
        layout.addRow("ADB Path:", self.adb_path_input)
        
        self.fastboot_path_input = QLineEdit()
        self.fastboot_path_input.setPlaceholderText("Auto-detect")
        layout.addRow("Fastboot Path:", self.fastboot_path_input)
        
        # Auto-detect checkbox
        self.auto_detect_cb = QCheckBox("Auto-detect binary paths")
        layout.addRow("", self.auto_detect_cb)
        
        # Theme selection
        # TODO: Add theme selection
        
        return widget
    
    def create_safety_tab(self) -> QWidget:
        """Create safety settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Safety options
        self.require_confirmations_cb = QCheckBox("Require confirmations for dangerous operations")
        layout.addWidget(self.require_confirmations_cb)
        
        self.enable_dev_mode_cb = QCheckBox("Enable developer mode (advanced users)")
        layout.addWidget(self.enable_dev_mode_cb)
        
        self.store_pairing_codes_cb = QCheckBox("Store wireless pairing codes (encrypted)")
        layout.addWidget(self.store_pairing_codes_cb)
        
        layout.addStretch()
        
        return widget
    
    def create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Network settings
        self.default_port_input = QLineEdit()
        layout.addRow("Default ADB Port:", self.default_port_input)
        
        self.timeout_input = QLineEdit()
        layout.addRow("Connection Timeout (s):", self.timeout_input)
        
        # Feature flags
        self.wireless_debugging_cb = QCheckBox("Enable wireless debugging features")
        layout.addRow("", self.wireless_debugging_cb)
        
        self.fastboot_features_cb = QCheckBox("Enable fastboot features")
        layout.addRow("", self.fastboot_features_cb)
        
        return widget
    
    def load_settings(self):
        """Load current settings into UI."""
        # General settings
        self.adb_path_input.setText(self.app_config.adb_path or "")
        self.fastboot_path_input.setText(self.app_config.fastboot_path or "")
        self.auto_detect_cb.setChecked(self.app_config.auto_detect_binaries)
        
        # Safety settings
        self.require_confirmations_cb.setChecked(self.app_config.require_confirmations)
        self.enable_dev_mode_cb.setChecked(self.app_config.enable_dev_mode)
        self.store_pairing_codes_cb.setChecked(self.app_config.store_pairing_codes)
        
        # Advanced settings
        self.default_port_input.setText(str(self.app_config.default_adb_port))
        self.timeout_input.setText(str(self.app_config.connection_timeout))
        self.wireless_debugging_cb.setChecked(self.app_config.enable_wireless_debugging)
        self.fastboot_features_cb.setChecked(self.app_config.enable_fastboot_features)
    
    def save_settings(self):
        """Save settings and close dialog."""
        try:
            # Update config
            self.config.update_config(
                adb_path=self.adb_path_input.text() or None,
                fastboot_path=self.fastboot_path_input.text() or None,
                auto_detect_binaries=self.auto_detect_cb.isChecked(),
                require_confirmations=self.require_confirmations_cb.isChecked(),
                enable_dev_mode=self.enable_dev_mode_cb.isChecked(),
                store_pairing_codes=self.store_pairing_codes_cb.isChecked(),
                default_adb_port=int(self.default_port_input.text()),
                connection_timeout=int(self.timeout_input.text()),
                enable_wireless_debugging=self.wireless_debugging_cb.isChecked(),
                enable_fastboot_features=self.fastboot_features_cb.isChecked()
            )
            
            self.accept()
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Please check your input values:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings:\n{e}")
    
    def reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config.reset_to_defaults()
            self.load_settings()


class WirelessPairingDialog(QDialog):
    """Dialog for wireless ADB pairing."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Wireless ADB Pairing")
        self.setModal(True)
        self.setMinimumSize(400, 300)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "To enable wireless debugging:\n\n"
            "1. Go to Settings > Developer Options on your device\n"
            "2. Enable 'Wireless debugging'\n"
            "3. Tap 'Pair device with pairing code'\n"
            "4. Enter the IP address and pairing code below"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Input fields
        form_layout = QFormLayout()
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        form_layout.addRow("Device IP:", self.ip_input)
        
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("5555")
        self.port_input.setText("5555")
        form_layout.addRow("Port:", self.port_input)
        
        self.pairing_code_input = QLineEdit()
        self.pairing_code_input.setPlaceholderText("123456")
        form_layout.addRow("Pairing Code:", self.pairing_code_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.pair_btn = QPushButton("Pair Device")
        self.pair_btn.clicked.connect(self.pair_device)
        button_layout.addWidget(self.pair_btn)
        
        layout.addLayout(button_layout)
    
    def pair_device(self):
        """Attempt to pair with device."""
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        pairing_code = self.pairing_code_input.text().strip()
        
        if not all([ip, port, pairing_code]):
            QMessageBox.warning(self, "Missing Information", "Please fill in all fields.")
            return
        
        try:
            port_num = int(port)
            # TODO: Implement actual pairing logic
            QMessageBox.information(self, "Pairing", f"Attempting to pair with {ip}:{port_num}")
            self.accept()
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", "Port must be a number.")


class ProgressDialog(QDialog):
    """Dialog for showing operation progress."""
    
    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Message
        self.message_label = QLabel(message)
        layout.addWidget(self.message_label)
        
        # Progress bar
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)
    
    def update_message(self, message: str):
        """Update progress message."""
        self.message_label.setText(message)
    
    def set_progress(self, value: int, maximum: int = 100):
        """Set progress value."""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)

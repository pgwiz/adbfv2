"""
Wizard components for ADB Helper application.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QFormLayout, QGroupBox,
    QRadioButton, QButtonGroup, QMessageBox, QProgressBar
)
from adb_tools.adb import ADBWrapper
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class WirelessPairingWizard(QWizard):
    """Wizard for setting up wireless ADB debugging."""
    
    def __init__(self, parent, adb_wrapper):
        super().__init__(parent)
        self.adb_wrapper = adb_wrapper
        
        self.setWindowTitle("Wireless ADB Pairing Wizard")
        self.setMinimumSize(500, 400)
        
        # Add pages
        self.addPage(IntroPage())
        self.addPage(MethodSelectionPage())
        self.addPage(ModernPairingPage(adb_wrapper))
        self.addPage(LegacyPairingPage(adb_wrapper))
        self.addPage(CompletionPage())


class IntroPage(QWizardPage):
    """Introduction page for wireless pairing."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Wireless ADB Setup")
        self.setSubTitle("Set up wireless debugging to use ADB over Wi-Fi")
        
        layout = QVBoxLayout(self)
        
        intro_text = QLabel(
            "This wizard will help you set up wireless ADB debugging.\n\n"
            "Requirements:\n"
            "• Android 11+ for modern pairing (recommended)\n"
            "• Android 4.2+ for legacy TCP/IP mode\n"
            "• Device and computer on same Wi-Fi network\n"
            "• USB debugging enabled in Developer Options"
        )
        intro_text.setWordWrap(True)
        layout.addWidget(intro_text)


class MethodSelectionPage(QWizardPage):
    """Page for selecting pairing method."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Select Pairing Method")
        self.setSubTitle("Choose the appropriate method for your Android version")
        
        layout = QVBoxLayout(self)
        
        # Method selection
        self.method_group = QButtonGroup()
        
        self.modern_radio = QRadioButton("Modern Pairing (Android 11+)")
        self.modern_radio.setChecked(True)
        self.method_group.addButton(self.modern_radio, 0)
        layout.addWidget(self.modern_radio)
        
        modern_desc = QLabel("Uses pairing codes for secure connection. Recommended for newer devices.")
        modern_desc.setStyleSheet("margin-left: 20px; color: gray;")
        layout.addWidget(modern_desc)
        
        self.legacy_radio = QRadioButton("Legacy TCP/IP Mode (Android 4.2+)")
        self.method_group.addButton(self.legacy_radio, 1)
        layout.addWidget(self.legacy_radio)
        
        legacy_desc = QLabel("Requires USB connection first. Works with older Android versions.")
        legacy_desc.setStyleSheet("margin-left: 20px; color: gray;")
        layout.addWidget(legacy_desc)
        
        layout.addStretch()
    
    def nextId(self):
        """Determine next page based on selection."""
        if self.modern_radio.isChecked():
            return 2  # ModernPairingPage
        else:
            return 3  # LegacyPairingPage


class ModernPairingPage(QWizardPage):
    """Page for modern wireless pairing (Android 11+)."""
    
    def __init__(self, adb_wrapper):
        super().__init__()
        self.adb_wrapper = adb_wrapper
        self.setTitle("Modern Wireless Pairing")
        self.setSubTitle("Pair using pairing code (Android 11+)")
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "On your Android device:\n"
            "1. Go to Settings > Developer Options\n"
            "2. Enable 'Wireless debugging'\n"
            "3. Tap 'Pair device with pairing code'\n"
            "4. Enter the information shown on your device below:"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Input form
        form_layout = QFormLayout()
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        form_layout.addRow("Device IP Address:", self.ip_input)
        
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("37045")
        form_layout.addRow("Pairing Port:", self.port_input)
        
        self.pairing_code_input = QLineEdit()
        self.pairing_code_input.setPlaceholderText("123456")
        form_layout.addRow("Pairing Code:", self.pairing_code_input)
        
        layout.addLayout(form_layout)
        
        # Pair button
        self.pair_btn = QPushButton("Pair Device")
        self.pair_btn.clicked.connect(self.pair_device)
        layout.addWidget(self.pair_btn)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def pair_device(self):
        """Attempt to pair with device."""
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        pairing_code = self.pairing_code_input.text().strip()
        
        if not all([ip, port, pairing_code]):
            self.status_label.setText("❌ Please fill in all fields")
            return
        
        try:
            port_num = int(port)
            self.status_label.setText("🔄 Pairing...")
            
            result = self.adb_wrapper.pair(ip, port_num, pairing_code)
            
            if result.success:
                self.status_label.setText("✅ Pairing successful!")
                self.setField("pairing_successful", True)
            else:
                self.status_label.setText(f"❌ Pairing failed: {result.stderr}")
                
        except ValueError:
            self.status_label.setText("❌ Invalid port number")
    
    def nextId(self):
        """Skip to completion page."""
        return 4  # CompletionPage


class LegacyPairingPage(QWizardPage):
    """Page for legacy TCP/IP pairing."""
    
    def __init__(self, adb_wrapper):
        super().__init__()
        self.adb_wrapper = adb_wrapper
        self.setTitle("Legacy TCP/IP Mode")
        self.setSubTitle("Enable ADB over TCP/IP (requires USB connection)")
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Legacy mode setup:\n\n"
            "1. Connect your device via USB\n"
            "2. Ensure USB debugging is enabled\n"
            "3. Click 'Enable TCP/IP Mode' below\n"
            "4. Disconnect USB cable\n"
            "5. Connect using device IP address"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Enable TCP/IP button
        self.enable_tcpip_btn = QPushButton("Enable TCP/IP Mode")
        self.enable_tcpip_btn.clicked.connect(self.enable_tcpip)
        layout.addWidget(self.enable_tcpip_btn)
        
        # Connection form
        form_layout = QFormLayout()
        
        self.device_ip_input = QLineEdit()
        self.device_ip_input.setPlaceholderText("192.168.1.100")
        form_layout.addRow("Device IP:", self.device_ip_input)
        
        self.connect_port_input = QLineEdit()
        self.connect_port_input.setText("5555")
        form_layout.addRow("Port:", self.connect_port_input)
        
        layout.addLayout(form_layout)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_device)
        self.connect_btn.setEnabled(False)
        layout.addWidget(self.connect_btn)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def enable_tcpip(self):
        """Enable TCP/IP mode on connected device."""
        self.status_label.setText("🔄 Enabling TCP/IP mode...")
        
        result = self.adb_wrapper.tcpip(5555)
        
        if result.success:
            self.status_label.setText("✅ TCP/IP mode enabled. You can now disconnect USB.")
            self.connect_btn.setEnabled(True)
        else:
            self.status_label.setText(f"❌ Failed to enable TCP/IP: {result.stderr}")
    
    def connect_device(self):
        """Connect to device over TCP/IP."""
        ip = self.device_ip_input.text().strip()
        port = self.connect_port_input.text().strip()
        
        if not ip:
            self.status_label.setText("❌ Please enter device IP address")
            return
        
        try:
            port_num = int(port)
            self.status_label.setText("🔄 Connecting...")
            
            result = self.adb_wrapper.connect(ip, port_num)
            
            if result.success:
                self.status_label.setText("✅ Connected successfully!")
                self.setField("connection_successful", True)
            else:
                self.status_label.setText(f"❌ Connection failed: {result.stderr}")
                
        except ValueError:
            self.status_label.setText("❌ Invalid port number")
    
    def nextId(self):
        """Skip to completion page."""
        return 4  # CompletionPage


class CompletionPage(QWizardPage):
    """Completion page for wireless setup."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle("Wireless debugging is now configured")
        
        layout = QVBoxLayout(self)
        
        success_label = QLabel("✅ Wireless ADB debugging has been set up successfully!")
        success_label.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(success_label)
        
        tips = QLabel(
            "\nTips for wireless debugging:\n\n"
            "• Keep your device and computer on the same Wi-Fi network\n"
            "• The connection may timeout after inactivity\n"
            "• Use 'adb connect <ip>:5555' to reconnect manually\n"
            "• Disable wireless debugging when not needed to save battery"
        )
        tips.setWordWrap(True)
        layout.addWidget(tips)
        
        layout.addStretch()

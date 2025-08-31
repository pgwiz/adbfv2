"""
Main window for ADB Helper application.
"""

import logging
from typing import Optional, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QStatusBar,
    QMenuBar, QMenu, QToolBar, QSplitter, QTextEdit, QGroupBox,
    QProgressBar, QMessageBox, QHeaderView, QAbstractItemView,
    QLineEdit, QRadioButton, QCheckBox, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QFont

from adb_tools.adb import ADBWrapper, ADBDevice, ADBState
from adb_tools.fastboot import FastbootWrapper, FastbootDevice
from utils.config import Config
from ui.dialogs import SafetyConfirmationDialog, DeviceInfoDialog, SettingsDialog
from ui.wizard import WirelessPairingWizard


class DeviceRefreshThread(QThread):
    """Background thread for refreshing device list."""
    devices_updated = pyqtSignal(list, list)  # adb_devices, fastboot_devices
    
    def __init__(self, adb_wrapper: ADBWrapper, fastboot_wrapper: FastbootWrapper):
        super().__init__()
        self.adb_wrapper = adb_wrapper
        self.fastboot_wrapper = fastboot_wrapper
        self.running = True
    
    def run(self):
        """Run device refresh in background."""
        while self.running:
            try:
                adb_devices = []
                fastboot_devices = []
                
                if self.adb_wrapper and self.adb_wrapper.is_available():
                    adb_devices = self.adb_wrapper.devices()
                
                if self.fastboot_wrapper and self.fastboot_wrapper.is_available():
                    fastboot_devices = self.fastboot_wrapper.devices()
                
                self.devices_updated.emit(adb_devices, fastboot_devices)
                self.msleep(2000)  # Refresh every 2 seconds
                
            except Exception as e:
                print(f"Device refresh error: {e}")
                self.msleep(5000)  # Wait longer on error
    
    def stop(self):
        """Stop the refresh thread."""
        self.running = False
        self.quit()
        self.wait()


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, config: Config, adb_available: bool, fastboot_available: bool):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.adb_available = adb_available
        self.fastboot_available = fastboot_available
        
        # Initialize ADB and Fastboot wrappers
        self.adb_wrapper = ADBWrapper() if adb_available else None
        self.fastboot_wrapper = FastbootWrapper() if fastboot_available else None
        
        # UI state
        self.selected_adb_device: Optional[str] = None
        self.selected_fastboot_device: Optional[str] = None
        self.refresh_timer = QTimer()
        self.refresh_thread: Optional[DeviceRefreshThread] = None
        
        self.setup_ui()
        self.setup_connections()
        self.restore_window_state()
        self.start_device_refresh()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("ADB Helper - Advanced Android Debug Bridge Tool")
        self.setMinimumSize(1000, 700)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for main content
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel - Device management
        self.create_device_panel(main_splitter)
        
        # Right panel - Tabbed interface
        self.create_tabs_panel(main_splitter)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 600])
        
        # Status bar
        self.create_status_bar()
    
    def create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        refresh_action = QAction("&Refresh Devices", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_devices)
        tools_menu.addAction(refresh_action)
        
        wireless_action = QAction("&Wireless Pairing", self)
        wireless_action.triggered.connect(self.show_wireless_wizard)
        tools_menu.addAction(wireless_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        docs_action = QAction("&Documentation", self)
        docs_action.setShortcut("F1")
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_device_panel(self, parent):
        """Create device management panel."""
        device_widget = QWidget()
        device_layout = QVBoxLayout(device_widget)
        
        # Device list header
        header_layout = QHBoxLayout()
        device_label = QLabel("Connected Devices")
        device_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(device_label)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        header_layout.addWidget(self.refresh_btn)
        
        device_layout.addLayout(header_layout)
        
        # Device table
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(6)
        self.device_table.setHorizontalHeaderLabels([
            "Serial", "State", "Model", "Android", "Battery", "IP"
        ])
        
        # Configure table
        header = self.device_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.device_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.device_table.itemSelectionChanged.connect(self.on_device_selection_changed)
        
        device_layout.addWidget(self.device_table)
        
        # Device actions
        actions_group = QGroupBox("Device Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Basic actions
        basic_layout = QHBoxLayout()
        
        self.reboot_btn = QPushButton("Reboot")
        self.reboot_btn.setEnabled(False)
        self.reboot_btn.clicked.connect(self.reboot_device)
        basic_layout.addWidget(self.reboot_btn)
        
        self.device_info_btn = QPushButton("Device Info")
        self.device_info_btn.setEnabled(False)
        self.device_info_btn.clicked.connect(self.show_device_info)
        basic_layout.addWidget(self.device_info_btn)
        
        actions_layout.addLayout(basic_layout)
        device_layout.addWidget(actions_group)
        
        parent.addWidget(device_widget)
    
    def create_tabs_panel(self, parent):
        """Create tabbed interface panel."""
        self.tab_widget = QTabWidget()
        
        # File Transfer tab
        self.tab_widget.addTab(self.create_file_transfer_tab(), "File Transfer")
        
        # APK Manager tab
        self.tab_widget.addTab(self.create_apk_manager_tab(), "APK Manager")
        
        # Logcat tab
        self.tab_widget.addTab(self.create_logcat_tab(), "Logcat")
        
        # Fastboot Tools tab
        self.tab_widget.addTab(self.create_fastboot_tab(), "Fastboot Tools")
        
        parent.addWidget(self.tab_widget)
    
    def create_file_transfer_tab(self):
        """Create file transfer tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Transfer direction selection
        direction_group = QGroupBox("Transfer Direction")
        direction_layout = QHBoxLayout(direction_group)
        
        self.push_radio = QPushButton("Push to Device")
        self.pull_radio = QPushButton("Pull from Device")
        self.push_radio.setCheckable(True)
        self.pull_radio.setCheckable(True)
        self.push_radio.setChecked(True)
        
        direction_layout.addWidget(self.push_radio)
        direction_layout.addWidget(self.pull_radio)
        
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        self.local_path_edit = QLineEdit()
        self.local_path_edit.setPlaceholderText("Local file/folder path")
        self.browse_local_btn = QPushButton("Browse Local...")
        
        self.remote_path_edit = QLineEdit()
        self.remote_path_edit.setPlaceholderText("Remote path on device")
        
        local_layout = QHBoxLayout()
        local_layout.addWidget(QLabel("Local:"))
        local_layout.addWidget(self.local_path_edit)
        local_layout.addWidget(self.browse_local_btn)
        
        remote_layout = QHBoxLayout()
        remote_layout.addWidget(QLabel("Remote:"))
        remote_layout.addWidget(self.remote_path_edit)
        
        file_layout.addLayout(local_layout)
        file_layout.addLayout(remote_layout)
        
        # Transfer options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.preserve_timestamp_cb = QCheckBox("Preserve timestamps")
        self.compression_cb = QCheckBox("Use compression")
        options_layout.addWidget(self.preserve_timestamp_cb)
        options_layout.addWidget(self.compression_cb)
        
        # Transfer controls
        controls_layout = QHBoxLayout()
        self.transfer_btn = QPushButton("Start Transfer")
        self.cancel_transfer_btn = QPushButton("Cancel")
        self.cancel_transfer_btn.setEnabled(False)
        
        controls_layout.addWidget(self.transfer_btn)
        controls_layout.addWidget(self.cancel_transfer_btn)
        controls_layout.addStretch()
        
        # Progress
        self.transfer_progress = QProgressBar()
        self.transfer_status = QLabel("Ready")
        
        # Layout assembly
        layout.addWidget(direction_group)
        layout.addWidget(file_group)
        layout.addWidget(options_group)
        layout.addLayout(controls_layout)
        layout.addWidget(self.transfer_progress)
        layout.addWidget(self.transfer_status)
        layout.addStretch()
        
        # Connect signals
        self.push_radio.clicked.connect(lambda: self.pull_radio.setChecked(False))
        self.pull_radio.clicked.connect(lambda: self.push_radio.setChecked(False))
        self.browse_local_btn.clicked.connect(self.browse_local_file)
        self.transfer_btn.clicked.connect(self.start_file_transfer)
        
        return widget
    
    def create_apk_manager_tab(self):
        """Create APK manager tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # APK selection
        apk_group = QGroupBox("APK Selection")
        apk_layout = QVBoxLayout(apk_group)
        
        self.apk_path_edit = QLineEdit()
        self.apk_path_edit.setPlaceholderText("Select APK file to install")
        self.browse_apk_btn = QPushButton("Browse APK...")
        
        apk_file_layout = QHBoxLayout()
        apk_file_layout.addWidget(QLabel("APK File:"))
        apk_file_layout.addWidget(self.apk_path_edit)
        apk_file_layout.addWidget(self.browse_apk_btn)
        apk_layout.addLayout(apk_file_layout)
        
        # Install options
        options_group = QGroupBox("Install Options")
        options_layout = QVBoxLayout(options_group)
        
        self.replace_app_cb = QCheckBox("Replace existing app (-r)")
        self.test_app_cb = QCheckBox("Install as test app (-t)")
        self.downgrade_cb = QCheckBox("Allow downgrade (-d)")
        self.grant_permissions_cb = QCheckBox("Grant all permissions (-g)")
        
        options_layout.addWidget(self.replace_app_cb)
        options_layout.addWidget(self.test_app_cb)
        options_layout.addWidget(self.downgrade_cb)
        options_layout.addWidget(self.grant_permissions_cb)
        
        # Install controls
        controls_layout = QHBoxLayout()
        self.install_btn = QPushButton("Install APK")
        self.uninstall_btn = QPushButton("Uninstall App")
        
        controls_layout.addWidget(self.install_btn)
        controls_layout.addWidget(self.uninstall_btn)
        controls_layout.addStretch()
        
        # Package name for uninstall
        uninstall_layout = QHBoxLayout()
        self.package_name_edit = QLineEdit()
        self.package_name_edit.setPlaceholderText("com.example.package")
        uninstall_layout.addWidget(QLabel("Package:"))
        uninstall_layout.addWidget(self.package_name_edit)
        
        # Progress and status
        self.apk_progress = QProgressBar()
        self.apk_status = QLabel("Ready")
        
        # Layout assembly
        layout.addWidget(apk_group)
        layout.addWidget(options_group)
        layout.addLayout(controls_layout)
        layout.addLayout(uninstall_layout)
        layout.addWidget(self.apk_progress)
        layout.addWidget(self.apk_status)
        layout.addStretch()
        
        # Connect signals
        self.browse_apk_btn.clicked.connect(self.browse_apk_file)
        self.install_btn.clicked.connect(self.install_apk)
        self.uninstall_btn.clicked.connect(self.uninstall_app)
        
        return widget
    
    def create_logcat_tab(self):
        """Create logcat viewer tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logcat controls
        controls_layout = QHBoxLayout()
        
        self.logcat_start_btn = QPushButton("Start Logcat")
        self.logcat_start_btn.clicked.connect(self.start_logcat)
        controls_layout.addWidget(self.logcat_start_btn)
        
        self.logcat_stop_btn = QPushButton("Stop")
        self.logcat_stop_btn.setEnabled(False)
        controls_layout.addWidget(self.logcat_stop_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Logcat output
        self.logcat_output = QTextEdit()
        self.logcat_output.setReadOnly(True)
        self.logcat_output.setFont(QFont("Consolas", 9))
        layout.addWidget(self.logcat_output)
        
        self.tab_widget.addTab(widget, "Logcat")
    
    def create_fastboot_tab(self):
        """Create fastboot tools tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Warning label
        warning_label = QLabel("⚠️ Fastboot operations can permanently damage your device!")
        warning_label.setStyleSheet("color: red; font-weight: bold; padding: 10px;")
        layout.addWidget(warning_label)
        
        # Fastboot controls
        controls_layout = QHBoxLayout()
        
        self.unlock_btn = QPushButton("🔓 Unlock Bootloader")
        self.unlock_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        self.unlock_btn.clicked.connect(self.unlock_bootloader)
        controls_layout.addWidget(self.unlock_btn)
        
        self.lock_btn = QPushButton("🔒 Lock Bootloader")
        self.lock_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        self.lock_btn.clicked.connect(self.lock_bootloader)
        controls_layout.addWidget(self.lock_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Fastboot output
        self.fastboot_output = QTextEdit()
        self.fastboot_output.setReadOnly(True)
        self.fastboot_output.setFont(QFont("Consolas", 9))
        layout.addWidget(self.fastboot_output)
        
        self.tab_widget.addTab(widget, "Fastboot Tools")
    
    def create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status labels
        adb_status = "ADB: Ready" if self.adb_available else "ADB: Not Available"
        fastboot_status = "Fastboot: Ready" if self.fastboot_available else "Fastboot: Not Available"
        
        self.status_bar.addWidget(QLabel(adb_status))
        self.status_bar.addWidget(QLabel(fastboot_status))
        self.status_bar.addPermanentWidget(QLabel("Ready"))
    
    def setup_connections(self):
        """Setup signal connections."""
        self.refresh_timer.timeout.connect(self.refresh_devices)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def start_device_refresh(self):
        """Start background device refresh."""
        if self.refresh_thread and self.refresh_thread.isRunning():
            return
        
        if self.adb_wrapper or self.fastboot_wrapper:
            self.refresh_thread = DeviceRefreshThread(self.adb_wrapper, self.fastboot_wrapper)
            self.refresh_thread.devices_updated.connect(self.update_device_table)
            self.refresh_thread.start()
    
    @pyqtSlot(list, list)
    def update_device_table(self, adb_devices: List[ADBDevice], fastboot_devices: List[FastbootDevice]):
        """Update device table with new device information."""
        self.device_table.setRowCount(0)
        
        # Add ADB devices
        for device in adb_devices:
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)
            
            self.device_table.setItem(row, 0, QTableWidgetItem(device.serial))
            self.device_table.setItem(row, 1, QTableWidgetItem(f"ADB: {device.state.value}"))
            self.device_table.setItem(row, 2, QTableWidgetItem(device.model or "Unknown"))
            self.device_table.setItem(row, 3, QTableWidgetItem("Android"))
            self.device_table.setItem(row, 4, QTableWidgetItem("N/A"))
            self.device_table.setItem(row, 5, QTableWidgetItem("N/A"))
        
        # Add Fastboot devices
        for device in fastboot_devices:
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)
            
            self.device_table.setItem(row, 0, QTableWidgetItem(device.serial))
            self.device_table.setItem(row, 1, QTableWidgetItem(f"Fastboot: {device.state}"))
            self.device_table.setItem(row, 2, QTableWidgetItem("N/A"))
            self.device_table.setItem(row, 3, QTableWidgetItem("N/A"))
            self.device_table.setItem(row, 4, QTableWidgetItem("N/A"))
            self.device_table.setItem(row, 5, QTableWidgetItem("N/A"))
    
    def on_device_selection_changed(self):
        """Handle device selection change."""
        selected_items = self.device_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            serial = self.device_table.item(row, 0).text()
            state = self.device_table.item(row, 1).text()
            
            if "ADB:" in state:
                self.selected_adb_device = serial
                self.selected_fastboot_device = None
            elif "Fastboot:" in state:
                self.selected_fastboot_device = serial
                self.selected_adb_device = None
            
            self.update_button_states()
    
    def update_button_states(self):
        """Update button enabled states based on selection."""
        has_adb_device = self.selected_adb_device is not None
        has_fastboot_device = self.selected_fastboot_device is not None
        
        self.reboot_btn.setEnabled((has_adb_device and self.adb_available) or (has_fastboot_device and self.fastboot_available))
        self.device_info_btn.setEnabled(has_adb_device or has_fastboot_device)
        self.logcat_start_btn.setEnabled(has_adb_device and self.adb_available)
        
        if hasattr(self, 'unlock_btn'):
            self.unlock_btn.setEnabled(has_fastboot_device and self.fastboot_available)
            self.lock_btn.setEnabled(has_fastboot_device and self.fastboot_available)
    
    def refresh_devices(self):
        """Refresh device list."""
        self.start_device_refresh()
    
    def reboot_device(self):
        """Reboot selected device."""
        if self.selected_adb_device and self.adb_wrapper:
            reply = QMessageBox.question(
                self, "Reboot Device", f"Reboot device {self.selected_adb_device}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                result = self.adb_wrapper.reboot(serial=self.selected_adb_device)
                if result.success:
                    self.status_bar.showMessage("Device rebooting...")
                else:
                    QMessageBox.warning(self, "Reboot Failed", f"Failed to reboot:\n{result.stderr}")
    
    def unlock_bootloader(self):
        """Unlock bootloader with safety confirmation."""
        QMessageBox.critical(self, "Not Implemented", "Bootloader unlock requires safety dialog - coming soon!")
    
    def lock_bootloader(self):
        """Lock bootloader with safety confirmation."""
        QMessageBox.critical(self, "Not Implemented", "Bootloader lock requires safety dialog - coming soon!")
    
    def show_device_info(self):
        """Show device information."""
        QMessageBox.information(self, "Device Info", "Device information dialog - coming soon!")
    
    def start_logcat(self):
        """Start logcat monitoring."""
        if not self.selected_adb_device:
            QMessageBox.warning(self, "No Device", "Please select an ADB device first.")
            return
        
        self.logcat_output.append("Logcat functionality - coming soon!")
    
    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self, self.config)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.status_bar.showMessage("Settings updated")
    
    def show_wireless_wizard(self):
        """Show wireless pairing wizard."""
        if not self.adb_available:
            QMessageBox.warning(self, "ADB Not Available", "ADB is required for wireless debugging.")
            return
        
        wizard = WirelessPairingWizard(self, self.adb_wrapper)
        wizard.exec()
    
    def show_documentation(self):
        """Show documentation."""
        QMessageBox.information(self, "Documentation", "Documentation viewer - coming soon!")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About ADB Helper",
            "ADB Helper v2.0\n\n"
            "Advanced ADB + Fastboot Desktop Application\n"
            "Built with PyQt6 and Python\n\n"
            " 2024 ADB Helper Project"
        )
    
    # File Transfer Methods
    def browse_local_file(self):
        """Browse for local file or directory."""
        from PyQt6.QtWidgets import QFileDialog
        if self.push_radio.isChecked():
            path, _ = QFileDialog.getOpenFileName(self, "Select File to Push")
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Directory for Pull")
        
        if path:
            self.local_path_edit.setText(path)
    
    def start_file_transfer(self):
        """Start file transfer operation."""
        if not self.selected_adb_device:
            QMessageBox.warning(self, "No Device", "Please select an ADB device first.")
            return
        
        local_path = self.local_path_edit.text().strip()
        remote_path = self.remote_path_edit.text().strip()
        
        if not local_path or not remote_path:
            QMessageBox.warning(self, "Missing Paths", "Please specify both local and remote paths.")
            return
        
        # Start transfer in background thread
        self.transfer_btn.setEnabled(False)
        self.cancel_transfer_btn.setEnabled(True)
        self.transfer_progress.setValue(0)
        self.transfer_status.setText("Starting transfer...")
        
        try:
            if self.push_radio.isChecked():
                # Push to device
                result = self.adb_wrapper.push(
                    local=local_path,
                    remote=remote_path,
                    serial=self.selected_adb_device,
                    sync=False,
                    compression="lz4" if self.compression_cb.isChecked() else None
                )
            else:
                # Pull from device
                result = self.adb_wrapper.pull(
                    remote=remote_path,
                    local=local_path,
                    serial=self.selected_adb_device,
                    preserve_timestamp=self.preserve_timestamp_cb.isChecked(),
                    compression="lz4" if self.compression_cb.isChecked() else None
                )
            
            if result.success:
                self.transfer_progress.setValue(100)
                self.transfer_status.setText("Transfer completed successfully!")
                QMessageBox.information(self, "Success", "File transfer completed successfully!")
            else:
                self.transfer_status.setText("Transfer failed!")
                QMessageBox.warning(self, "Transfer Failed", f"Transfer failed:\n{result.stderr}")
                
        except Exception as e:
            self.transfer_status.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Transfer error:\n{str(e)}")
        
        finally:
            self.transfer_btn.setEnabled(True)
            self.cancel_transfer_btn.setEnabled(False)
    
    # APK Manager Methods
    def browse_apk_file(self):
        """Browse for APK file."""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select APK File", "", "APK Files (*.apk);;All Files (*)"
        )
        if path:
            self.apk_path_edit.setText(path)
    
    def install_apk(self):
        """Install APK to device."""
        if not self.selected_adb_device:
            QMessageBox.warning(self, "No Device", "Please select an ADB device first.")
            return
        
        apk_path = self.apk_path_edit.text().strip()
        if not apk_path:
            QMessageBox.warning(self, "No APK", "Please select an APK file first.")
            return
        
        # Start installation
        self.install_btn.setEnabled(False)
        self.apk_progress.setValue(0)
        self.apk_status.setText("Installing APK...")
        
        try:
            result = self.adb_wrapper.install(
                apk_path=apk_path,
                serial=self.selected_adb_device,
                replace=self.replace_app_cb.isChecked(),
                test=self.test_app_cb.isChecked(),
                downgrade=self.downgrade_cb.isChecked(),
                grant_permissions=self.grant_permissions_cb.isChecked()
            )
            
            if result.success:
                self.apk_progress.setValue(100)
                self.apk_status.setText("APK installed successfully!")
                QMessageBox.information(self, "Success", "APK installed successfully!")
            else:
                self.apk_status.setText("Installation failed!")
                QMessageBox.warning(self, "Installation Failed", f"APK installation failed:\n{result.stderr}")
                
        except Exception as e:
            self.apk_status.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Installation error:\n{str(e)}")
        
        finally:
            self.install_btn.setEnabled(True)
    
    def uninstall_app(self):
        """Uninstall app from device."""
        if not self.selected_adb_device:
            QMessageBox.warning(self, "No Device", "Please select an ADB device first.")
            return
        
        package_name = self.package_name_edit.text().strip()
        if not package_name:
            QMessageBox.warning(self, "No Package", "Please enter a package name.")
            return
        
        # Confirm uninstall
        reply = QMessageBox.question(
            self, "Confirm Uninstall", 
            f"Uninstall package '{package_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            result = self.adb_wrapper.uninstall(
                package=package_name,
                serial=self.selected_adb_device,
                keep_data=False
            )
            
            if result.success:
                self.apk_status.setText("App uninstalled successfully!")
                QMessageBox.information(self, "Success", "App uninstalled successfully!")
            else:
                self.apk_status.setText("Uninstall failed!")
                QMessageBox.warning(self, "Uninstall Failed", f"App uninstall failed:\n{result.stderr}")
                
        except Exception as e:
            self.apk_status.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Uninstall error:\n{str(e)}")
    
    def restore_window_state(self):
        """Restore window geometry and state."""
        # TODO: Implement window state restoration from config
        pass
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save window state
        # TODO: Save window geometry to config
        
        # Stop refresh thread
        if self.refresh_thread:
            self.refresh_thread.stop()
        
        # Stop refresh timer
        self.refresh_timer.stop()
        
        event.accept()

# ADB Helper - Advanced Android Debug Bridge Desktop App

A comprehensive, safety-first desktop application for Android development and device management using ADB and Fastboot.

## Features

### 🛡️ Safety-First Design
- **Multi-tier safety system** for fastboot operations
- **Typed confirmations** for destructive commands
- **Device serial verification** for critical operations
- **Automatic compatibility checks** before dangerous operations

### 📱 Device Management
- **Real-time device monitoring** with auto-refresh
- **Wireless ADB pairing** (Android 11+ and legacy TCP/IP)
- **Comprehensive device information** display
- **Multi-device support** with easy switching

### 🔧 Complete ADB Support (v1.0.41)
- **File transfer** with progress tracking and compression
- **APK installation** with advanced options
- **Shell command execution** with interactive console
- **Logcat viewer** with filtering and export
- **Port forwarding** and reverse forwarding
- **System control** (reboot, root, remount)

### ⚡ Fastboot Tools
- **Bootloader management** with safety confirmations
- **Partition operations** (flash, erase, format)
- **A/B slot management** for modern devices
- **GSI support** and logical partitions
- **OEM command execution** with warnings

### 🔐 Secure Storage
- **OS keyring integration** (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- **Encrypted fallback storage** with user passphrase
- **Optional pairing code storage** with explicit consent

### 👨‍💻 Developer Features
- **Interactive console** with command history
- **Session transcript export**
- **Embedded documentation** with search
- **Advanced logging** and debugging tools

## Installation

### Prerequisites
- Python 3.8 or higher
- Android SDK Platform Tools (ADB and Fastboot)
- PyQt6 and dependencies

### Quick Start

1. **Clone or download** the project:
   ```bash
   git clone https://github.com/adbhelper/adb-helper.git
   cd adb-helper
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python -m adb_helper
   ```

### Installing Android SDK Platform Tools

#### Windows
1. Download from [Android Developer site](https://developer.android.com/studio/releases/platform-tools)
2. Extract to `C:\platform-tools\`
3. Add to PATH or let ADB Helper auto-detect

#### macOS
```bash
# Using Homebrew
brew install android-platform-tools

# Or download manually and add to PATH
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt install android-tools-adb android-tools-fastboot

# Or download platform-tools and add to PATH
```

## Usage

### First Run
1. **Launch ADB Helper**
2. **Grant permissions** for USB debugging on your device
3. **Enable Developer Options** on Android device
4. **Connect device** via USB or wireless

### Wireless Debugging Setup

#### Modern Method (Android 11+)
1. Go to **Settings > Developer Options**
2. Enable **"Wireless debugging"**
3. Tap **"Pair device with pairing code"**
4. Use **Tools > Wireless Pairing** in ADB Helper
5. Enter IP address and pairing code

#### Legacy Method (Android 4.2+)
1. Connect device via **USB first**
2. Use **Tools > Wireless Pairing > Legacy Mode**
3. Click **"Enable TCP/IP Mode"**
4. Disconnect USB and connect wirelessly

### Safety Features

#### Fastboot Safety Tiers

**🟢 SAFE** - Standard confirmation:
- Device information queries
- Temporary boot operations
- Status checks

**🟡 RISKY** - Confirmation dialog:
- Firmware flashing operations
- Slot management
- OEM commands

**🔴 DESTRUCTIVE** - Device serial + "I UNDERSTAND":
- Bootloader unlock/lock
- Partition erase/format
- Critical partition operations

### File Transfer
- **Drag and drop** APK files to install
- **Bulk file operations** with progress tracking
- **Compression support** for faster transfers
- **Sync mode** for development workflows

### Developer Console
- **Direct command execution** with safety checks
- **Command history** with persistence
- **Auto-completion** for common commands
- **Session export** for documentation

## Configuration

### Settings Location
- **Windows**: `%APPDATA%\ADB Helper\config.json`
- **macOS**: `~/Library/Application Support/ADB Helper/config.json`
- **Linux**: `~/.config/adb-helper/config.json`

### Key Settings
- **Binary paths**: Custom ADB/Fastboot locations
- **Safety options**: Confirmation requirements
- **Network settings**: Default ports and timeouts
- **UI preferences**: Theme and layout options

## Security

### Credential Storage
- **Primary**: OS native keyring (most secure)
- **Fallback**: AES-encrypted file with user passphrase
- **Optional**: Wireless pairing code storage
- **Clear all data**: Requires "DELETE" + password confirmation

### Safety Measures
- **No auto-execution** of dangerous commands
- **Device compatibility validation** before operations
- **Battery level checks** for critical operations
- **Recovery instructions** for common failures

## Troubleshooting

### ADB Not Found
1. Install Android SDK Platform Tools
2. Add platform-tools to system PATH
3. Or set custom path in Settings

### Device Not Detected
1. Enable **USB Debugging** in Developer Options
2. Accept **USB debugging authorization** on device
3. Try different **USB cable/port**
4. Install **device drivers** (Windows)

### Wireless Connection Issues
1. Ensure **same Wi-Fi network**
2. Check **firewall settings**
3. Verify **wireless debugging enabled**
4. Try **legacy TCP/IP mode**

### Fastboot Issues
1. Boot device to **fastboot mode** (Power + Volume Down)
2. Install **proper USB drivers**
3. Check **bootloader unlock status**
4. Verify **device compatibility**

## Development

### Project Structure
```
adb_helper/
├── __main__.py              # App entry point
├── app.py                   # Application bootstrap
├── ui/                      # Qt UI modules
├── adb_tools/              # Core ADB/Fastboot wrappers
├── features/               # Feature modules
├── utils/                  # Utilities
├── docs/                   # Embedded documentation
└── tests/                  # Unit tests
```

### Building from Source

1. **Install development dependencies**:
   ```bash
   pip install -e .[dev]
   ```

2. **Run tests**:
   ```bash
   pytest
   ```

3. **Format code**:
   ```bash
   black .
   flake8 .
   ```

4. **Build executable**:
   ```bash
   pyinstaller --onefile --windowed app.py
   ```

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## License

MIT License - see LICENSE file for details.

## Disclaimer

**⚠️ IMPORTANT SAFETY NOTICE**

This tool provides access to powerful ADB and Fastboot commands that can:
- **Permanently damage** or brick your device
- **Void device warranty**
- **Erase all data** without recovery possibility

**Use at your own risk.** The developers are not responsible for any damage to devices, data loss, or other issues resulting from use of this software.

Always:
- **Backup your device** before making changes
- **Research commands** before execution
- **Verify device compatibility** for firmware operations
- **Keep stock firmware** available for recovery

## Support

- **Documentation**: Built-in help system (F1)
- **Issues**: GitHub Issues tracker
- **Discussions**: GitHub Discussions
- **Wiki**: Community-maintained guides

---

**Made with ❤️ for the Android development community**

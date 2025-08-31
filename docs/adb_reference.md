# ADB Reference Guide

## Android Debug Bridge (ADB) Commands

ADB is a versatile command-line tool that lets you communicate with a device. This reference covers ADB v1.0.41 commands available in ADB Helper.

### Device Management

#### `adb devices [-l]`
List all connected devices.
- `-l`: Show additional device information (model, product, transport)

**Example:**
```
adb devices -l
List of devices attached
emulator-5554          device product:sdk_gphone_x86 model:Android_SDK_built_for_x86 device:generic_x86
```

#### `adb connect <host>[:<port>]`
Connect to device over TCP/IP.
- Default port: 5555
- Requires wireless debugging enabled

#### `adb disconnect [<host>[:<port>]]`
Disconnect from TCP/IP device.
- Without arguments: disconnect from all TCP/IP devices

#### `adb pair <host>:<port> [<pairing_code>]`
Pair with device using pairing code (Android 11+).

### File Operations

#### `adb push <local> <remote> [options]`
Copy files/directories from computer to device.

**Options:**
- `--sync`: Only push newer files
- `-z <algorithm>`: Use compression (none, any, brotli, lz4, zstd)
- `-n`: Dry run (show what would be copied)

**Examples:**
```bash
adb push myfile.txt /sdcard/
adb push --sync ./photos/ /sdcard/Pictures/
adb push -z lz4 largefile.zip /data/local/tmp/
```

#### `adb pull <remote> [<local>] [options]`
Copy files/directories from device to computer.

**Options:**
- `-a`: Preserve file timestamps
- `-z <algorithm>`: Use compression

**Examples:**
```bash
adb pull /sdcard/photo.jpg
adb pull -a /data/app/com.example.app/ ./app_backup/
```

#### `adb sync [<directory>] [options]`
Sync files to device.
- `<directory>`: system, vendor, oem, data, or all (default)
- `-l`: List files that would be synced

### App Management

#### `adb install <apk> [options]`
Install APK package.

**Options:**
- `-r`: Replace existing application
- `-t`: Allow test packages
- `-d`: Allow version code downgrade
- `-g`: Grant all runtime permissions
- `--streaming`: Force streaming install
- `--no-streaming`: Force non-streaming install

#### `adb install-multiple <apk1> <apk2> ...`
Install multiple APKs as a single operation.

#### `adb uninstall [-k] <package>`
Remove application package.
- `-k`: Keep data and cache directories

### Shell Commands

#### `adb shell [<command>]`
Run shell commands on device.
- Without command: Start interactive shell
- `-e <char>`: Set escape character (default: ~)
- `-T`: Disable PTY allocation

**Common shell commands:**
```bash
adb shell pm list packages              # List installed packages
adb shell pm install -r app.apk         # Install APK via shell
adb shell am start -n com.app/.Activity # Start activity
adb shell dumpsys battery               # Battery information
adb shell getprop                       # System properties
adb shell input text "Hello World"     # Input text
adb shell screencap -p /sdcard/screen.png # Screenshot
adb shell screenrecord /sdcard/video.mp4  # Screen recording
```

### System Control

#### `adb reboot [<mode>]`
Reboot device.
- `bootloader`: Reboot to bootloader
- `recovery`: Reboot to recovery mode
- `sideload`: Reboot to sideload mode

#### `adb root` / `adb unroot`
Restart ADB daemon with/without root permissions.

#### `adb remount [-R]`
Remount system partitions as read-write.
- `-R`: Automatically reboot if needed

### Debugging

#### `adb logcat [options]`
View device log output.

**Common options:**
- `-c`: Clear log buffer
- `-d`: Dump logs and exit
- `-v <format>`: Output format (brief, process, tag, thread, raw, time, threadtime, long)
- `-b <buffer>`: Log buffer (main, system, radio, events, crash, all)
- `-s <tag>`: Filter by tag
- `<tag>:<level>`: Filter by tag and level

**Examples:**
```bash
adb logcat                           # View all logs
adb logcat -c                        # Clear logs
adb logcat -v threadtime             # Detailed format
adb logcat ActivityManager:I *:S     # Only ActivityManager info and above
adb logcat | grep -i error           # Filter for errors
```

#### `adb bugreport [<path>]`
Generate bug report for debugging.

### Network Operations

#### `adb tcpip <port>`
Switch device to TCP/IP mode.
- Default port: 5555
- Requires USB connection initially

#### `adb usb`
Switch device back to USB mode.

#### `adb forward [options] <local> <remote>`
Forward local port to device.

**Socket types:**
- `tcp:<port>`: TCP socket
- `localabstract:<name>`: Unix abstract socket
- `localreserved:<name>`: Unix reserved socket
- `localfilesystem:<name>`: Unix filesystem socket
- `dev:<character_device>`: Character device
- `jdwp:<pid>`: JDWP process

**Examples:**
```bash
adb forward tcp:8080 tcp:8080        # Forward port 8080
adb forward --list                   # List active forwards
adb forward --remove tcp:8080        # Remove specific forward
adb forward --remove-all             # Remove all forwards
```

#### `adb reverse [options] <remote> <local>`
Reverse forward device port to local.

### Advanced Operations

#### `adb wait-for[-<transport>]-<state>`
Wait for device to reach specified state.

**Transports:** usb, local, any
**States:** device, recovery, rescue, sideload, bootloader, disconnect

**Examples:**
```bash
adb wait-for-device                  # Wait for any device
adb wait-for-usb-device             # Wait for USB device
adb wait-for-local-bootloader       # Wait for local device in bootloader
```

#### `adb sideload <otapackage>`
Sideload OTA update package.
- Device must be in sideload mode

#### `adb keygen <file>`
Generate new ADB key pair.

### Server Management

#### `adb start-server`
Start ADB server daemon.

#### `adb kill-server`
Kill ADB server daemon.

#### `adb reconnect [<mode>]`
Reconnect to device.
- `device`: Reconnect in device mode
- `recovery`: Reconnect in recovery mode
- `sideload`: Reconnect in sideload mode

### Security Features

#### `adb disable-verity` / `adb enable-verity`
Disable/enable dm-verity checking on userdebug builds.

### Tips and Best Practices

1. **Always check device state** before operations:
   ```bash
   adb get-state
   ```

2. **Use device serial** for multiple devices:
   ```bash
   adb -s <serial> <command>
   ```

3. **Enable compression** for large file transfers:
   ```bash
   adb push -z lz4 largefile.zip /sdcard/
   ```

4. **Monitor transfer progress** with verbose output:
   ```bash
   adb push -v myfile.txt /sdcard/
   ```

5. **Use sync for development**:
   ```bash
   adb sync system  # Sync system partition
   ```

### Common Error Solutions

**"device offline"**
- Try: `adb kill-server && adb start-server`
- Check USB cable and connection

**"device unauthorized"**
- Accept USB debugging prompt on device
- Check "Always allow from this computer"

**"no devices/emulators found"**
- Enable Developer Options and USB Debugging
- Install proper USB drivers (Windows)
- Try different USB cable/port

**"insufficient permissions"**
- Run ADB as administrator (Windows)
- Check file permissions on Linux/macOS
- Use `adb root` if device supports it

**"protocol fault (no status)"**
- Device may be in wrong mode
- Try `adb kill-server && adb start-server`
- Reboot device if necessary

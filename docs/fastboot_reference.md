# Fastboot Reference Guide

## Fastboot Commands and Safety Guidelines

Fastboot is a protocol and tool for flashing firmware and modifying device partitions. **⚠️ WARNING: Fastboot commands can permanently brick your device!**

### Safety Tiers

#### 🟢 SAFE Operations
Standard operations with minimal risk:
- `getvar`, `devices`, `reboot`, `boot` (temporary)
- `gsi status`, `fetch`

#### 🟡 RISKY Operations  
Require confirmation dialog:
- `flashall`, `update`, `oem` commands
- `set_active`, logical partition operations
- `snapshot-update cancel`

#### 🔴 DESTRUCTIVE Operations
Require device serial + "I UNDERSTAND" confirmation:
- `flashing unlock/lock`, `flashing unlock_critical`
- `erase`, `format`, `wipe-super`
- `flash` for critical partitions

### Core Commands

#### `fastboot devices [-l]`
List devices in fastboot mode.
- `-l`: Show additional device information

#### `fastboot getvar <variable>`
Get bootloader variable value.

**Important variables:**
```bash
fastboot getvar product              # Device product name
fastboot getvar version-bootloader   # Bootloader version
fastboot getvar unlocked            # Unlock status
fastboot getvar secure              # Secure boot status
fastboot getvar current-slot        # Current active slot (A/B)
fastboot getvar max-download-size   # Maximum download size
fastboot getvar partition-type:system # Partition filesystem type
```

#### `fastboot reboot [<mode>]`
Reboot device.
- No mode: Normal reboot
- `bootloader`: Reboot to bootloader
- `recovery`: Reboot to recovery
- `fastboot`: Stay in fastboot mode

### Flashing Operations ⚠️

#### `fastboot flash <partition> [<filename>]`
Flash partition with image file.

**Critical partitions** (high brick risk):
- `bootloader`: Device bootloader
- `boot`: Kernel and ramdisk
- `recovery`: Recovery image
- `system`: Android system
- `vendor`: Vendor partition

**Examples:**
```bash
fastboot flash boot boot.img
fastboot flash system system.img
fastboot flash recovery recovery.img
```

#### `fastboot flashall [options]`
Flash all partitions from `$ANDROID_PRODUCT_OUT`.
- `--skip-secondary`: Skip secondary slot on A/B devices
- `--skip-reboot`: Don't reboot after flashing

#### `fastboot update <filename.zip>`
Flash update package.
- `-n`: Don't reboot after update

### Partition Management ⚠️ DESTRUCTIVE

#### `fastboot erase <partition>`
**PERMANENTLY ERASE** partition data.

**⚠️ CRITICAL WARNING:**
- Erasing `bootloader`, `boot`, or `recovery` can brick device
- Always have recovery plan before erasing critical partitions
- Ensure you have backup images

#### `fastboot format <partition> [<fs_type>] [<size>]`
Format partition with specified filesystem.
- `<fs_type>`: ext4, f2fs, etc.
- `<size>`: Partition size

#### `fastboot wipe-super [<super_empty.img>]`
Wipe super partition (destroys all logical partitions).

### Bootloader Security ⚠️ CRITICAL

#### `fastboot flashing unlock`
**UNLOCK BOOTLOADER - ERASES ALL DATA!**

**⚠️ CRITICAL WARNINGS:**
- **ALL USER DATA WILL BE PERMANENTLY DELETED**
- Voids warranty on most devices
- Makes device vulnerable to tampering
- Process is irreversible on some devices

**Prerequisites:**
- Enable "OEM unlocking" in Developer Options
- Device must support bootloader unlocking
- Charge battery to >50%

#### `fastboot flashing lock`
**LOCK BOOTLOADER - CAN BRICK DEVICE!**

**⚠️ CRITICAL WARNINGS:**
- Can permanently brick device if custom firmware is installed
- Only lock with 100% stock firmware
- Verify all partitions are stock before locking

#### `fastboot flashing unlock_critical`
Unlock critical partitions (bootloader, radio).
- **EXTREMELY DANGEROUS** - can permanently brick device
- Only for experienced developers

#### `fastboot flashing get_unlock_ability`
Check if bootloader can be unlocked.
- Returns: 0 (locked), 1 (unlockable)

### A/B Slot Management

#### `fastboot set_active <slot>`
Set active boot slot.
- `<slot>`: a, b, all, other

**⚠️ WARNING:** Switching to slot with broken firmware will make device unbootable.

**Check slot status first:**
```bash
fastboot getvar current-slot
fastboot getvar slot-successful:a
fastboot getvar slot-successful:b
fastboot getvar slot-unbootable:a
fastboot getvar slot-unbootable:b
```

### Advanced Features

#### `fastboot boot <kernel> [<ramdisk> [<second>]]`
Boot image from RAM without flashing.
- Safe way to test custom kernels
- Changes are temporary (lost on reboot)

#### `fastboot flash:raw <partition> <kernel> [<ramdisk> [<second>]]`
Flash raw kernel image to partition.

#### `fastboot oem <command>`
Execute OEM-specific commands.
- **⚠️ RISKY:** Commands vary by manufacturer
- Can perform dangerous operations
- Only use if you know exact command purpose

### Logical Partitions (Android 10+)

#### `fastboot create-logical-partition <name> <size>`
Create new logical partition.

#### `fastboot delete-logical-partition <name>`
Delete logical partition.

#### `fastboot resize-logical-partition <name> <size>`
Resize logical partition.

### GSI (Generic System Image)

#### `fastboot gsi wipe`
Wipe GSI installation.

#### `fastboot gsi disable`
Disable GSI and revert to original system.

#### `fastboot gsi status`
Check GSI installation status.

### Snapshots and Updates

#### `fastboot snapshot-update cancel`
Cancel ongoing snapshot update.

#### `fastboot snapshot-update merge`
Merge snapshot update.

#### `fastboot fetch <partition> <filename>`
Download partition to file.

### Android Things

#### `fastboot stage <filename>`
Stage file for flashing.

#### `fastboot get_staged <filename>`
Retrieve staged file.

### Global Options

#### Device Selection
```bash
fastboot -s <serial> <command>       # Target specific device
fastboot -w <command>                # Wipe userdata after flashing
```

#### Network Devices
```bash
fastboot -s tcp:<hostname>[:port] <command>
fastboot -s udp:<hostname>[:port] <command>
```

#### Slot Targeting
```bash
fastboot --slot <slot> <command>     # Target specific slot
fastboot --slot all <command>        # Target all slots
```

#### Advanced Options
```bash
fastboot --force <command>           # Force operation
fastboot --disable-verity <command>  # Disable verity
fastboot --disable-verification <command> # Disable verification
fastboot --fs-options=<options> <command> # Filesystem options
```

### Recovery Procedures

#### Soft Brick Recovery
1. Boot to fastboot mode (Power + Volume Down)
2. Flash stock boot image: `fastboot flash boot boot.img`
3. Flash stock recovery: `fastboot flash recovery recovery.img`
4. Reboot: `fastboot reboot`

#### Hard Brick Prevention
- **Always verify device model** before flashing
- **Check bootloader version** compatibility
- **Have stock firmware** ready before modifications
- **Charge battery** to >50% before critical operations
- **Never interrupt** flashing operations

#### Emergency Download Mode
Some devices have emergency download modes:
- **Samsung**: Download Mode (Volume Down + Home + Power)
- **LG**: Download Mode (Volume Up + USB cable)
- **HTC**: RUU Mode (specific key combinations)

### Common Error Solutions

**"FAILED (remote: 'Partition doesn't exist')"**
- Partition name is incorrect
- Device doesn't have that partition
- Check: `fastboot getvar all` for available partitions

**"FAILED (remote: 'Command not allowed')"**
- Bootloader is locked
- Operation requires unlocked bootloader
- Some operations need critical unlock

**"FAILED (remote: 'Download size exceeded')"**
- File too large for device buffer
- Check: `fastboot getvar max-download-size`
- Split large files or use sparse images

**"FAILED (remote: 'Flashing is not allowed')"**
- Bootloader locked
- OEM unlocking not enabled
- Device doesn't support unlocking

**"waiting for device"**
- Device not in fastboot mode
- USB drivers not installed (Windows)
- Try different USB cable/port

### Best Practices

1. **Always backup** before flashing:
   ```bash
   fastboot fetch boot boot_backup.img
   fastboot fetch recovery recovery_backup.img
   ```

2. **Verify device compatibility**:
   ```bash
   fastboot getvar product
   fastboot getvar version-bootloader
   ```

3. **Check battery level**:
   ```bash
   fastboot getvar battery-voltage
   ```

4. **Test with boot before flashing**:
   ```bash
   fastboot boot custom_boot.img  # Test first
   fastboot flash boot custom_boot.img  # Flash if working
   ```

5. **Use sparse images** for large partitions to avoid timeout issues.

6. **Keep stock firmware** readily available for recovery.

### Manufacturer-Specific Notes

#### Samsung
- Uses Odin tool primarily
- Fastboot support limited
- Download Mode for recovery

#### Google Pixel
- Full fastboot support
- Bootloader unlocking supported
- A/B partition scheme

#### OnePlus
- MSM Download Tool for hard bricks
- Fastboot fully supported
- OEM unlocking required

#### Xiaomi
- Mi Unlock Tool required first
- Fastboot supported after unlock
- EDL mode for recovery

Remember: **When in doubt, don't flash!** Research your specific device model and current firmware before attempting any fastboot operations.

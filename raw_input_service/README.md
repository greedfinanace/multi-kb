# Windows Raw Input Detection Service

A C++ service that detects connected keyboards and mice, identifies them individually, and streams device events to TCP clients.

## Building

### Option 1: Using build.bat (Recommended)
1. Open a Developer Command Prompt for Visual Studio
2. Navigate to this directory
3. Run: `build.bat`

### Option 2: Using CMake
```cmd
mkdir build && cd build
cmake ..
cmake --build . --config Release
```

## Output Files
- `raw_input_service_console.exe` - Console version (shows window, good for debugging)
- `raw_input_service.exe` - Silent version (no console window)

## Usage

1. Run the service as Administrator:
   ```cmd
   raw_input_service_console.exe
   ```

2. Connect a client to receive events:
   ```cmd
   python test_client.py
   ```
   Or use netcat: `nc localhost 9999`

## Event Format (JSON)

Keyboard events:
```json
{"device_id":"0x12AB34CD","type":"keyboard","vkey":65,"timestamp":1234567890}
```

Mouse events:
```json
{"device_id":"0x12AB34CD","type":"mouse","dx":10,"dy":5,"buttons":0,"timestamp":1234567890}
```

## Files
- `common.h` - Shared definitions and logger
- `device_detector.h/cpp` - HID device enumeration
- `socket_server.h/cpp` - TCP server implementation  
- `raw_input_service.cpp` - Main application with Raw Input handling

## Notes
- Requires Windows 10/11
- Admin privileges recommended for full device access
- Does not interfere with normal keyboard/mouse operation
- Log file: `raw_input_service.log`

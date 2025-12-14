# Input Router Daemon

Routes keyboard/mouse input from multiple devices to separate Cursor/VS Code instances.

## Requirements

- Python 3.8+
- Windows 10/11
- Admin privileges (recommended)
- Raw Input Service running on localhost:9999

## Installation

```bash
pip install pywin32
```

## Configuration

Edit `config.json` to configure:

1. **device_mappings**: Map device IDs to users
2. **users**: Define project directories and editor for each user
3. **editor_paths**: Paths to Cursor/VS Code executables

### Finding Device IDs

1. Start the Raw Input Service
2. Run `python input_router.py run`
3. Press keys on each keyboard - device IDs will appear in logs
4. Map devices: `python input_router.py map <device_id> user_1`

## Usage

```bash
# Start daemon (launches editors and routes input)
python input_router.py run

# Map a device to a user
python input_router.py map kb-001 user_1
python input_router.py map mouse-001 user_1

# Launch editor for a user
python input_router.py launch user_1

# List current mappings
python input_router.py list
```

## HTTP API

When running, the daemon exposes an HTTP API on port 8080:

```bash
# Get mappings
curl http://localhost:8080/mappings

# Add mapping
curl -X POST http://localhost:8080/mapping -d '{"device_id":"kb-001","user_id":"user_1"}'

# Launch editor
curl -X POST http://localhost:8080/launch -d '{"user_id":"user_1"}'

# Get active sessions
curl http://localhost:8080/sessions
```

## Auto-Start (Windows Service)

Use `install_service.bat` to install as a Windows service, or add to Task Scheduler.

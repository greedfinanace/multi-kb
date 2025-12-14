<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?style=for-the-badge&logo=windows" alt="Platform">
  <img src="https://img.shields.io/badge/License-Personal%20Use%20Only-red?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" alt="Status">
</p>

<h1 align="center">Multi-User Input Router</h1>

<p align="center">
  <strong>One PC. Multiple keyboards. Multiple mice. Multiple coders.</strong>
</p>

<p align="center">
  <a href="https://x.com/INSIDOOOR69">
    <img src="https://img.shields.io/badge/Follow-@INSIDOOOR69-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white" alt="Twitter">
  </a>
</p>

---

## Why Does This Exist?

Ever tried pair programming on the same machine? One keyboard, one mouse, constant "pass me the keyboard" moments. **Frustrating.**

What if two (or more) developers could each have their own keyboard and mouse, controlling their own VS Code or Cursor window, on the **same computer**?

That's exactly what this does.

```
Developer A                      Developer B
    |                                   |
    v                                   v
+---------+                       +---------+
|Keyboard |                       |Keyboard |
| + Mouse |                       | + Mouse |
+----+----+                       +----+----+
     |                                 |
     +----------+----------------------+
                |
                v
        +---------------+
        |   This App    |
        |  Routes Input |
        +-------+-------+
                |
       +--------+--------+
       v                 v
   +-------+         +-------+
   |Cursor |         |Cursor |
   |User A |         |User B |
   +-------+         +-------+
```

**No VMs. No remote desktop. No network lag. Just native Windows input routing.**

---

## How It Works (Simple Version)

```
+----------------------------------------------------------------+
|                                                                |
|   STEP 1: Plug in 2 keyboards + 2 mice                        |
|                                                                |
|   STEP 2: Run start.bat                                       |
|                                                                |
|   STEP 3: In the Control Panel that opens:                    |
|           - Assign Keyboard A -> User 1                       |
|           - Assign Mouse A    -> User 1                       |
|           - Assign Keyboard B -> User 2                       |
|           - Assign Mouse B    -> User 2                       |
|                                                                |
|   STEP 4: Click "Pick Window" to attach to existing           |
|           Cursor/VS Code windows, OR "Launch" new ones        |
|                                                                |
|   STEP 5: Done! Both people can type SIMULTANEOUSLY!          |
|                                                                |
+----------------------------------------------------------------+
```

### True Simultaneous Typing

Both users can type at the **exact same time** — no focus switching, no lag, no interference.

```
Person A typing "hello"          Person B typing "world"
on their keyboard                on their keyboard
        |                                |
        | (PostMessage)                  | (PostMessage)
        v                                v
+---------------+                +---------------+
|   Cursor A    |                |   Cursor B    |
|   hello_      |                |   world_      |
+---------------+                +---------------+
```

The app uses Windows `PostMessage` API to send keystrokes directly to each window without changing focus. This means:
- Both can type at full speed simultaneously
- No flickering or focus stealing
- Each window maintains its own text caret

### What Happens Behind the Scenes

1. **Windows normally** sends ALL keyboard/mouse input to ONE active window
2. **This app** intercepts input at the hardware level
3. **Identifies** which physical device sent the input
4. **Routes** it to the correct user's editor window
5. **Switches focus** automatically when needed

**Result:** Two people, two keyboards, two mice, two editors, ONE computer. No lag, no VMs, no network.

---

## Features

- **Individual Device Detection** — Each keyboard and mouse is uniquely identified
- **Per-User Routing** — Assign any device to any user session
- **Editor Management** — Launch and control Cursor/VS Code instances from one dashboard
- **Real-Time Monitoring** — Live input event log for debugging
- **Dark Mode UI** — Easy on the eyes during those late-night sessions
- **Low Latency** — Native Windows APIs, no perceptible delay

---

## Architecture


```
+-----------------------------------------------------------------------------+
|                              SYSTEM OVERVIEW                                |
+-----------------------------------------------------------------------------+

+---------------------+                      +---------------------+
|                     |      TCP:9999        |                     |
|  RAW INPUT SERVICE  | ----------------->>  |   INPUT ROUTER      |
|       (C++)         |                      |     DAEMON          |
|                     |                      |    (Python)         |
|  - Captures HID     |                      |                     |
|  - Identifies       |                      |  - Routes events    |
|    devices          |                      |  - Manages editors  |
|  - Streams JSON     |                      |  - Focus control    |
|                     |                      |                     |
+---------------------+                      +----------+----------+
                                                        |
                                                   HTTP:8080
                                                        |
+---------------------+                      +----------v----------+
|                     |      HTTP:3000       |                     |
|   CONTROL PANEL     | <<---------------->> |    API SERVER       |
|      (Web UI)       |      WebSocket       |    (Node.js)        |
|                     |                      |                     |
|  - Device assign    |                      |  - REST endpoints   |
|  - Session mgmt     |                      |  - WebSocket relay  |
|  - Live event log   |                      |  - Status bridge    |
|                     |                      |                     |
+---------------------+                      +---------------------+
```

| Component | Language | Port | Purpose |
|-----------|----------|------|---------|
| Raw Input Service | C++ | 9999 | Captures keyboard/mouse at hardware level |
| Input Router Daemon | Python | 8080 | Routes input to correct editor window |
| API Server | Node.js | 3000 | REST API + WebSocket for web UI |
| Control Panel | HTML/JS | — | Web dashboard for management |

---

## Quick Start

### Prerequisites

- **Windows 10/11** (uses Windows Raw Input API)
- **Node.js 18+** 
- **Python 3.10+**
- **Visual Studio Build Tools** (for C++ compilation)
- **Cursor or VS Code** installed

### One-Click Launch

```batch
start.bat
```

That's it. The batch file handles everything:
1. Builds the C++ service (if needed)
2. Installs Node.js dependencies
3. Starts all services
4. Opens the Control Panel in your browser

### Manual Setup

<details>
<summary>Click to expand manual instructions</summary>

**1. Build Raw Input Service**
```batch
cd raw_input_service
build.bat
```

**2. Install API Server Dependencies**
```batch
cd api_server
npm install
```

**3. Start Services (in order)**

Terminal 1 - Raw Input Service:
```batch
cd raw_input_service
raw_input_service_console.exe
```

Terminal 2 - Input Router Daemon:
```batch
cd input_router
python input_router.py run
```

Terminal 3 - API Server:
```batch
cd api_server
npm start
```

**4. Open Control Panel**

Open `control_panel/index.html` in your browser, or navigate to `http://localhost:3000`

</details>

---

## Usage

### 1. Connect Your Devices

Plug in multiple keyboards and/or mice. The Raw Input Service will detect them automatically.

### 2. Open the Control Panel

The web dashboard shows all detected devices and their current assignments.

### 3. Assign Devices to Users

Use the dropdown next to each device to assign it to a user (user_1, user_2, etc.)

### 4. Launch Editors

Click "Launch" next to each user to start their Cursor/VS Code instance.

### 5. Start Coding

Each keyboard/mouse now controls only its assigned editor window.

---

## Configuration

Edit `input_router/config.json` to customize:

```json
{
  "users": {
    "user_1": {
      "project_dir": "C:\\Projects\\frontend",
      "editor": "cursor"
    },
    "user_2": {
      "project_dir": "C:\\Projects\\backend", 
      "editor": "vscode"
    }
  },
  "editor_paths": {
    "cursor": "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\cursor\\Cursor.exe",
    "vscode": "C:\\Program Files\\Microsoft VS Code\\Code.exe"
  }
}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Devices not detected | Run Raw Input Service as Administrator |
| Input not routing | Check device assignments in Control Panel |
| Editor won't launch | Verify editor path in config.json |
| WebSocket disconnected | Restart API Server |

---

## Project Structure

```
├── raw_input_service/     # C++ Windows service
│   ├── raw_input_service.cpp
│   ├── device_detector.cpp
│   ├── socket_server.cpp
│   └── build.bat
├── input_router/          # Python daemon
│   ├── input_router.py
│   └── config.json
├── api_server/            # Node.js API
│   ├── server.js
│   ├── routes/api.js
│   └── lib/daemon-client.js
├── control_panel/         # Web UI
│   └── index.html
├── start.bat              # One-click launcher
└── README.md
```

---

## Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features  
- Submit PRs

---

## License

**Personal Use Only** — No commercial use, no corporate use, no forking for business.  
See [LICENSE](LICENSE) for details. For commercial inquiries, DM me.

---

<p align="center">
  <strong>Built for developers who share desks, not keyboards.</strong>
</p>

<p align="center">
  <a href="https://x.com/INSIDOOOR69">
    <img src="https://img.shields.io/badge/Questions%3F-DM%20me%20on%20Twitter-1DA1F2?style=flat-square&logo=twitter" alt="Twitter DM">
  </a>
</p>

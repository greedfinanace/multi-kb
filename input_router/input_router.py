#!/usr/bin/env python3
"""
Input Router Daemon
Bridges Raw Input Service (C++) and target applications (Cursor/VS Code)
Routes keyboard/mouse input from multiple devices to separate editor instances.
"""

import socket
import json
import time
import logging
import signal
import sys
import os
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from pathlib import Path
import ctypes
from ctypes import wintypes

# Windows API constants
INPUT_KEYBOARD = 1
INPUT_MOUSE = 0
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000

# Raw Input button flags (from Windows headers)
RI_MOUSE_LEFT_BUTTON_DOWN = 0x0001
RI_MOUSE_LEFT_BUTTON_UP = 0x0002
RI_MOUSE_RIGHT_BUTTON_DOWN = 0x0004
RI_MOUSE_RIGHT_BUTTON_UP = 0x0008
RI_MOUSE_MIDDLE_BUTTON_DOWN = 0x0010
RI_MOUSE_MIDDLE_BUTTON_UP = 0x0020

# Window message constants for PostMessage (no focus switch!)
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102

# Windows API structures
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]

# Load Windows DLLs
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


@dataclass
class UserSession:
    """Represents a user's editor session"""
    user_id: str
    process: Optional[subprocess.Popen] = None
    hwnd: Optional[int] = None
    project_dir: str = ""
    editor: str = "cursor"
    pid: int = 0


class InputRouter:
    """Main daemon class for routing input between devices and editor instances"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config: Dict = {}
        self.device_mappings: Dict[str, str] = {}
        self.user_sessions: Dict[str, UserSession] = {}
        self.running = False
        self.socket: Optional[socket.socket] = None
        self.last_active_user: Optional[str] = None
        self.lock = threading.Lock()
        
        # Setup logging
        self._setup_logging()
        
        # Load configuration
        self._load_config()
    
    def _setup_logging(self):
        """Configure logging to file and console"""
        log_format = '%(asctime)s [%(levelname)s] %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('input_router.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('InputRouter')
    
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                self.device_mappings = self.config.get('device_mappings', {})
                self.logger.info(f"Loaded config from {self.config_path}")
                self.logger.info(f"Device mappings: {self.device_mappings}")
            else:
                self.logger.warning(f"Config file not found: {self.config_path}")
                self._create_default_config()
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration"""
        self.config = {
            "raw_input_service": {"host": "127.0.0.1", "port": 9999},
            "device_mappings": {},
            "users": {
                "user_1": {"project_dir": "C:\\Projects\\user1", "editor": "cursor"},
                "user_2": {"project_dir": "C:\\Projects\\user2", "editor": "cursor"}
            },
            "editor_paths": {
                "cursor": "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\cursor\\Cursor.exe",
                "vscode": "C:\\Program Files\\Microsoft VS Code\\Code.exe"
            },
            "settings": {"focus_delay_ms": 50, "reconnect_delay_s": 5}
        }
        self._save_config()
    
    def _save_config(self):
        """Save current configuration to file"""
        try:
            self.config['device_mappings'] = self.device_mappings
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info("Configuration saved")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def add_device_mapping(self, device_id: str, user_id: str):
        """Add or update a device mapping"""
        with self.lock:
            self.device_mappings[device_id] = user_id
            self._save_config()
            self.logger.info(f"Mapped device '{device_id}' to '{user_id}'")
    
    def remove_device_mapping(self, device_id: str):
        """Remove a device mapping"""
        with self.lock:
            if device_id in self.device_mappings:
                del self.device_mappings[device_id]
                self._save_config()
                self.logger.info(f"Removed mapping for device '{device_id}'")


    def _get_editor_path(self, editor: str) -> str:
        """Get the full path to the editor executable"""
        paths = self.config.get('editor_paths', {})
        path = paths.get(editor, paths.get('cursor', 'cursor.exe'))
        # Expand environment variables
        return os.path.expandvars(path)
    
    def launch_editor(self, user_id: str) -> Optional[UserSession]:
        """Launch an editor instance for a user"""
        users_config = self.config.get('users', {})
        if user_id not in users_config:
            self.logger.error(f"User '{user_id}' not found in config")
            return None
        
        user_config = users_config[user_id]
        project_dir = user_config.get('project_dir', '')
        editor = user_config.get('editor', 'cursor')
        editor_path = self._get_editor_path(editor)
        
        try:
            # Launch editor with project directory
            cmd = [editor_path]
            if project_dir and os.path.exists(project_dir):
                cmd.append(project_dir)
            
            self.logger.info(f"Launching {editor} for {user_id}: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            
            session = UserSession(
                user_id=user_id,
                process=process,
                project_dir=project_dir,
                editor=editor,
                pid=process.pid
            )
            
            # Wait a bit for window to appear, then find HWND
            time.sleep(2)
            session.hwnd = self._find_window_by_pid(process.pid)
            
            if session.hwnd:
                self.logger.info(f"Found window handle {session.hwnd} for {user_id}")
            else:
                self.logger.warning(f"Could not find window for {user_id}, will retry later")
            
            self.user_sessions[user_id] = session
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to launch editor for {user_id}: {e}")
            return None
    
    def _find_window_by_pid(self, pid: int) -> Optional[int]:
        """Find window handle by process ID"""
        result = []
        
        def enum_callback(hwnd, _):
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value == pid:
                if user32.IsWindowVisible(hwnd):
                    result.append(hwnd)
            return True
        
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        
        return result[0] if result else None
    
    def _find_window_by_title(self, title_part: str) -> Optional[int]:
        """Find window handle by partial title match"""
        result = []
        
        def enum_callback(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd) + 1
                buffer = ctypes.create_unicode_buffer(length)
                user32.GetWindowTextW(hwnd, buffer, length)
                if title_part.lower() in buffer.value.lower():
                    result.append(hwnd)
            return True
        
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        
        return result[0] if result else None
    
    def list_open_windows(self) -> list:
        """List all open windows that could be editor targets"""
        windows = []
        
        def enum_callback(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd) + 1
                if length > 1:
                    buffer = ctypes.create_unicode_buffer(length)
                    user32.GetWindowTextW(hwnd, buffer, length)
                    title = buffer.value
                    # Filter for likely editor windows
                    if any(kw in title.lower() for kw in ['cursor', 'code', 'kiro', 'visual studio', 'notepad', 'sublime', 'atom']):
                        # Get process ID
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        windows.append({
                            'hwnd': hwnd,
                            'title': title,
                            'pid': pid.value
                        })
            return True
        
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        
        return windows
    
    def attach_to_window(self, user_id: str, hwnd: int) -> bool:
        """Attach a user session to an existing window (no launch needed)"""
        # Verify window exists
        if not user32.IsWindow(hwnd):
            self.logger.error(f"Window {hwnd} does not exist")
            return False
        
        # Get window title for logging
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buffer, length)
        title = buffer.value
        
        # Create or update session
        session = UserSession(
            user_id=user_id,
            process=None,  # No process - attached to existing window
            hwnd=hwnd,
            project_dir="",
            editor="attached",
            pid=0
        )
        
        self.user_sessions[user_id] = session
        self.logger.info(f"Attached {user_id} to window: {title} (hwnd={hwnd})")
        return True
    
    def _refresh_window_handle(self, session: UserSession) -> bool:
        """Refresh window handle for a session"""
        if session.process and session.process.poll() is None:
            hwnd = self._find_window_by_pid(session.pid)
            if hwnd:
                session.hwnd = hwnd
                return True
        return False


    def set_foreground_window(self, hwnd: int) -> bool:
        """Bring window to foreground"""
        try:
            # Check if window still exists
            if not user32.IsWindow(hwnd):
                return False
            
            # Restore if minimized
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            
            # Set foreground
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set foreground window: {e}")
            return False
    
    def inject_keyboard(self, vkey: int, key_up: bool = False):
        """Inject a keyboard event using SendInput (legacy, requires focus)"""
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki.wVk = vkey
        inp.union.ki.wScan = user32.MapVirtualKeyW(vkey, 0)
        inp.union.ki.dwFlags = KEYEVENTF_KEYUP if key_up else 0
        inp.union.ki.time = 0
        inp.union.ki.dwExtraInfo = None
        
        result = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if result != 1:
            self.logger.warning(f"SendInput keyboard failed: {kernel32.GetLastError()}")
    
    def inject_keyboard_to_window(self, hwnd: int, vkey: int):
        """Inject keyboard event directly to a window using PostMessage (NO FOCUS SWITCH!)"""
        # Get scan code for the virtual key
        scan_code = user32.MapVirtualKeyW(vkey, 0)
        
        # Build lParam for key messages
        # Bits 0-15: repeat count (1)
        # Bits 16-23: scan code
        # Bit 24: extended key flag
        # Bits 25-28: reserved
        # Bit 29: context code (0 for WM_KEYDOWN)
        # Bit 30: previous key state (0 for down, 1 for up)
        # Bit 31: transition state (0 for down, 1 for up)
        
        lparam_down = (scan_code << 16) | 1
        lparam_up = (scan_code << 16) | 1 | (1 << 30) | (1 << 31)
        
        # Post key down
        user32.PostMessageW(hwnd, WM_KEYDOWN, vkey, lparam_down)
        
        # Post WM_CHAR for printable characters
        char_code = user32.MapVirtualKeyW(vkey, 2)  # MAPVK_VK_TO_CHAR
        if char_code > 0:
            user32.PostMessageW(hwnd, WM_CHAR, char_code, lparam_down)
        
        # Post key up
        user32.PostMessageW(hwnd, WM_KEYUP, vkey, lparam_up)
    
    def inject_mouse_move(self, dx: int, dy: int, absolute: bool = False):
        """Inject mouse movement"""
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dx = dx
        inp.union.mi.dy = dy
        inp.union.mi.mouseData = 0
        inp.union.mi.dwFlags = MOUSEEVENTF_MOVE
        if absolute:
            inp.union.mi.dwFlags |= MOUSEEVENTF_ABSOLUTE
        inp.union.mi.time = 0
        inp.union.mi.dwExtraInfo = None
        
        result = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if result != 1:
            self.logger.warning(f"SendInput mouse move failed: {kernel32.GetLastError()}")
    
    def inject_mouse_button(self, buttons: int):
        """Inject mouse button events based on raw input button flags"""
        flags = 0
        
        if buttons & RI_MOUSE_LEFT_BUTTON_DOWN:
            flags |= MOUSEEVENTF_LEFTDOWN
        if buttons & RI_MOUSE_LEFT_BUTTON_UP:
            flags |= MOUSEEVENTF_LEFTUP
        if buttons & RI_MOUSE_RIGHT_BUTTON_DOWN:
            flags |= MOUSEEVENTF_RIGHTDOWN
        if buttons & RI_MOUSE_RIGHT_BUTTON_UP:
            flags |= MOUSEEVENTF_RIGHTUP
        if buttons & RI_MOUSE_MIDDLE_BUTTON_DOWN:
            flags |= MOUSEEVENTF_MIDDLEDOWN
        if buttons & RI_MOUSE_MIDDLE_BUTTON_UP:
            flags |= MOUSEEVENTF_MIDDLEUP
        
        if flags == 0:
            return
        
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dx = 0
        inp.union.mi.dy = 0
        inp.union.mi.mouseData = 0
        inp.union.mi.dwFlags = flags
        inp.union.mi.time = 0
        inp.union.mi.dwExtraInfo = None
        
        result = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if result != 1:
            self.logger.warning(f"SendInput mouse button failed: {kernel32.GetLastError()}")


    def route_event(self, event: Dict):
        """Route an input event to the appropriate user's window"""
        device_id = event.get('device_id', '')
        event_type = event.get('type', '')
        
        # Find user for this device
        user_id = self.device_mappings.get(device_id)
        if not user_id:
            # Unknown device - log it for mapping
            self.logger.debug(f"Unknown device: {device_id}")
            return
        
        # Get user session
        session = self.user_sessions.get(user_id)
        if not session:
            self.logger.warning(f"No session for user {user_id}")
            return
        
        # Check if process is still running
        if session.process and session.process.poll() is not None:
            self.logger.warning(f"Process for {user_id} has terminated")
            session.hwnd = None
            return
        
        # Refresh window handle if needed
        if not session.hwnd:
            if not self._refresh_window_handle(session):
                self.logger.warning(f"Cannot find window for {user_id}")
                return
        
        # Check if window still exists
        if not user32.IsWindow(session.hwnd):
            self._refresh_window_handle(session)
            if not session.hwnd:
                return
        
        # Inject the input - NO FOCUS SWITCHING for keyboard!
        if event_type == 'keyboard':
            vkey = event.get('vkey', 0)
            # Use PostMessage - sends directly to window without focus change
            self.inject_keyboard_to_window(session.hwnd, vkey)
            self.logger.debug(f"Posted key {vkey} to {user_id} (hwnd={session.hwnd})")
            
        elif event_type == 'mouse':
            dx = event.get('dx', 0)
            dy = event.get('dy', 0)
            buttons = event.get('buttons', 0)
            
            # Inject movement
            if dx != 0 or dy != 0:
                self.inject_mouse_move(dx, dy)
            
            # Inject button events
            if buttons != 0:
                self.inject_mouse_button(buttons)
            
            self.logger.debug(f"Injected mouse dx={dx} dy={dy} buttons={buttons} to {user_id}")


    def connect_to_service(self) -> bool:
        """Connect to Raw Input Service"""
        host = self.config.get('raw_input_service', {}).get('host', '127.0.0.1')
        port = self.config.get('raw_input_service', {}).get('port', 9999)
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((host, port))
            self.socket.settimeout(None)
            self.logger.info(f"Connected to Raw Input Service at {host}:{port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Raw Input Service: {e}")
            self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from Raw Input Service"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def event_loop(self):
        """Main event processing loop"""
        buffer = ""
        
        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.logger.warning("Server disconnected")
                    break
                
                buffer += data.decode('utf-8')
                
                # Process complete JSON lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            event = json.loads(line)
                            self.route_event(event)
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON parse error: {e}")
                            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Event loop error: {e}")
                break
    
    def run(self):
        """Main daemon run loop with reconnection"""
        self.running = True
        reconnect_delay = self.config.get('settings', {}).get('reconnect_delay_s', 5)
        
        self.logger.info("Input Router Daemon starting...")
        
        while self.running:
            if self.connect_to_service():
                self.event_loop()
            
            if self.running:
                self.logger.info(f"Reconnecting in {reconnect_delay} seconds...")
                time.sleep(reconnect_delay)
        
        self.disconnect()
        self.logger.info("Input Router Daemon stopped")
    
    def stop(self):
        """Stop the daemon"""
        self.logger.info("Stopping daemon...")
        self.running = False
        self.disconnect()
        
        # Terminate launched processes
        for user_id, session in self.user_sessions.items():
            if session.process and session.process.poll() is None:
                self.logger.info(f"Terminating editor for {user_id}")
                session.process.terminate()


class HTTPConfigServer:
    """Simple HTTP server for configuration API"""
    
    def __init__(self, router: InputRouter, port: int = 8080):
        self.router = router
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        """Start HTTP server in background thread"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import urllib.parse
        
        router = self.router
        
        class ConfigHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                router.logger.debug(f"HTTP: {format % args}")
            
            def do_GET(self):
                if self.path == '/mappings':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(router.device_mappings).encode())
                elif self.path == '/sessions':
                    sessions = {
                        uid: {'hwnd': s.hwnd, 'pid': s.pid, 'editor': s.editor}
                        for uid, s in router.user_sessions.items()
                    }
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(sessions).encode())
                elif self.path == '/config':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(router.config).encode())
                elif self.path == '/status':
                    status = {
                        'running': router.running,
                        'connected': router.socket is not None,
                        'sessions': len(router.user_sessions),
                        'mappings': len(router.device_mappings)
                    }
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(status).encode())
                elif self.path == '/windows':
                    # NEW: List all open editor windows for attachment
                    windows = router.list_open_windows()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(windows).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_POST(self):
                if self.path == '/mapping':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        device_id = data.get('device_id')
                        user_id = data.get('user_id')
                        if device_id and user_id:
                            router.add_device_mapping(device_id, user_id)
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(b'{"status":"ok"}')
                        else:
                            self.send_response(400)
                            self.end_headers()
                    except:
                        self.send_response(400)
                        self.end_headers()
                elif self.path == '/launch':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        user_id = data.get('user_id')
                        if user_id:
                            session = router.launch_editor(user_id)
                            if session:
                                self.send_response(200)
                                self.send_header('Content-Type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({
                                    'status': 'ok',
                                    'pid': session.pid,
                                    'hwnd': session.hwnd
                                }).encode())
                            else:
                                self.send_response(500)
                                self.end_headers()
                        else:
                            self.send_response(400)
                            self.end_headers()
                    except:
                        self.send_response(400)
                        self.end_headers()
                elif self.path == '/stop':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        user_id = data.get('user_id')
                        if user_id and user_id in router.user_sessions:
                            session = router.user_sessions[user_id]
                            if session.process and session.process.poll() is None:
                                session.process.terminate()
                                session.process.wait(timeout=5)
                            del router.user_sessions[user_id]
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(b'{"status":"ok"}')
                        else:
                            self.send_response(404)
                            self.end_headers()
                    except:
                        self.send_response(400)
                        self.end_headers()
                elif self.path == '/config':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        router.config.update(data)
                        if 'device_mappings' in data:
                            router.device_mappings = data['device_mappings']
                        router._save_config()
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"status":"ok"}')
                    except:
                        self.send_response(400)
                        self.end_headers()
                elif self.path == '/attach':
                    # NEW: Attach user to an existing window (no launch needed)
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        user_id = data.get('user_id')
                        hwnd = data.get('hwnd')
                        if user_id and hwnd:
                            success = router.attach_to_window(user_id, int(hwnd))
                            if success:
                                self.send_response(200)
                                self.send_header('Content-Type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({
                                    'status': 'ok',
                                    'user_id': user_id,
                                    'hwnd': hwnd
                                }).encode())
                            else:
                                self.send_response(400)
                                self.send_header('Content-Type', 'application/json')
                                self.end_headers()
                                self.wfile.write(b'{"error":"Window not found"}')
                        else:
                            self.send_response(400)
                            self.end_headers()
                    except:
                        self.send_response(400)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_DELETE(self):
                if self.path.startswith('/mapping/'):
                    device_id = urllib.parse.unquote(self.path[9:])
                    router.remove_device_mapping(device_id)
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
        
        self.server = HTTPServer(('127.0.0.1', self.port), ConfigHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.router.logger.info(f"HTTP config server started on port {self.port}")
    
    def stop(self):
        if self.server:
            self.server.shutdown()


def print_usage():
    """Print CLI usage"""
    print("""
Input Router Daemon - Routes input from multiple devices to separate editor instances

Usage:
    python input_router.py [command] [options]

Commands:
    run                     Start the daemon (default)
    map <device_id> <user>  Add device mapping
    unmap <device_id>       Remove device mapping
    launch <user_id>        Launch editor for user
    list                    List current mappings
    help                    Show this help

Examples:
    python input_router.py run
    python input_router.py map kb-001 user_1
    python input_router.py map mouse-001 user_1
    python input_router.py launch user_1
    python input_router.py list

HTTP API (when daemon is running):
    GET  /mappings          - Get all device mappings
    GET  /sessions          - Get active sessions
    POST /mapping           - Add mapping {"device_id": "...", "user_id": "..."}
    POST /launch            - Launch editor {"user_id": "..."}
    DELETE /mapping/<id>    - Remove mapping
""")


def main():
    """Main entry point"""
    # Check for admin privileges
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
    
    if not is_admin:
        print("WARNING: Running without admin privileges. Some features may not work.")
        print("Consider running as Administrator for full functionality.\n")
    
    # Parse command line
    args = sys.argv[1:] if len(sys.argv) > 1 else ['run']
    command = args[0].lower()
    
    config_path = "config.json"
    
    if command == 'help' or command == '-h' or command == '--help':
        print_usage()
        return
    
    router = InputRouter(config_path)
    
    if command == 'run':
        # Setup signal handlers
        def signal_handler(sig, frame):
            print("\nShutdown requested...")
            router.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start HTTP config server
        http_server = HTTPConfigServer(router, port=8080)
        http_server.start()
        
        # Launch editors for configured users
        for user_id in router.config.get('users', {}).keys():
            router.launch_editor(user_id)
        
        # Run main loop
        try:
            router.run()
        finally:
            http_server.stop()
    
    elif command == 'map':
        if len(args) < 3:
            print("Usage: python input_router.py map <device_id> <user_id>")
            return
        device_id = args[1]
        user_id = args[2]
        router.add_device_mapping(device_id, user_id)
        print(f"Mapped '{device_id}' -> '{user_id}'")
    
    elif command == 'unmap':
        if len(args) < 2:
            print("Usage: python input_router.py unmap <device_id>")
            return
        device_id = args[1]
        router.remove_device_mapping(device_id)
        print(f"Removed mapping for '{device_id}'")
    
    elif command == 'launch':
        if len(args) < 2:
            print("Usage: python input_router.py launch <user_id>")
            return
        user_id = args[1]
        session = router.launch_editor(user_id)
        if session:
            print(f"Launched editor for '{user_id}' (PID: {session.pid})")
        else:
            print(f"Failed to launch editor for '{user_id}'")
    
    elif command == 'list':
        print("Device Mappings:")
        for device_id, user_id in router.device_mappings.items():
            print(f"  {device_id} -> {user_id}")
        if not router.device_mappings:
            print("  (none)")
    
    else:
        print(f"Unknown command: {command}")
        print_usage()


if __name__ == '__main__':
    main()

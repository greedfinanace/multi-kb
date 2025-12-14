#!/usr/bin/env python3
"""
Test client for Raw Input Service
Connects to the TCP server and displays incoming events
"""

import socket
import json
import sys

HOST = '127.0.0.1'
PORT = 9999

def main():
    print(f"Connecting to Raw Input Service at {HOST}:{PORT}...")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((HOST, PORT))
            print("Connected! Waiting for input events...")
            print("Press keys or move mice to see events.")
            print("Press Ctrl+C to exit.\n")
            
            buffer = ""
            while True:
                data = sock.recv(4096)
                if not data:
                    print("Server disconnected")
                    break
                
                buffer += data.decode('utf-8')
                
                # Process complete JSON lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            event = json.loads(line)
                            
                            # Pretty print the event
                            device_id = event.get('device_id', 'unknown')
                            event_type = event.get('type', 'unknown')
                            timestamp = event.get('timestamp', 0)
                            
                            if event_type == 'keyboard':
                                vkey = event.get('vkey', 0)
                                # Try to get key name
                                key_name = chr(vkey) if 32 <= vkey <= 126 else f"VK_{vkey}"
                                print(f"[{timestamp}] KEYBOARD {device_id}: Key={key_name} (VK={vkey})")
                            
                            elif event_type == 'mouse':
                                dx = event.get('dx', 0)
                                dy = event.get('dy', 0)
                                buttons = event.get('buttons', 0)
                                print(f"[{timestamp}] MOUSE {device_id}: dx={dx:+4d} dy={dy:+4d} buttons={buttons}")
                            
                            else:
                                print(f"[{timestamp}] UNKNOWN: {line}")
                                
                        except json.JSONDecodeError as e:
                            print(f"JSON parse error: {e}")
                            print(f"Raw data: {line}")
                            
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {HOST}:{PORT}")
        print("Make sure raw_input_service.exe is running.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDisconnected.")

if __name__ == '__main__':
    main()

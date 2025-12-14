// raw_input_service.cpp - Main application with Raw Input handling
#include "common.h"
#include "device_detector.h"
#include "socket_server.h"

// Window class name
const wchar_t* WINDOW_CLASS = L"RawInputServiceClass";

// Global flag for clean shutdown
std::atomic<bool> g_running(true);

// Process raw input data
void processRawInput(LPARAM lParam) {
    UINT dwSize = 0;
    
    // Get required buffer size
    if (GetRawInputData((HRAWINPUT)lParam, RID_INPUT, nullptr, &dwSize, sizeof(RAWINPUTHEADER)) != 0) {
        return;
    }

    std::vector<BYTE> buffer(dwSize);
    if (GetRawInputData((HRAWINPUT)lParam, RID_INPUT, buffer.data(), &dwSize, sizeof(RAWINPUTHEADER)) != dwSize) {
        return;
    }

    RAWINPUT* raw = reinterpret_cast<RAWINPUT*>(buffer.data());
    
    InputEvent event = {};
    event.device_id = deviceHandleToId(raw->header.hDevice);
    event.timestamp = GetTickCount64();

    // Check if device is known, if not add it
    DeviceInfo* deviceInfo = DeviceDetector::instance().getDevice(raw->header.hDevice);
    
    if (raw->header.dwType == RIM_TYPEKEYBOARD) {
        event.type = DeviceType::Keyboard;
        event.data.keyboard.vkey = raw->data.keyboard.VKey;
        
        // Only send key down events (not key up) to reduce noise
        // Remove this check if you want both key down and key up
        if (raw->data.keyboard.Flags & RI_KEY_BREAK) {
            return; // Key up event, skip
        }

        if (!deviceInfo) {
            DeviceDetector::instance().addDevice(raw->header.hDevice, DeviceType::Keyboard);
        }
    }
    else if (raw->header.dwType == RIM_TYPEMOUSE) {
        event.type = DeviceType::Mouse;
        event.data.mouse.dx = raw->data.mouse.lLastX;
        event.data.mouse.dy = raw->data.mouse.lLastY;
        event.data.mouse.buttons = raw->data.mouse.usButtonFlags;

        // Skip events with no movement and no button changes
        if (event.data.mouse.dx == 0 && event.data.mouse.dy == 0 && event.data.mouse.buttons == 0) {
            return;
        }

        if (!deviceInfo) {
            DeviceDetector::instance().addDevice(raw->header.hDevice, DeviceType::Mouse);
        }
    }
    else {
        return; // Unknown device type
    }

    // Format and broadcast the event
    std::string json = formatEventJson(event);
    SocketServer::instance().broadcast(json);
}

// Window procedure
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
        case WM_INPUT:
            processRawInput(lParam);
            return 0;

        case WM_INPUT_DEVICE_CHANGE:
            // Device added or removed
            if (wParam == GIDC_ARRIVAL) {
                LOG("Device arrival detected");
                DeviceDetector::instance().enumerateDevices();
            } else if (wParam == GIDC_REMOVAL) {
                LOG("Device removal detected");
                DeviceDetector::instance().enumerateDevices();
            }
            return 0;

        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;

        default:
            return DefWindowProc(hwnd, uMsg, wParam, lParam);
    }
}

// Register for raw input
bool registerRawInput(HWND hwnd) {
    RAWINPUTDEVICE rid[2];

    // Keyboard
    rid[0].usUsagePage = 0x01;  // Generic Desktop
    rid[0].usUsage = 0x06;      // Keyboard
    rid[0].dwFlags = RIDEV_INPUTSINK | RIDEV_DEVNOTIFY;
    rid[0].hwndTarget = hwnd;

    // Mouse
    rid[1].usUsagePage = 0x01;  // Generic Desktop
    rid[1].usUsage = 0x02;      // Mouse
    rid[1].dwFlags = RIDEV_INPUTSINK | RIDEV_DEVNOTIFY;
    rid[1].hwndTarget = hwnd;

    if (!RegisterRawInputDevices(rid, 2, sizeof(RAWINPUTDEVICE))) {
        LOG("Failed to register raw input devices: " + std::to_string(GetLastError()));
        return false;
    }

    LOG("Raw input devices registered successfully");
    return true;
}

// Create hidden window for receiving messages
HWND createHiddenWindow(HINSTANCE hInstance) {
    WNDCLASSEXW wc = {};
    wc.cbSize = sizeof(WNDCLASSEXW);
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = WINDOW_CLASS;

    if (!RegisterClassExW(&wc)) {
        LOG("Failed to register window class: " + std::to_string(GetLastError()));
        return nullptr;
    }

    HWND hwnd = CreateWindowExW(
        0,
        WINDOW_CLASS,
        L"Raw Input Service",
        0,  // No visible style
        0, 0, 0, 0,
        HWND_MESSAGE,  // Message-only window
        nullptr,
        hInstance,
        nullptr
    );

    if (!hwnd) {
        LOG("Failed to create window: " + std::to_string(GetLastError()));
    }

    return hwnd;
}

// Console control handler for graceful shutdown
BOOL WINAPI ConsoleHandler(DWORD signal) {
    if (signal == CTRL_C_EVENT || signal == CTRL_BREAK_EVENT || signal == CTRL_CLOSE_EVENT) {
        LOG("Shutdown signal received");
        g_running = false;
        PostQuitMessage(0);
        return TRUE;
    }
    return FALSE;
}


// Entry point - supports both console and Windows subsystem
int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPWSTR lpCmdLine, int nCmdShow) {
    (void)hPrevInstance;
    (void)lpCmdLine;
    (void)nCmdShow;

    // Initialize logger
    Logger::instance().init("raw_input_service.log");
    LOG("=== Raw Input Service Starting ===");

    // Set console handler if running with console
    SetConsoleCtrlHandler(ConsoleHandler, TRUE);

    // Start TCP server
    if (!SocketServer::instance().start(TCP_PORT)) {
        LOG("Failed to start TCP server");
        return 1;
    }

    // Enumerate existing devices
    DeviceDetector::instance().enumerateDevices();

    // Create hidden window
    HWND hwnd = createHiddenWindow(hInstance);
    if (!hwnd) {
        LOG("Failed to create hidden window");
        SocketServer::instance().stop();
        return 1;
    }

    // Register for raw input
    if (!registerRawInput(hwnd)) {
        LOG("Failed to register raw input");
        DestroyWindow(hwnd);
        SocketServer::instance().stop();
        return 1;
    }

    LOG("Service running. Listening on port " + std::to_string(TCP_PORT));
    LOG("Press Ctrl+C to stop");

    // Message loop
    MSG msg;
    while (g_running && GetMessage(&msg, nullptr, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    // Cleanup
    LOG("Shutting down...");
    SocketServer::instance().stop();
    DestroyWindow(hwnd);
    UnregisterClassW(WINDOW_CLASS, hInstance);
    
    LOG("=== Raw Input Service Stopped ===");
    return 0;
}

// Alternative main() for console builds
int main() {
    return wWinMain(GetModuleHandle(nullptr), nullptr, nullptr, SW_HIDE);
}

// common.h - Shared definitions and utilities
#pragma once

#define WIN32_LEAN_AND_MEAN
#define _WINSOCK_DEPRECATED_NO_WARNINGS

#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <hidsdi.h>
#include <setupapi.h>
#include <string>
#include <vector>
#include <mutex>
#include <fstream>
#include <ctime>
#include <sstream>
#include <iomanip>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "hid.lib")
#pragma comment(lib, "setupapi.lib")

constexpr int TCP_PORT = 9999;
constexpr int MAX_CLIENTS = 10;
constexpr size_t BUFFER_SIZE = 4096;

// Device types
enum class DeviceType {
    Keyboard,
    Mouse,
    Unknown
};

// Input event structure
struct InputEvent {
    std::string device_id;
    DeviceType type;
    union {
        struct { int vkey; } keyboard;
        struct { int dx; int dy; int buttons; } mouse;
    } data;
    ULONGLONG timestamp;
};

// Logger class
class Logger {
public:
    static Logger& instance() {
        static Logger inst;
        return inst;
    }

    void log(const std::string& message) {
        std::lock_guard<std::mutex> lock(mutex_);
        std::time_t now = std::time(nullptr);
        char timeStr[64];
        std::strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
        
        if (logFile_.is_open()) {
            logFile_ << "[" << timeStr << "] " << message << std::endl;
            logFile_.flush();
        }
    }

    void init(const std::string& filename) {
        std::lock_guard<std::mutex> lock(mutex_);
        logFile_.open(filename, std::ios::app);
    }

private:
    Logger() = default;
    std::ofstream logFile_;
    std::mutex mutex_;
};

#define LOG(msg) Logger::instance().log(msg)

// Convert device handle to hex string ID
inline std::string deviceHandleToId(HANDLE hDevice) {
    std::stringstream ss;
    ss << "0x" << std::uppercase << std::hex << reinterpret_cast<uintptr_t>(hDevice);
    return ss.str();
}

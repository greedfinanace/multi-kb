// device_detector.h - HID device enumeration
#pragma once
#include "common.h"
#include <map>

struct DeviceInfo {
    HANDLE handle;
    DeviceType type;
    std::wstring name;
    std::string id;
};

class DeviceDetector {
public:
    static DeviceDetector& instance() {
        static DeviceDetector inst;
        return inst;
    }

    void enumerateDevices();
    DeviceInfo* getDevice(HANDLE hDevice);
    std::vector<DeviceInfo> getAllDevices() const;
    void addDevice(HANDLE hDevice, DeviceType type);
    void removeDevice(HANDLE hDevice);

private:
    DeviceDetector() = default;
    std::map<HANDLE, DeviceInfo> devices_;
    std::mutex mutex_;
    
    std::wstring getDeviceName(HANDLE hDevice);
};

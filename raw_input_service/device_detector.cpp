// device_detector.cpp - HID device enumeration implementation
#include "device_detector.h"

void DeviceDetector::enumerateDevices() {
    std::lock_guard<std::mutex> lock(mutex_);
    devices_.clear();

    UINT numDevices = 0;
    if (GetRawInputDeviceList(nullptr, &numDevices, sizeof(RAWINPUTDEVICELIST)) != 0) {
        LOG("Failed to get raw input device count");
        return;
    }

    if (numDevices == 0) {
        LOG("No raw input devices found");
        return;
    }

    std::vector<RAWINPUTDEVICELIST> deviceList(numDevices);
    if (GetRawInputDeviceList(deviceList.data(), &numDevices, sizeof(RAWINPUTDEVICELIST)) == (UINT)-1) {
        LOG("Failed to enumerate raw input devices");
        return;
    }

    for (const auto& device : deviceList) {
        DeviceType type = DeviceType::Unknown;
        
        if (device.dwType == RIM_TYPEKEYBOARD) {
            type = DeviceType::Keyboard;
        } else if (device.dwType == RIM_TYPEMOUSE) {
            type = DeviceType::Mouse;
        } else {
            continue; // Skip HID devices that aren't keyboard/mouse
        }

        DeviceInfo info;
        info.handle = device.hDevice;
        info.type = type;
        info.name = getDeviceName(device.hDevice);
        info.id = deviceHandleToId(device.hDevice);

        devices_[device.hDevice] = info;

        std::string typeStr = (type == DeviceType::Keyboard) ? "Keyboard" : "Mouse";
        LOG("Found device: " + typeStr + " ID=" + info.id);
    }

    LOG("Total devices enumerated: " + std::to_string(devices_.size()));
}

std::wstring DeviceDetector::getDeviceName(HANDLE hDevice) {
    UINT nameSize = 0;
    if (GetRawInputDeviceInfoW(hDevice, RIDI_DEVICENAME, nullptr, &nameSize) != 0) {
        return L"Unknown";
    }

    std::wstring name(nameSize, L'\0');
    if (GetRawInputDeviceInfoW(hDevice, RIDI_DEVICENAME, &name[0], &nameSize) == (UINT)-1) {
        return L"Unknown";
    }

    // Remove trailing null if present
    if (!name.empty() && name.back() == L'\0') {
        name.pop_back();
    }

    return name;
}

DeviceInfo* DeviceDetector::getDevice(HANDLE hDevice) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = devices_.find(hDevice);
    if (it != devices_.end()) {
        return &it->second;
    }
    return nullptr;
}

std::vector<DeviceInfo> DeviceDetector::getAllDevices() const {
    std::vector<DeviceInfo> result;
    for (const auto& pair : devices_) {
        result.push_back(pair.second);
    }
    return result;
}

void DeviceDetector::addDevice(HANDLE hDevice, DeviceType type) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    if (devices_.find(hDevice) != devices_.end()) {
        return; // Already exists
    }

    DeviceInfo info;
    info.handle = hDevice;
    info.type = type;
    info.name = getDeviceName(hDevice);
    info.id = deviceHandleToId(hDevice);

    devices_[hDevice] = info;
    
    std::string typeStr = (type == DeviceType::Keyboard) ? "Keyboard" : "Mouse";
    LOG("Device added: " + typeStr + " ID=" + info.id);
}

void DeviceDetector::removeDevice(HANDLE hDevice) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = devices_.find(hDevice);
    if (it != devices_.end()) {
        LOG("Device removed: ID=" + it->second.id);
        devices_.erase(it);
    }
}

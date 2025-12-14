cmake_minimum_required(VERSION 3.15)
project(RawInputService VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Source files
set(SOURCES
    raw_input_service.cpp
    device_detector.cpp
    socket_server.cpp
)

set(HEADERS
    common.h
    device_detector.h
    socket_server.h
)

# Console version (shows console window, useful for debugging)
add_executable(raw_input_service_console ${SOURCES} ${HEADERS})
target_link_libraries(raw_input_service_console PRIVATE ws2_32 hid setupapi)

# Windows subsystem version (no console window, runs silently)
add_executable(raw_input_service WIN32 ${SOURCES} ${HEADERS})
target_link_libraries(raw_input_service PRIVATE ws2_32 hid setupapi)

# Set output directory
set_target_properties(raw_input_service raw_input_service_console
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Require admin privileges via manifest
if(MSVC)
    set_target_properties(raw_input_service raw_input_service_console
        PROPERTIES
        LINK_FLAGS "/MANIFESTUAC:\"level='requireAdministrator' uiAccess='false'\""
    )
endif()

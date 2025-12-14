// socket_server.cpp - TCP server implementation
#include "socket_server.h"

std::string formatEventJson(const InputEvent& event) {
    std::stringstream ss;
    ss << "{\"device_id\":\"" << event.device_id << "\",";
    
    if (event.type == DeviceType::Keyboard) {
        ss << "\"type\":\"keyboard\",";
        ss << "\"vkey\":" << event.data.keyboard.vkey << ",";
    } else if (event.type == DeviceType::Mouse) {
        ss << "\"type\":\"mouse\",";
        ss << "\"dx\":" << event.data.mouse.dx << ",";
        ss << "\"dy\":" << event.data.mouse.dy << ",";
        ss << "\"buttons\":" << event.data.mouse.buttons << ",";
    }
    
    ss << "\"timestamp\":" << event.timestamp << "}";
    return ss.str();
}

bool SocketServer::start(int port) {
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        LOG("WSAStartup failed");
        return false;
    }

    listenSocket_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listenSocket_ == INVALID_SOCKET) {
        LOG("Failed to create socket: " + std::to_string(WSAGetLastError()));
        WSACleanup();
        return false;
    }

    // Allow address reuse
    int opt = 1;
    setsockopt(listenSocket_, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

    sockaddr_in serverAddr = {};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(port);

    if (bind(listenSocket_, (sockaddr*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        LOG("Bind failed: " + std::to_string(WSAGetLastError()));
        closesocket(listenSocket_);
        WSACleanup();
        return false;
    }

    if (listen(listenSocket_, SOMAXCONN) == SOCKET_ERROR) {
        LOG("Listen failed: " + std::to_string(WSAGetLastError()));
        closesocket(listenSocket_);
        WSACleanup();
        return false;
    }

    running_ = true;
    acceptThread_ = std::thread(&SocketServer::acceptLoop, this);

    LOG("TCP server started on port " + std::to_string(port));
    return true;
}

void SocketServer::stop() {
    if (!running_) return;

    running_ = false;

    // Close listen socket to unblock accept()
    if (listenSocket_ != INVALID_SOCKET) {
        closesocket(listenSocket_);
        listenSocket_ = INVALID_SOCKET;
    }

    // Close all client connections
    {
        std::lock_guard<std::mutex> lock(clientsMutex_);
        for (SOCKET client : clients_) {
            closesocket(client);
        }
        clients_.clear();
    }

    if (acceptThread_.joinable()) {
        acceptThread_.join();
    }

    WSACleanup();
    LOG("TCP server stopped");
}

void SocketServer::acceptLoop() {
    while (running_) {
        sockaddr_in clientAddr;
        int addrLen = sizeof(clientAddr);
        
        SOCKET clientSocket = accept(listenSocket_, (sockaddr*)&clientAddr, &addrLen);
        
        if (clientSocket == INVALID_SOCKET) {
            if (running_) {
                LOG("Accept failed: " + std::to_string(WSAGetLastError()));
            }
            continue;
        }

        {
            std::lock_guard<std::mutex> lock(clientsMutex_);
            if (clients_.size() >= MAX_CLIENTS) {
                LOG("Max clients reached, rejecting connection");
                closesocket(clientSocket);
                continue;
            }
            clients_.insert(clientSocket);
        }

        char clientIP[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &clientAddr.sin_addr, clientIP, INET_ADDRSTRLEN);
        LOG("Client connected: " + std::string(clientIP));

        // Start client handler thread (detached - will clean up on disconnect)
        std::thread(&SocketServer::clientHandler, this, clientSocket).detach();
    }
}

void SocketServer::clientHandler(SOCKET clientSocket) {
    char buffer[BUFFER_SIZE];
    
    while (running_) {
        // Just wait for client disconnect or data (we don't process incoming data)
        int bytesReceived = recv(clientSocket, buffer, BUFFER_SIZE - 1, 0);
        
        if (bytesReceived <= 0) {
            break; // Client disconnected or error
        }
        // Ignore any incoming data - this is a one-way stream
    }

    {
        std::lock_guard<std::mutex> lock(clientsMutex_);
        clients_.erase(clientSocket);
    }
    
    closesocket(clientSocket);
    LOG("Client disconnected");
}

void SocketServer::broadcast(const std::string& message) {
    std::string data = message + "\n";
    
    std::lock_guard<std::mutex> lock(clientsMutex_);
    
    std::vector<SOCKET> deadClients;
    
    for (SOCKET client : clients_) {
        int result = send(client, data.c_str(), (int)data.length(), 0);
        if (result == SOCKET_ERROR) {
            deadClients.push_back(client);
        }
    }

    // Remove dead clients
    for (SOCKET dead : deadClients) {
        clients_.erase(dead);
        closesocket(dead);
    }
}

int SocketServer::getClientCount() const {
    return (int)clients_.size();
}

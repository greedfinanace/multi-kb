// socket_server.h - TCP server for streaming events
#pragma once
#include "common.h"
#include <set>
#include <thread>
#include <atomic>

class SocketServer {
public:
    static SocketServer& instance() {
        static SocketServer inst;
        return inst;
    }

    bool start(int port = TCP_PORT);
    void stop();
    void broadcast(const std::string& message);
    int getClientCount() const;

private:
    SocketServer() : running_(false), listenSocket_(INVALID_SOCKET) {}
    ~SocketServer() { stop(); }

    void acceptLoop();
    void clientHandler(SOCKET clientSocket);

    SOCKET listenSocket_;
    std::atomic<bool> running_;
    std::set<SOCKET> clients_;
    std::mutex clientsMutex_;
    std::thread acceptThread_;
};

// JSON formatter for events
std::string formatEventJson(const InputEvent& event);

/**
 * Input Router API Server
 * Bridges Web UI and Input Router Daemon
 */

const express = require('express');
const http = require('http');
const cors = require('cors');
const WebSocket = require('ws');
const net = require('net');
const apiRoutes = require('./routes/api');

const PORT = process.env.PORT || 3000;
const RAW_INPUT_SERVICE_PORT = 9999;

const app = express();
const server = http.createServer(app);

// WebSocket server for input log streaming
const wss = new WebSocket.Server({ server, path: '/ws/input-log' });

// Middleware
app.use(cors());
app.use(express.json());

// Request logging
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
    next();
});

// API routes
app.use('/api', apiRoutes);

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: Date.now() });
});

// Error handler
app.use((err, req, res, next) => {
    console.error('Error:', err.message);
    res.status(err.status || 500).json({
        error: err.message || 'Internal server error',
        code: err.code || 'INTERNAL_ERROR'
    });
});


// ============================================
// WebSocket: Stream input events from Raw Input Service
// ============================================

let rawInputSocket = null;
let reconnectTimer = null;

function connectToRawInputService() {
    if (rawInputSocket) {
        rawInputSocket.destroy();
    }

    console.log(`Connecting to Raw Input Service on port ${RAW_INPUT_SERVICE_PORT}...`);
    
    rawInputSocket = new net.Socket();
    let buffer = '';

    rawInputSocket.connect(RAW_INPUT_SERVICE_PORT, '127.0.0.1', () => {
        console.log('Connected to Raw Input Service');
        broadcastToClients({ type: 'connection', status: 'connected' });
    });

    rawInputSocket.on('data', (data) => {
        buffer += data.toString();
        
        // Process complete JSON lines
        while (buffer.includes('\n')) {
            const newlineIndex = buffer.indexOf('\n');
            const line = buffer.slice(0, newlineIndex).trim();
            buffer = buffer.slice(newlineIndex + 1);
            
            if (line) {
                try {
                    const event = JSON.parse(line);
                    broadcastToClients({ type: 'input', ...event });
                } catch (e) {
                    console.error('JSON parse error:', e.message);
                }
            }
        }
    });

    rawInputSocket.on('error', (err) => {
        console.error('Raw Input Service error:', err.message);
    });

    rawInputSocket.on('close', () => {
        console.log('Disconnected from Raw Input Service');
        broadcastToClients({ type: 'connection', status: 'disconnected' });
        rawInputSocket = null;
        
        // Reconnect after delay
        if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null;
                connectToRawInputService();
            }, 5000);
        }
    });
}

function broadcastToClients(data) {
    const message = JSON.stringify(data);
    wss.clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
        }
    });
}

// WebSocket connection handler
wss.on('connection', (ws) => {
    console.log('WebSocket client connected');
    
    // Send current connection status
    ws.send(JSON.stringify({
        type: 'connection',
        status: rawInputSocket && !rawInputSocket.destroyed ? 'connected' : 'disconnected'
    }));

    ws.on('close', () => {
        console.log('WebSocket client disconnected');
    });

    ws.on('error', (err) => {
        console.error('WebSocket error:', err.message);
    });
});

// Export for use in routes
module.exports.isRawInputConnected = () => rawInputSocket && !rawInputSocket.destroyed;
module.exports.getWsClientCount = () => wss.clients.size;


// ============================================
// Start server
// ============================================

server.listen(PORT, () => {
    console.log(`API Server running on http://localhost:${PORT}`);
    console.log(`WebSocket endpoint: ws://localhost:${PORT}/ws/input-log`);
    
    // Connect to Raw Input Service for event streaming
    connectToRawInputService();
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\nShutting down...');
    
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
    }
    
    if (rawInputSocket) {
        rawInputSocket.destroy();
    }
    
    wss.close(() => {
        server.close(() => {
            console.log('Server closed');
            process.exit(0);
        });
    });
});

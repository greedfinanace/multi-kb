/**
 * API Routes for Input Router
 */

const express = require('express');
const router = express.Router();
const DaemonClient = require('../lib/daemon-client');

const daemon = new DaemonClient('http://127.0.0.1:8080');

// ============================================
// Device Management
// ============================================

/**
 * GET /api/devices
 * Returns detected keyboards and mice from Raw Input Service
 */
router.get('/devices', async (req, res, next) => {
    try {
        const config = await daemon.getConfig();
        const mappings = config.device_mappings || {};
        
        // Categorize devices by type based on ID prefix
        const keyboards = [];
        const mice = [];
        
        for (const [deviceId, userId] of Object.entries(mappings)) {
            const device = { device_id: deviceId, assigned_to: userId };
            
            if (deviceId.toLowerCase().includes('kb') || deviceId.toLowerCase().includes('keyboard')) {
                keyboards.push(device);
            } else if (deviceId.toLowerCase().includes('mouse') || deviceId.toLowerCase().includes('mi')) {
                mice.push(device);
            } else {
                // Unknown type - add to both for visibility
                keyboards.push({ ...device, type_unknown: true });
            }
        }
        
        res.json({ keyboards, mice });
    } catch (err) {
        next(err);
    }
});

/**
 * POST /api/assign-device
 * Assign a device to a user
 * Body: { user: "user_1", type: "keyboard", device_id: "kb-001" }
 */
router.post('/assign-device', async (req, res, next) => {
    try {
        const { user, device_id } = req.body;
        
        if (!user || !device_id) {
            return res.status(400).json({
                error: 'Missing required fields: user, device_id',
                code: 'INVALID_REQUEST'
            });
        }
        
        await daemon.addMapping(device_id, user);
        res.json({ status: 'ok', device_id, user });
    } catch (err) {
        next(err);
    }
});

/**
 * DELETE /api/device/:deviceId
 * Remove device assignment
 */
router.delete('/device/:deviceId', async (req, res, next) => {
    try {
        const deviceId = decodeURIComponent(req.params.deviceId);
        await daemon.removeMapping(deviceId);
        res.json({ status: 'ok', device_id: deviceId });
    } catch (err) {
        next(err);
    }
});


// ============================================
// Configuration
// ============================================

/**
 * GET /api/config
 * Returns current daemon configuration
 */
router.get('/config', async (req, res, next) => {
    try {
        const config = await daemon.getConfig();
        res.json(config);
    } catch (err) {
        next(err);
    }
});

/**
 * POST /api/config
 * Update daemon configuration
 * Body: { ...config fields to update }
 */
router.post('/config', async (req, res, next) => {
    try {
        const updates = req.body;
        
        if (!updates || Object.keys(updates).length === 0) {
            return res.status(400).json({
                error: 'No configuration updates provided',
                code: 'INVALID_REQUEST'
            });
        }
        
        await daemon.updateConfig(updates);
        res.json({ status: 'ok' });
    } catch (err) {
        next(err);
    }
});

/**
 * GET /api/mappings
 * Returns device-to-user mappings
 */
router.get('/mappings', async (req, res, next) => {
    try {
        const mappings = await daemon.getMappings();
        res.json(mappings);
    } catch (err) {
        next(err);
    }
});

// ============================================
// Process Management
// ============================================

/**
 * POST /api/launch
 * Launch Cursor/VS Code instance for a user
 * Body: { user: "user_1" }
 */
router.post('/launch', async (req, res, next) => {
    try {
        const { user } = req.body;
        
        if (!user) {
            return res.status(400).json({
                error: 'Missing required field: user',
                code: 'INVALID_REQUEST'
            });
        }
        
        const result = await daemon.launchEditor(user);
        res.json(result);
    } catch (err) {
        next(err);
    }
});

/**
 * POST /api/stop
 * Stop Cursor/VS Code instance for a user
 * Body: { user: "user_1" }
 */
router.post('/stop', async (req, res, next) => {
    try {
        const { user } = req.body;
        
        if (!user) {
            return res.status(400).json({
                error: 'Missing required field: user',
                code: 'INVALID_REQUEST'
            });
        }
        
        const result = await daemon.stopEditor(user);
        res.json(result);
    } catch (err) {
        next(err);
    }
});

/**
 * GET /api/windows
 * List all open editor windows that can be attached to
 */
router.get('/windows', async (req, res, next) => {
    try {
        const windows = await daemon.request('GET', '/windows');
        res.json(windows);
    } catch (err) {
        next(err);
    }
});

/**
 * POST /api/attach
 * Attach a user to an existing window (no launch needed)
 * Body: { user_id: "user_1", hwnd: 12345 }
 */
router.post('/attach', async (req, res, next) => {
    try {
        const { user_id, hwnd } = req.body;
        
        if (!user_id || !hwnd) {
            return res.status(400).json({
                error: 'Missing required fields: user_id, hwnd',
                code: 'INVALID_REQUEST'
            });
        }
        
        const result = await daemon.request('POST', '/attach', { user_id, hwnd });
        res.json(result);
    } catch (err) {
        next(err);
    }
});

/**
 * GET /api/sessions
 * Get active editor sessions
 */
router.get('/sessions', async (req, res, next) => {
    try {
        const sessions = await daemon.getSessions();
        res.json(sessions);
    } catch (err) {
        next(err);
    }
});


// ============================================
// Status
// ============================================

/**
 * GET /api/status
 * Returns overall system status
 */
router.get('/status', async (req, res, next) => {
    try {
        const server = require('../server');
        
        let daemonStatus = { running: false, error: null };
        let sessions = {};
        
        try {
            sessions = await daemon.getSessions();
            daemonStatus.running = true;
        } catch (err) {
            daemonStatus.error = err.message;
        }
        
        // Build process info
        const processes = {};
        for (const [userId, session] of Object.entries(sessions)) {
            processes[userId] = {
                pid: session.pid,
                hwnd: session.hwnd,
                editor: session.editor,
                running: session.pid > 0
            };
        }
        
        res.json({
            router_running: daemonStatus.running,
            router_error: daemonStatus.error,
            service_connected: server.isRawInputConnected(),
            ws_clients: server.getWsClientCount(),
            processes
        });
    } catch (err) {
        next(err);
    }
});

/**
 * GET /api/users
 * Get configured users
 */
router.get('/users', async (req, res, next) => {
    try {
        const config = await daemon.getConfig();
        res.json(config.users || {});
    } catch (err) {
        next(err);
    }
});

/**
 * POST /api/users/:userId
 * Update user configuration
 * Body: { project_dir: "...", editor: "cursor" }
 */
router.post('/users/:userId', async (req, res, next) => {
    try {
        const { userId } = req.params;
        const userConfig = req.body;
        
        const config = await daemon.getConfig();
        config.users = config.users || {};
        config.users[userId] = { ...config.users[userId], ...userConfig };
        
        await daemon.updateConfig({ users: config.users });
        res.json({ status: 'ok', user: userId });
    } catch (err) {
        next(err);
    }
});

module.exports = router;

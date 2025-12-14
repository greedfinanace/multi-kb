/**
 * Daemon Client
 * HTTP client for communicating with Input Router Daemon
 */

const http = require('http');
const fs = require('fs').promises;
const path = require('path');

const TIMEOUT_MS = 5000;
const CONFIG_PATH = path.join(__dirname, '../../input_router/config.json');

class DaemonClient {
    constructor(baseUrl = 'http://127.0.0.1:8080') {
        const url = new URL(baseUrl);
        this.host = url.hostname;
        this.port = parseInt(url.port) || 8080;
    }

    /**
     * Make HTTP request to daemon
     */
    async request(method, path, body = null) {
        return new Promise((resolve, reject) => {
            const options = {
                hostname: this.host,
                port: this.port,
                path,
                method,
                timeout: TIMEOUT_MS,
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            const req = http.request(options, (res) => {
                let data = '';
                
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    if (res.statusCode >= 200 && res.statusCode < 300) {
                        try {
                            resolve(data ? JSON.parse(data) : {});
                        } catch {
                            resolve(data);
                        }
                    } else {
                        const error = new Error(`Daemon returned ${res.statusCode}`);
                        error.status = res.statusCode;
                        error.code = 'DAEMON_ERROR';
                        reject(error);
                    }
                });
            });

            req.on('error', (err) => {
                const error = new Error(`Daemon connection failed: ${err.message}`);
                error.status = 503;
                error.code = 'DAEMON_UNAVAILABLE';
                reject(error);
            });

            req.on('timeout', () => {
                req.destroy();
                const error = new Error('Daemon request timed out');
                error.status = 504;
                error.code = 'DAEMON_TIMEOUT';
                reject(error);
            });

            if (body) {
                req.write(JSON.stringify(body));
            }
            req.end();
        });
    }

    /**
     * Get device mappings from daemon
     */
    async getMappings() {
        return this.request('GET', '/mappings');
    }

    /**
     * Add device mapping
     */
    async addMapping(deviceId, userId) {
        return this.request('POST', '/mapping', { device_id: deviceId, user_id: userId });
    }

    /**
     * Remove device mapping
     */
    async removeMapping(deviceId) {
        return this.request('DELETE', `/mapping/${encodeURIComponent(deviceId)}`);
    }

    /**
     * Get active sessions
     */
    async getSessions() {
        return this.request('GET', '/sessions');
    }

    /**
     * Launch editor for user
     */
    async launchEditor(userId) {
        return this.request('POST', '/launch', { user_id: userId });
    }


    /**
     * Stop editor for user
     */
    async stopEditor(userId) {
        return this.request('POST', '/stop', { user_id: userId });
    }

    /**
     * Get full config from file (daemon may not expose all config via HTTP)
     */
    async getConfig() {
        try {
            // First try daemon endpoint
            return await this.request('GET', '/config');
        } catch {
            // Fall back to reading config file directly
            try {
                const data = await fs.readFile(CONFIG_PATH, 'utf8');
                return JSON.parse(data);
            } catch (err) {
                const error = new Error(`Cannot read config: ${err.message}`);
                error.status = 500;
                error.code = 'CONFIG_ERROR';
                throw error;
            }
        }
    }

    /**
     * Update config
     */
    async updateConfig(updates) {
        try {
            // Try daemon endpoint first
            return await this.request('POST', '/config', updates);
        } catch {
            // Fall back to direct file update
            try {
                const data = await fs.readFile(CONFIG_PATH, 'utf8');
                const config = JSON.parse(data);
                
                // Merge updates
                Object.assign(config, updates);
                
                await fs.writeFile(CONFIG_PATH, JSON.stringify(config, null, 4));
                return { status: 'ok' };
            } catch (err) {
                const error = new Error(`Cannot update config: ${err.message}`);
                error.status = 500;
                error.code = 'CONFIG_ERROR';
                throw error;
            }
        }
    }

    /**
     * Check if daemon is running
     */
    async ping() {
        try {
            await this.request('GET', '/mappings');
            return true;
        } catch {
            return false;
        }
    }
}

module.exports = DaemonClient;

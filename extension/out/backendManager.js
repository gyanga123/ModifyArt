"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.BackendManager = void 0;
const cp = __importStar(require("child_process"));
const path = __importStar(require("path"));
const http = __importStar(require("http"));
const net = __importStar(require("net"));
class BackendManager {
    process = null;
    port = 0;
    async start() {
        if (this.process && this.port) {
            // Already running, check if responsive
            if (await this.isHealthy()) {
                return;
            }
            // Not responding, restart
            this.stop();
        }
        this.port = await this.findFreePort();
        const serverPath = path.resolve(__dirname, "..", "..", "backend", "server.py");
        this.process = cp.spawn("python", [serverPath, String(this.port)], {
            cwd: path.dirname(serverPath),
            stdio: ["ignore", "pipe", "pipe"],
        });
        this.process.stdout?.on("data", (data) => {
            console.log(`[ModifyArt Backend] ${data.toString().trim()}`);
        });
        this.process.stderr?.on("data", (data) => {
            console.error(`[ModifyArt Backend] ${data.toString().trim()}`);
        });
        this.process.on("exit", (code) => {
            console.log(`[ModifyArt Backend] exited with code ${code}`);
            this.process = null;
        });
        // Wait for backend to be ready
        await this.waitForReady(5000);
    }
    stop() {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
        this.port = 0;
    }
    getPort() {
        return this.port;
    }
    async isHealthy() {
        try {
            await this.httpGet(`http://127.0.0.1:${this.port}/api/health`);
            return true;
        }
        catch {
            return false;
        }
    }
    async waitForReady(timeoutMs) {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            if (await this.isHealthy()) {
                return;
            }
            await this.sleep(200);
        }
        throw new Error("Backend did not start within timeout");
    }
    findFreePort() {
        return new Promise((resolve, reject) => {
            const server = net.createServer();
            server.listen(0, "127.0.0.1", () => {
                const address = server.address();
                if (address && typeof address === "object") {
                    const port = address.port;
                    server.close(() => resolve(port));
                }
                else {
                    reject(new Error("Failed to get port"));
                }
            });
            server.on("error", reject);
        });
    }
    httpGet(url) {
        return new Promise((resolve, reject) => {
            http.get(url, (res) => {
                let data = "";
                res.on("data", (chunk) => (data += chunk));
                res.on("end", () => {
                    if (res.statusCode === 200) {
                        resolve(data);
                    }
                    else {
                        reject(new Error(`HTTP ${res.statusCode}`));
                    }
                });
            }).on("error", reject);
        });
    }
    sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }
}
exports.BackendManager = BackendManager;
//# sourceMappingURL=backendManager.js.map
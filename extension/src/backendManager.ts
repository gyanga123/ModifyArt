import * as cp from "child_process";
import * as path from "path";
import * as http from "http";
import * as net from "net";

export class BackendManager {
    private process: cp.ChildProcess | null = null;
    private port: number = 0;

    async start(): Promise<void> {
        if (this.process && this.port) {
            // Already running, check if responsive
            if (await this.isHealthy()) {
                return;
            }
            // Not responding, restart
            this.stop();
        }

        this.port = await this.findFreePort();

        const serverPath = path.resolve(
            __dirname, "..", "..", "backend", "server.py"
        );

        this.process = cp.spawn("python", [serverPath, String(this.port)], {
            cwd: path.dirname(serverPath),
            stdio: ["ignore", "pipe", "pipe"],
        });

        this.process.stdout?.on("data", (data: Buffer) => {
            console.log(`[ModifyArt Backend] ${data.toString().trim()}`);
        });

        this.process.stderr?.on("data", (data: Buffer) => {
            console.error(`[ModifyArt Backend] ${data.toString().trim()}`);
        });

        this.process.on("exit", (code) => {
            console.log(`[ModifyArt Backend] exited with code ${code}`);
            this.process = null;
        });

        // Wait for backend to be ready
        await this.waitForReady(5000);
    }

    stop(): void {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
        this.port = 0;
    }

    getPort(): number {
        return this.port;
    }

    private async isHealthy(): Promise<boolean> {
        try {
            await this.httpGet(`http://127.0.0.1:${this.port}/api/health`);
            return true;
        } catch {
            return false;
        }
    }

    private async waitForReady(timeoutMs: number): Promise<void> {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            if (await this.isHealthy()) {
                return;
            }
            await this.sleep(200);
        }
        throw new Error("Backend did not start within timeout");
    }

    private findFreePort(): Promise<number> {
        return new Promise((resolve, reject) => {
            const server = net.createServer();
            server.listen(0, "127.0.0.1", () => {
                const address = server.address();
                if (address && typeof address === "object") {
                    const port = address.port;
                    server.close(() => resolve(port));
                } else {
                    reject(new Error("Failed to get port"));
                }
            });
            server.on("error", reject);
        });
    }

    private httpGet(url: string): Promise<string> {
        return new Promise((resolve, reject) => {
            http.get(url, (res) => {
                let data = "";
                res.on("data", (chunk) => (data += chunk));
                res.on("end", () => {
                    if (res.statusCode === 200) {
                        resolve(data);
                    } else {
                        reject(new Error(`HTTP ${res.statusCode}`));
                    }
                });
            }).on("error", reject);
        });
    }

    private sleep(ms: number): Promise<void> {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }
}

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { BackendManager } from "./backendManager";

export class WebviewProvider implements vscode.WebviewViewProvider {
    constructor(
        private readonly extensionUri: vscode.Uri,
        private readonly backendManager: BackendManager
    ) {}

    resolveWebviewView(
        _webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ): void {
        // Not used - we create panels dynamically
    }

    getHtml(webview: vscode.Webview): string {
        const webviewDir = path.resolve(
            this.extensionUri.fsPath, "webview"
        );

        const htmlPath = path.join(webviewDir, "index.html");
        const cssPath = path.join(webviewDir, "style.css");
        const jsPath = path.join(webviewDir, "app.js");

        let html = fs.readFileSync(htmlPath, "utf-8");
        const css = fs.readFileSync(cssPath, "utf-8");
        const js = fs.readFileSync(jsPath, "utf-8");

        // Inline CSS and JS
        html = html.replace(
            '<link rel="stylesheet" href="style.css">',
            `<style>${css}</style>`
        );
        html = html.replace(
            '<script src="app.js"></script>',
            `<script>${js}</script>`
        );

        return html;
    }
}

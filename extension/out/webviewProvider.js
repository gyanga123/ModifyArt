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
exports.WebviewProvider = void 0;
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class WebviewProvider {
    extensionUri;
    backendManager;
    constructor(extensionUri, backendManager) {
        this.extensionUri = extensionUri;
        this.backendManager = backendManager;
    }
    resolveWebviewView(_webviewView, _context, _token) {
        // Not used - we create panels dynamically
    }
    getHtml(webview) {
        const webviewDir = path.resolve(this.extensionUri.fsPath, "webview");
        const htmlPath = path.join(webviewDir, "index.html");
        const cssPath = path.join(webviewDir, "style.css");
        const jsPath = path.join(webviewDir, "app.js");
        let html = fs.readFileSync(htmlPath, "utf-8");
        const css = fs.readFileSync(cssPath, "utf-8");
        const js = fs.readFileSync(jsPath, "utf-8");
        // Inline CSS and JS
        html = html.replace('<link rel="stylesheet" href="style.css">', `<style>${css}</style>`);
        html = html.replace('<script src="app.js"></script>', `<script>${js}</script>`);
        return html;
    }
}
exports.WebviewProvider = WebviewProvider;
//# sourceMappingURL=webviewProvider.js.map
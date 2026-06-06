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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const backendManager_1 = require("./backendManager");
const webviewProvider_1 = require("./webviewProvider");
let backendManager;
let webviewProvider;
function activate(context) {
    backendManager = new backendManager_1.BackendManager();
    webviewProvider = new webviewProvider_1.WebviewProvider(context.extensionUri, backendManager);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider("modifyart.panel", webviewProvider));
    const openCmd = vscode.commands.registerCommand("modifyart.open", async () => {
        const editor = vscode.window.activeTextEditor;
        let text = "";
        let filePath = "";
        if (editor) {
            text = editor.document.getText(editor.selection.isEmpty ? undefined : editor.selection);
            filePath = editor.document.uri.fsPath;
        }
        await backendManager.start();
        const panel = vscode.window.createWebviewPanel("modifyart", "ModifyArt - AI 写作助手", vscode.ViewColumn.Beside, {
            enableScripts: true,
            retainContextWhenHidden: true,
        });
        panel.webview.html = webviewProvider.getHtml(panel.webview);
        const port = backendManager.getPort();
        // ── 主动监听编辑器选区变化，推送给前端 ──
        const pushSelection = () => {
            const ed = vscode.window.activeTextEditor;
            if (ed && ed.document.uri.fsPath === filePath) {
                const sel = ed.document.getText(ed.selection.isEmpty ? undefined : ed.selection);
                panel.webview.postMessage({ type: "selection_changed", text: sel });
            }
        };
        const selectionListener = vscode.window.onDidChangeTextEditorSelection((e) => {
            if (e.textEditor === vscode.window.activeTextEditor) {
                pushSelection();
            }
        });
        panel.onDidDispose(() => {
            selectionListener.dispose();
        });
        // ── 消息处理 ──
        panel.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case "ready":
                    panel.webview.postMessage({ type: "init", text, port, filePath });
                    break;
                case "apply":
                    if (editor) {
                        await editor.edit((editBuilder) => {
                            editBuilder.replace(editor.selection.isEmpty
                                ? new vscode.Range(0, 0, editor.document.lineCount, 0)
                                : editor.selection, message.text);
                        });
                        vscode.window.showInformationMessage("ModifyArt: 修改已应用到文档，可继续选择其他操作");
                        panel.webview.postMessage({ type: "applied", text: message.text });
                    }
                    break;
                case "save_context":
                    try {
                        const res = await fetch(`http://127.0.0.1:${port}/api/context`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify(message.data),
                        });
                        const result = await res.json();
                        panel.webview.postMessage({ type: "context_saved", data: result });
                    }
                    catch (e) {
                        panel.webview.postMessage({ type: "context_error", error: e.message });
                    }
                    break;
                case "close":
                    panel.dispose();
                    break;
            }
        });
    });
    context.subscriptions.push(openCmd);
    // Cleanup on deactivate
    context.subscriptions.push({
        dispose: () => {
            backendManager.stop();
        },
    });
}
function deactivate() {
    if (backendManager) {
        backendManager.stop();
    }
}
//# sourceMappingURL=extension.js.map
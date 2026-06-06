// ── State ──────────────────────────────────────────
const vscode = acquireVsCodeApi();
let port = 0;
let originalText = "";
let modifiedText = "";
let contextFile = "";

// ── DOM ────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const opSelect = $("operation");
const extraInput = $("extra-instruction");
const btnExecute = $("btn-execute");
const btnCancel = $("btn-cancel");
const btnApply = $("btn-apply");
const btnRefine = $("btn-refine");
const btnRetry = $("btn-retry");
const statusBar = $("status-bar");
const originalPane = $("original-pane");
const modifiedPane = $("modified-pane");
const resultInfo = $("result-info");
const ctxStatus = $("ctx-status");
const ctxCharUpdatesInput = $("ctx-char-updates");
const ctxProblemsInput = $("ctx-problems");
const ctxChangeInput = $("ctx-change");
const btnSaveCtx = $("btn-save-ctx");
const ctxPanel = $("ctx-panel");

let detectedChapter = "";  // 当前检测到的章节号
let abortController = null;

// ── Init ───────────────────────────────────────────
vscode.postMessage({ type: "ready" });

window.addEventListener("message", (event) => {
    const msg = event.data;
    if (msg.type === "init") {
        port = msg.port;
        originalText = msg.text || "";
        contextFile = msg.filePath || "";
        loadContext();
        resetPanel();
        updateStatus("info", port ? "后端已连接" : "后端未启动");
    }
    if (msg.type === "selection_changed") {
        if (msg.text) originalText = msg.text;
    }
    if (msg.type === "applied") {
        originalText = msg.text || "";
        modifiedText = "";
        resetPanel();
        btnApply.disabled = true;
        btnApply.style.display = "";
        btnRefine.style.display = "none";
        btnRetry.style.display = "none";
        resultInfo.textContent = "";
        ctxPanel.style.display = "block";
        extraInput.style.borderColor = "";
        updateStatus("success", "已应用。下方可更新上下文，或继续选择操作");
    }
    if (msg.type === "context_saved") {
        updateStatus("success", "上下文已保存");
        ctxPanel.style.display = "none";
        ctxCharUpdatesInput.value = "";
        ctxProblemsInput.value = "";
        ctxChangeInput.value = "";
        loadContext();  // 刷新右上角上下文状态
    }
    if (msg.type === "context_error") {
        updateStatus("error", `上下文保存失败: ${msg.error}`);
    }
});

async function loadContext() {
    if (!contextFile || !port) { ctxStatus.textContent = "无上下文"; return; }
    try {
        const res = await fetch(`http://127.0.0.1:${port}/api/context?context_file=${encodeURIComponent(contextFile)}`);
        if (!res.ok) { ctxStatus.textContent = "上下文加载失败"; return; }
        const ctx = await res.json();
        const charCount = ctx.人物 ? Object.keys(ctx.人物).length : 0;
        const eventCount = ctx.事件 ? Object.keys(ctx.事件).length : 0;
        let probCount = 0;
        if (ctx.章节问题) {
            probCount = Object.values(ctx.章节问题).flat().length;
        }
        const changeCount = ctx.改动记录 ? Object.keys(ctx.改动记录).length : 0;
        let parts = [];
        if (charCount) parts.push(`${charCount}人物`);
        if (eventCount) parts.push(`${eventCount}事件`);
        if (probCount) parts.push(`${probCount}问题`);
        if (changeCount) parts.push(`${changeCount}改动`);
        ctxStatus.textContent = parts.length > 0 ? `上下文: ${parts.join(' · ')}` : "上下文: 空";
    } catch {
        ctxStatus.textContent = "上下文加载失败";
    }
}

// ── Execute ────────────────────────────────────────
btnExecute.addEventListener("click", async () => {
    if (!originalText) {
        updateStatus("error", "请先在编辑器中选中文本");
        return;
    }
    if (!port) {
        updateStatus("error", "后端未启动，请关闭面板后重新右键打开");
        return;
    }

    const operation = opSelect.value;
    const extraInstruction = extraInput.value.trim();

    setLoading(true);
    abortController = new AbortController();
    updateStatus("info", '<span class="loading-spinner"></span> 处理中...');

    try {
        const res = await fetch(`http://127.0.0.1:${port}/api/modify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: originalText,
                operation,
                extra_instruction: extraInstruction,
                context_file: contextFile,
            }),
            signal: abortController.signal,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `服务器错误 HTTP ${res.status}`);
        }

        const data = await res.json();
        modifiedText = data.modified_text || "";
        renderDiff(data.diff_hunks || []);

        const opNames = {
            polish: "润色改写", remove_filler: "去除水句", format: "智能分段",
            pipeline: "逐章改写", dedup_plot: "情节去重分析", logic_check: "逻辑校验", refine: "反馈修正",
        };
        let ctxTag = data.context_summary ? ` · ${data.context_summary}` : "";
        resultInfo.textContent = `${opNames[operation] || operation} · ${data.tokens_used || 0} tokens${ctxTag}`;

        // 记录检测到的章节号
        detectedChapter = data.detected_chapter || "";

        if (operation === "dedup_plot" || operation === "logic_check") {
            // 分析类操作：不显示应用到编辑器，直接显示上下文面板
            btnApply.style.display = "none";
            btnRefine.style.display = "none";
            btnRetry.style.display = "inline-block";
            ctxPanel.style.display = "block";
            resultInfo.textContent += "（分析报告）";
            // 更新上下文面板标题，显示章节号
            const chLabel = detectedChapter ? `第${detectedChapter}章` : "未检测到章节号 → 存入「全局」";
            $("ctx-title").textContent = `更新上下文 — ${chLabel}`;
            // 有章节号时高亮，无章节号时警告色
            $("ctx-title").style.color = detectedChapter ? "" : "#f85149";
            // 预填人物更新
            if (data.character_updates && Object.keys(data.character_updates).length > 0) {
                const charLines = Object.entries(data.character_updates)
                    .map(([name, suggestion]) => `${name}: ${suggestion}`);
                ctxCharUpdatesInput.value = charLines.join("\n");
            } else {
                ctxCharUpdatesInput.value = "";
            }
            // 预填章节问题
            if (data.extracted_problems && data.extracted_problems.length > 0) {
                ctxProblemsInput.value = data.extracted_problems.join("\n");
                ctxChangeInput.value = `第${detectedChapter || "?"}章 情节去重分析`;
                const charCount = Object.keys(data.character_updates || {}).length;
                const probCount = data.extracted_problems.length;
                updateStatus("success", `分析完成 — ${charCount}人物更新 + ${probCount}问题（${chLabel}），审核后保存`);
            } else {
                updateStatus("success", `分析完成 — 下方可手动填写（${chLabel}）`);
            }
        } else {
            // 改写类操作：显示应用 + 修正 + 重试
            btnApply.style.display = "";
            btnApply.disabled = false;
            btnRefine.style.display = "inline-block";
            btnRetry.style.display = "inline-block";
            extraInput.style.borderColor = "var(--btn-primary)";
            updateStatus("success", "完成！不满意可在上方输入意见 → 点「根据反馈修正」");
        }

    } catch (err) {
        if (err.name === "AbortError") {
            updateStatus("info", "已取消");
        } else {
            updateStatus("error", `失败: ${err.message || err}`);
        }
    } finally {
        setLoading(false);
        abortController = null;
    }
});

// ── Cancel ─────────────────────────────────────────
btnCancel.addEventListener("click", () => {
    if (abortController) abortController.abort();
});

// ── Apply ──────────────────────────────────────────
btnApply.addEventListener("click", () => {
    const edited = modifiedPane.value;
    if (edited) {
        vscode.postMessage({ type: "apply", text: edited });
    }
});

// ── Refine ─────────────────────────────────────────
btnRefine.addEventListener("click", async () => {
    const feedback = extraInput.value.trim();
    if (!feedback) {
        updateStatus("error", "请先在「附加指令」输入框中输入具体的修改意见");
        extraInput.focus();
        return;
    }
    if (!modifiedText) {
        updateStatus("error", "没有可修正的内容");
        return;
    }

    setLoading(true);
    abortController = new AbortController();

    try {
        const res = await fetch(`http://127.0.0.1:${port}/api/modify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: originalText,
                operation: "refine",
                extra_instruction: feedback,
                previous_result: modifiedText,
                context_file: contextFile,
            }),
            signal: abortController.signal,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `服务器错误 HTTP ${res.status}`);
        }

        const data = await res.json();
        modifiedText = data.modified_text || "";
        renderDiff(data.diff_hunks || []);
        resultInfo.textContent = `反馈修正 · ${data.tokens_used || 0} tokens`;
        btnRefine.style.display = "inline-block";
        btnRetry.style.display = "inline-block";
        updateStatus("success", "修正完成，可继续输入意见再次修正");

    } catch (err) {
        if (err.name === "AbortError") {
            updateStatus("info", "已取消");
        } else {
            updateStatus("error", `修正失败: ${err.message || err}`);
        }
    } finally {
        setLoading(false);
        abortController = null;
    }
});

// ── Save Context ───────────────────────────────────
btnSaveCtx.addEventListener("click", () => {
    // 解析人物更新: "苏曼尼: 建议..." → {"苏曼尼": "建议..."}
    const charUpdates = {};
    const charText = ctxCharUpdatesInput.value.trim();
    if (charText) {
        charText.split("\n").forEach(line => {
            const m = line.match(/^(.+?)[：:]\s*(.+)$/);
            if (m) charUpdates[m[1].trim()] = m[2].trim();
        });
    }
    vscode.postMessage({
        type: "save_context",
        data: {
            context_file: contextFile,
            problems: ctxProblemsInput.value.trim(),
            change: ctxChangeInput.value.trim(),
            chapter: detectedChapter,
            character_updates: charUpdates,
        },
    });
});

// ── Retry ──────────────────────────────────────────
btnRetry.addEventListener("click", () => {
    btnExecute.click();
});

// ── Keyboard shortcut ──────────────────────────────
document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        btnExecute.click();
    }
});

// ── Render Diff ────────────────────────────────────
function renderDiff(hunks) {
    let originalHtml = "";
    for (const h of hunks) {
        const escaped = escapeHtml(h.content);
        switch (h.type) {
            case "equal":
                originalHtml += `<span class="equal">${escaped}</span>`;
                break;
            case "delete":
                originalHtml += `<span class="del">${escaped}</span>`;
                break;
            case "insert":
                originalHtml += `<span class="equal">${escaped}</span>`;
                break;
        }
    }
    originalPane.innerHTML = originalHtml || '<div class="empty-state">（空）</div>';
    modifiedPane.value = modifiedText;
    modifiedPane.onscroll = () => { originalPane.scrollTop = modifiedPane.scrollTop; };
    originalPane.onscroll = () => { modifiedPane.scrollTop = originalPane.scrollTop; };
}

function resetPanel() {
    if (originalText) {
        originalPane.innerHTML = `<div class="empty-state">已加载 ${originalText.length} 个字符，选中新文本后点执行</div>`;
    } else {
        originalPane.innerHTML = '<div class="empty-state">请选中文本后右键打开</div>';
    }
    modifiedPane.value = "";
}

// ── Helpers ────────────────────────────────────────
function setLoading(loading) {
    btnExecute.style.display = loading ? "none" : "";
    btnCancel.style.display = loading ? "" : "none";
    btnExecute.disabled = loading;
    if (loading) {
        btnRetry.style.display = "none";
        btnRefine.style.display = "none";
    }
}

function updateStatus(type, message) {
    statusBar.className = "status-bar";
    if (type === "error") statusBar.classList.add("error");
    if (type === "success") statusBar.classList.add("success");
    statusBar.innerHTML = message;
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

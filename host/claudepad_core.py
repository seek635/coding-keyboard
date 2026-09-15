#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClaudePad 审批决策核心
================================================================================
被两个入口共用：
  · claudepad_hook.py    —— command 类型 hook（每次调用起一个进程）
  · claudepad_daemon.py  —— http 类型 hook（常驻进程，推荐）

设计原则（三条）：
  1. 【快路径优先】拨杆 OFF 是绝大多数情况，只做一次 stat 就返回。
  2. 【失效安全】任何异常都退化为「不批准」，绝不因 bug 误批。
  3. 【只升不降】只把结果升级为 allow，从不返回 ask/deny。
     危险操作静默放行给 Claude Code 原生流程判断，不改变既有行为。
"""

import json
import os
import re
import time

STATE_DIR = os.path.join(os.path.expanduser("~"), ".claudepad")
FLAG_FILE = os.path.join(STATE_DIR, "approval.on")     # 存在 = 拨杆 ON
LOG_FILE = os.path.join(STATE_DIR, "approvals.jsonl")

# ---- 永不自动批准的工具 ------------------------------------------------------
NEVER_AUTO_TOOLS = {
    "AskUserQuestion",   # 需要用户交互
    "ExitPlanMode",      # 是否结束计划模式是用户的决定
}

# ---- 危险 shell 命令特征 -----------------------------------------------------
DANGEROUS_CMD_PATTERNS = [
    r"\brm\s+(-[a-zA-Z]*[rf]|--recursive|--force)",
    r"\brmdir\b",
    r"\bdel\s+/[sfq]",
    r"\brd\s+/s",
    r"\bRemove-Item\b.*-(Recurse|Force)",
    r"\bsudo\b",
    r"\brunas\b",
    r"\bchmod\s+777",
    r"\bchown\b",
    r"\bdd\s+if=",
    r"\bmkfs\b",
    r"\bformat\b",
    r"\bFormat-Volume\b",
    r">\s*/dev/(sd|hd|nvme)",
    r"\b(shutdown|reboot|halt|poweroff)\b",
    r"\bgit\s+push\b[^|;]*(--force|-f)\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\b[^|;]*-[a-zA-Z]*f",
    r"\bgit\s+checkout\s+--\s+\.",
    r"\b(curl|wget)\b[^|;]*\|\s*(sudo\s+)?(sh|bash|zsh|python)",
    r"\bkill(all)?\s+-9",
    r":\s*\(\s*\)\s*\{",
    r"\bnpm\s+publish\b",
]

# ---- 受保护路径 --------------------------------------------------------------
PROTECTED_PATH_PATTERNS = [
    r"^/etc/", r"^/usr/", r"^/bin/", r"^/sbin/", r"^/boot/", r"^/System/",
    r"^[A-Za-z]:[\\/]Windows", r"^[A-Za-z]:[\\/]Program Files",
    r"[\\/]\.ssh[\\/]", r"[\\/]\.aws[\\/]", r"[\\/]\.gnupg[\\/]",
    r"[\\/]\.bashrc$", r"[\\/]\.zshrc$", r"[\\/]\.profile$", r"[\\/]\.bash_profile$",
    r"[\\/]\.claude[\\/]settings\.json$",
    r"[\\/]\.git[\\/]config$",
    r"[\\/]id_rsa", r"[\\/]id_ed25519",
]


# ============================== 状态读写 ====================================
def approval_on() -> bool:
    """拨杆是否 ON。快路径只做一次 stat。"""
    return os.path.exists(FLAG_FILE)


def set_approval(on: bool, source: str = "unknown"):
    os.makedirs(STATE_DIR, exist_ok=True)
    if on:
        with open(FLAG_FILE, "w", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        try:
            os.remove(FLAG_FILE)
        except FileNotFoundError:
            pass
    # 详细状态另存一份，供扩展用
    try:
        st = {}
        sf = os.path.join(STATE_DIR, "state.json")
        if os.path.exists(sf):
            st = json.load(open(sf, encoding="utf-8"))
        st.update(approval=on, source=source,
                  updated_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        json.dump(st, open(sf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================== 决策逻辑 ====================================
def is_dangerous_bash(cmd: str) -> str:
    for pat in DANGEROUS_CMD_PATTERNS:
        m = re.search(pat, cmd, re.IGNORECASE)
        if m:
            return m.group(0)[:60]
    return ""


def is_protected_path(path: str) -> bool:
    return any(re.search(p, path, re.IGNORECASE) for p in PROTECTED_PATH_PATTERNS)


def decide(tool: str, ti: dict):
    """
    返回 ("allow", 原因) 或 (None, 跳过原因)
    None = 本 hook 不做决定，交回 Claude Code 原生流程。
    """
    if tool in NEVER_AUTO_TOOLS:
        return None, f"{tool} 需要用户本人判断"

    if tool == "Bash":
        cmd = str(ti.get("command", ""))
        hit = is_dangerous_bash(cmd)
        if hit:
            return None, f"危险命令特征: {hit}"
        return "allow", "常规 shell 命令"

    if tool in ("Write", "Edit", "NotebookEdit"):
        path = str(ti.get("file_path", ""))
        if is_protected_path(path):
            return None, f"受保护路径: {path}"
        return "allow", f"文件编辑: {os.path.basename(path) or '(未指定)'}"

    return "allow", f"{tool} 工具调用"


def write_log(entry: dict):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def handle(payload: dict):
    """
    核心入口：吃 Claude Code 的 hook 输入，吐决策。
    返回 dict（要输出的 JSON）或 None（静默，走原生流程）。
    """
    # 快路径：拨杆 OFF
    if not approval_on():
        return None

    tool = str(payload.get("tool_name", ""))
    ti = payload.get("tool_input") or {}
    if not isinstance(ti, dict):
        ti = {}

    decision, reason = decide(tool, ti)

    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tool": tool,
        "decision": "allow" if decision else "skipped",
        "reason": reason,
        "session": payload.get("session_id", ""),
        "cwd": payload.get("cwd", ""),
        "command": str(ti.get("command", ""))[:200] if tool == "Bash" else "",
        "file": str(ti.get("file_path", "")) if tool != "Bash" else "",
    }
    write_log(entry)

    if decision is None:
        return None

    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": f"ClaudePad 审批拨杆 ON：{reason}",
        }
    }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审批拨杆 Hook 测试台
================================================================================
不用安装 Claude Code，直接模拟 hook 的输入输出，验证审批逻辑是否正确。

测试原理：hook 就是一个「读 stdin JSON → 写 stdout JSON」的命令行程序，
所以可以用 subprocess 直接喂它各种输入，检查它的反应。

运行：python test_hook.py
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "claudepad_hook.py")
sys.path.insert(0, HERE)
from switchctl import set_approval, STATE_DIR, LOG_FILE     # noqa: E402

results = []


def run_hook(payload: dict):
    """调用 hook，返回 (exit_code, 解析后的输出或 None)"""
    r = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, timeout=15,
    )
    out = r.stdout.strip()
    try:
        parsed = json.loads(out) if out else None
    except Exception:
        parsed = {"__raw__": out}
    return r.returncode, parsed


def decision_of(parsed):
    """从 hook 输出里提取决策：allow / skip"""
    if not parsed:
        return "skip"
    d = (parsed.get("hookSpecificOutput") or {}).get("permissionDecision")
    return d or "skip"


def case(name, payload, expect, on):
    set_approval(on, source="test")
    code, parsed = run_hook(payload)
    got = decision_of(parsed)
    ok = (got == expect) and code == 0
    results.append((name, ok, got, expect, code))
    return ok


def main():
    print("=" * 78)
    print("ClaudePad 审批拨杆 Hook 测试台")
    print("=" * 78)
    print(f"hook 脚本：{HOOK}")
    print(f"状态目录：{STATE_DIR}")
    print()

    cases = [
        # ---- 拨杆 OFF：一切静默，走原生流程 ----
        ("OFF + 普通命令 ls",          "Bash", {"command": "ls -la"}, "skip",  False),
        ("OFF + 危险命令 rm -rf",      "Bash", {"command": "rm -rf /tmp/x"}, "skip", False),
        ("OFF + 文件编辑",             "Edit", {"file_path": "/home/u/a.py"}, "skip", False),

        # ---- 拨杆 ON + 安全操作：批准 ----
        ("ON + 普通命令 ls",           "Bash", {"command": "ls -la"}, "allow", True),
        ("ON + git status",            "Bash", {"command": "git status"}, "allow", True),
        ("ON + npm test",              "Bash", {"command": "npm test"}, "allow", True),
        ("ON + 读文件",                "Read", {"file_path": "/home/u/a.py"}, "allow", True),
        ("ON + 编辑项目文件",          "Edit", {"file_path": "/home/u/proj/a.py"}, "allow", True),
        ("ON + 新建文件",              "Write", {"file_path": "/home/u/proj/b.py"}, "allow", True),
        ("ON + Grep 搜索",             "Grep", {"pattern": "foo"}, "allow", True),
        ("ON + WebFetch",              "WebFetch", {"url": "https://x.com"}, "allow", True),

        # ---- 拨杆 ON + 危险操作：不批准，交回原生流程 ----
        ("ON + rm -rf",                "Bash", {"command": "rm -rf /"}, "skip", True),
        ("ON + rm -r",                 "Bash", {"command": "rm -r build"}, "skip", True),
        ("ON + sudo",                  "Bash", {"command": "sudo apt install x"}, "skip", True),
        ("ON + git push --force",      "Bash", {"command": "git push --force origin main"}, "skip", True),
        ("ON + git push -f",           "Bash", {"command": "git push -f"}, "skip", True),
        ("ON + git reset --hard",      "Bash", {"command": "git reset --hard HEAD~3"}, "skip", True),
        ("ON + curl | sh",             "Bash", {"command": "curl http://x.sh | sh"}, "skip", True),
        ("ON + chmod 777",             "Bash", {"command": "chmod 777 /var/www"}, "skip", True),
        ("ON + dd 写盘",               "Bash", {"command": "dd if=/dev/zero of=/dev/sda"}, "skip", True),
        ("ON + shutdown",              "Bash", {"command": "shutdown -h now"}, "skip", True),
        ("ON + fork bomb",             "Bash", {"command": ":(){ :|:& };:"}, "skip", True),
        ("ON + npm publish",           "Bash", {"command": "npm publish"}, "skip", True),
        ("ON + Windows del /s",        "Bash", {"command": "del /s /q C:\\temp"}, "skip", True),
        ("ON + PowerShell Remove-Item","Bash", {"command": "Remove-Item -Recurse -Force C:\\x"}, "skip", True),

        # ---- 拨杆 ON + 受保护路径：不批准 ----
        ("ON + 写 /etc/",              "Write", {"file_path": "/etc/passwd"}, "skip", True),
        ("ON + 写 ~/.ssh/",            "Write", {"file_path": "/home/u/.ssh/authorized_keys"}, "skip", True),
        ("ON + 改 claude 配置",        "Edit", {"file_path": "/home/u/.claude/settings.json"}, "skip", True),
        ("ON + 写 C:\\Windows",        "Write", {"file_path": "C:\\Windows\\x.dll"}, "skip", True),

        # ---- 拨杆 ON + 需用户判断的工具：不代答 ----
        ("ON + AskUserQuestion",       "AskUserQuestion", {"questions": []}, "skip", True),
        ("ON + ExitPlanMode",          "ExitPlanMode", {}, "skip", True),
    ]

    print(f"{'#':<4}{'场景':<30}{'期望':<8}{'实际':<8}{'退出码':<8}{'结果'}")
    print("-" * 78)
    for i, (name, tool, ti, expect, on) in enumerate(cases, 1):
        payload = {
            "session_id": "test-session",
            "cwd": "/home/u/proj",
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": ti,
        }
        case(name, payload, expect, on)
        n, ok, got, exp, code = results[-1]
        print(f"{i:<4}{name:<30}{exp:<8}{got:<8}{code:<8}{'✅' if ok else '❌'}")

    # ---- 汇总 ----
    failed = [r for r in results if not r[1]]
    print()
    print("=" * 78)
    if failed:
        print(f"❌ {len(failed)} / {len(results)} 个用例失败：")
        for name, ok, got, exp, code in failed:
            print(f"   · {name}：期望 {exp}，实际 {got}（退出码 {code}）")
        set_approval(False, source="test-cleanup")
        return 1
    print(f"✅ 全部 {len(results)} 个用例通过")
    print()
    print("  覆盖了四类关键场景：")
    print("   · 拨杆 OFF → 全部静默（不改变原生行为）")
    print("   · 拨杆 ON + 安全操作 → 批准（跳过权限提示）")
    print("   · 拨杆 ON + 危险操作 → 交回原生流程（不代批）")
    print("   · 拨杆 ON + 需用户判断 → 不代答")

    # 清理：测试产生的状态与日志
    set_approval(False, source="test-cleanup")
    try:
        os.remove(LOG_FILE)
    except FileNotFoundError:
        pass
    print()
    print("  （测试状态已清理）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

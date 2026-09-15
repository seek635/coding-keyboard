#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 ClaudePad 审批拨杆 hook 安装进 Claude Code 配置
================================================================================
两种模式，安装脚本会自动填好路径和令牌（手改最容易在这里出错）：

  http    推荐。由常驻守护进程应答，延迟 ~15ms。守护进程没跑时自动退化为
          「正常询问」，不会误批。
  command 备用。每次工具调用起一个 Python 进程，实测约 510ms。

安全设计：
  · 默认只**打印**配置，不动你的文件
  · 加 --apply 才真正写入，且会先备份原文件
  · 合并而不是覆盖 —— 保留你已有的其他 hook 和设置
  · 重复运行是幂等的（替换旧条目，不重复添加）

用法：
    python install_hook.py                      # 预览（默认 http 模式）
    python install_hook.py --mode command       # 预览 command 模式
    python install_hook.py --apply              # 真正写入
    python install_hook.py --uninstall --apply  # 卸载
"""

import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import claudepad_core as core            # noqa: E402
from claudepad_daemon import DEFAULT_PORT, get_or_create_token   # noqa: E402

HOOK = os.path.join(HERE, "claudepad_hook.py")
SETTINGS = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
PYTHON = sys.executable or "python"


def build_entry(mode: str, port: int, token: str) -> dict:
    if mode == "http":
        h = {
            "type": "http",
            "url": f"http://127.0.0.1:{port}/hooks/pre-tool-use",
            "timeout": 5,
            "statusMessage": "ClaudePad 审批拨杆检查中…",
        }
        if token:
            h["headers"] = {"X-ClaudePad-Token": token}
        return {"matcher": "*", "hooks": [h]}

    return {
        "matcher": "*",
        "hooks": [{
            "type": "command",
            "command": f'"{PYTHON}" "{HOOK}"',
            "timeout": 5,
            "statusMessage": "ClaudePad 审批拨杆检查中…",
        }],
    }


def is_claudepad_entry(entry: dict) -> bool:
    s = json.dumps(entry)
    return "claudepad_hook.py" in s or "X-ClaudePad-Token" in s or "/hooks/pre-tool-use" in s


def load_settings():
    if os.path.exists(SETTINGS):
        try:
            return json.load(open(SETTINGS, encoding="utf-8"))
        except Exception as e:
            print(f"❌ 现有 settings.json 解析失败：{e}")
            print(f"   路径：{SETTINGS}")
            print("   本脚本不会覆盖它，请先手动修复。")
            sys.exit(1)
    return {}


def merge(settings: dict, entry=None):
    hooks = settings.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    pre[:] = [e for e in pre if not is_claudepad_entry(e)]
    if entry:
        pre.append(entry)
    if not pre:
        hooks.pop("PreToolUse", None)
    if not hooks:
        settings.pop("hooks", None)
    return settings


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    uninstall = "--uninstall" in args
    mode = "http"
    port = DEFAULT_PORT
    for i, a in enumerate(args):
        if a == "--mode" and i + 1 < len(args):
            mode = args[i + 1]
        if a == "--port" and i + 1 < len(args):
            port = int(args[i + 1])

    token = "" if mode == "command" else get_or_create_token()

    print("=" * 74)
    print("ClaudePad 审批拨杆 hook 安装" + ("（卸载）" if uninstall else f"（{mode} 模式）"))
    print("=" * 74)
    print(f"  配置文件 : {SETTINGS}")
    if mode == "http":
        print(f"  端点     : http://127.0.0.1:{port}/hooks/pre-tool-use")
        print(f"  令牌     : {token[:8]}…（已存于 {os.path.join(core.STATE_DIR,'token')}）")
    else:
        print(f"  hook脚本 : {HOOK}")
        print(f"  Python   : {PYTHON}")
    print()

    entry = None if uninstall else build_entry(mode, port, token)
    settings = load_settings()
    before = json.dumps(settings, ensure_ascii=False, sort_keys=True)
    merged = merge(settings, entry)
    after = json.dumps(merged, ensure_ascii=False, sort_keys=True)

    print("将要写入的 hooks 段：")
    print("-" * 74)
    print(json.dumps(merged.get("hooks", {}), ensure_ascii=False, indent=2))
    print("-" * 74)
    print()

    if before == after:
        print("ℹ️  配置无变化（已是目标状态）")
        return 0

    if not apply:
        print("这是预览。确认无误后加 --apply 真正写入：")
        print(f"   python {os.path.basename(__file__)} --mode {mode} --apply")
        return 0

    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    if os.path.exists(SETTINGS):
        bak = SETTINGS + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(SETTINGS, bak)
        print(f"✅ 已备份原文件 → {os.path.basename(bak)}")

    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"✅ 已写入 {SETTINGS}")
    print()

    if uninstall:
        print("已卸载。审批拨杆不再生效，一切走原生流程。")
        return 0

    print("安装完成。接下来：")
    print(f"  1. 逻辑测试（不需要键盘、不需要 Claude Code）：")
    print(f"       python {os.path.join(HERE, 'test_hook.py')}")
    if mode == "http":
        print(f"  2. 启动守护进程（必须保持运行，否则 hook 失效）：")
        print(f"       python {os.path.join(HERE, 'claudepad_daemon.py')}")
    print(f"  3. 手动模拟拨杆，在 Claude Code 里验证真实效果：")
    print(f"       python {os.path.join(HERE, 'switchctl.py')} on")
    print(f"       python {os.path.join(HERE, 'switchctl.py')} off")
    return 0


if __name__ == "__main__":
    sys.exit(main())

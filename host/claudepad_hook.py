#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClaudePad 审批拨杆 —— PreToolUse Hook（command 模式 / 备用方案）
================================================================================
⚠️ 优先使用 HTTP 模式（claudepad_daemon.py）。本脚本是**没有守护进程时的降级方案**。

为什么是降级方案：command 类型 hook 每次调用都要起一个新进程。
实测 Windows 上 Python 启动约 **510ms**，每个工具调用都多等半秒。
HTTP 模式由常驻进程直接应答，延迟 < 2ms。

但本脚本仍有价值：
  · 不想常驻一个进程时可用
  · 逻辑与 daemon 共用 claudepad_core.py，行为完全一致
  · 拨杆 OFF 时只做一次 stat 就退出，是能找到的最快路径

依据 Claude Code 官方 hooks 文档：
  · 返回 {"hookSpecificOutput":{"permissionDecision":"allow"}} → 跳过权限提示
  · 返回空（exit 0 无输出）→ 不算批准，走原生权限流程
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claudepad_core as core     # noqa: E402


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)          # 解析失败 → 失效安全

    try:
        out = core.handle(payload)
    except Exception:
        sys.exit(0)          # 任何异常都不得导致误批

    if out is not None:
        print(json.dumps(out, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)

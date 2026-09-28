# -*- coding: utf-8 -*-
"""
让脚本输出不受 Windows 控制台代码页限制
================================================================================
这些脚本的输出里含中文、→、★、² 和 ✅ 等字符。当 stdout 被重定向到文件或管道
（Git Bash、IDE 输出面板、CI、`python xxx.py > log.txt`）时，Python 会按 locale
编码（简体中文 Windows 上是 cp936）去编码，碰到 ² / ✅ 直接抛 UnicodeEncodeError——
用户看到的是 traceback 而不是校验结果。

真实控制台窗口走的是宽字符 API，不受影响，所以这个 bug 只在重定向时出现。

用法：在脚本的 import 之后立刻调用 enable()。
"""

import sys


def enable():
    """把 stdout / stderr 切成 UTF-8，编码不了的字符降级而不是抛异常。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

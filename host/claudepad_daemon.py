#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClaudePad 常驻守护进程
================================================================================
一个进程干两件事：
  1. 【HTTP hook 服务】监听 127.0.0.1:PORT，接收 Claude Code 的 PreToolUse 请求
  2. 【键盘信号监听】监听全局按键，捕捉键盘拨杆发出的 F13/F14

为什么用 HTTP hook 而不是 command hook：
  实测 command hook 每次调用要起一个 Python 进程，Windows 上约 **510ms**。
  每个工具调用都多等半秒，不可接受。
  HTTP hook 由本进程直接应答，**延迟 < 2ms**，且省去进程创建开销。

失效安全：
  守护进程没跑 → HTTP 连接失败 → Claude Code 视为「非阻塞错误」→
  工具调用走**原生权限流程**。也就是说进程挂了只会退化成「正常询问」，
  绝不会变成「全部自动批准」。

用法：
    python claudepad_daemon.py              # 启动（默认端口 8787）
    python claudepad_daemon.py --port 9000
    python claudepad_daemon.py --no-keyboard   # 只跑 HTTP 服务，不监听键盘
"""

import argparse
import json
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import claudepad_core as core     # noqa: E402

DEFAULT_PORT = 8787
TOKEN_FILE = os.path.join(core.STATE_DIR, "token")

VK_F13, VK_F14 = 0x7C, 0x7D


# ============================== 访问令牌 ====================================
def get_or_create_token() -> str:
    """
    生成/读取本地访问令牌。

    为什么需要：守护进程监听在 127.0.0.1，理论上本机任何程序都能调它。
    加一个令牌可以防止本机的其他程序（或误配置的脚本）触发自动批准。
    """
    os.makedirs(core.STATE_DIR, exist_ok=True)
    if os.path.exists(TOKEN_FILE):
        t = open(TOKEN_FILE, encoding="utf-8").read().strip()
        if t:
            return t
    t = secrets.token_hex(16)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(t)
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except Exception:
        pass
    return t


# ============================== HTTP 服务 ===================================
class HookHandler(BaseHTTPRequestHandler):
    token = ""
    stats = {"allow": 0, "skip": 0, "denied": 0, "errors": 0}

    def log_message(self, *a):
        pass          # 静默，避免刷屏

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/status"):
            body = json.dumps({
                "ok": True,
                "approval": core.approval_on(),
                "stats": self.stats,
                "port": self.server.server_address[1],
            }, ensure_ascii=False).encode()
            self._send(200, body)
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        if not self.path.startswith("/hooks/pre-tool-use"):
            self._send(404, b'{"error":"not found"}')
            return

        # ---- 令牌校验 ----
        if self.token:
            got = self.headers.get("X-ClaudePad-Token", "")
            if not secrets.compare_digest(got, self.token):
                self.stats["denied"] += 1
                # 令牌不对 → 返回非 2xx，Claude Code 视为非阻塞错误，走原生流程
                self._send(403, b'{"error":"bad token"}')
                return

        # ---- 读输入 ----
        try:
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n) if n else b""
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self.stats["errors"] += 1
            self._send(200, b"{}")          # 解析失败 → 无决策，走原生流程
            return

        # ---- 决策 ----
        try:
            out = core.handle(payload)
        except Exception:
            self.stats["errors"] += 1
            self._send(200, b"{}")          # 任何异常都不得导致误批
            return

        if out is None:
            self.stats["skip"] += 1
            self._send(200, b"{}")          # 无决策 → 原生流程
        else:
            self.stats["allow"] += 1
            self._send(200, json.dumps(out, ensure_ascii=False).encode())


# ============================== 键盘监听 ====================================
def start_keyboard_listener():
    """在后台线程监听全局按键，捕捉键盘拨杆信号"""
    try:
        from pynput import keyboard
    except ImportError:
        print("⚠️  未安装 pynput，键盘监听已跳过。")
        print("   安装后可自动跟随键盘拨杆：pip install pynput")
        print("   现在可用 CLI 手动控制：python switchctl.py on|off")
        return None

    MOD_KEYS = {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}
    state = {"mods": set()}

    def combo_active():
        s = state["mods"]
        return (any("ctrl" in str(k) for k in s)
                and any("alt" in str(k) for k in s)
                and any("shift" in str(k) for k in s))

    def on_press(key):
        if key in MOD_KEYS:
            state["mods"].add(key)
            return
        vk = getattr(key, "vk", None)
        name = getattr(key, "name", str(key))
        if vk == VK_F13 or name == "f13":
            if combo_active():
                core.write_log({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "event": "perm_reset_request", "source": "keyboard"})
                print("  ⟳ 收到「复位到 default」请求")
            else:
                core.set_approval(True, source="keyboard")
                print("  🟢 拨杆 → ON（自动批准已启用）")
        elif vk == VK_F14 or name == "f14":
            core.write_log({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "event": "model_cycle_request", "source": "keyboard"})
            print("  ⟳ 收到「循环切换模型」请求")

    def on_release(key):
        if key in MOD_KEYS:
            state["mods"].discard(key)
            return
        vk = getattr(key, "vk", None)
        name = getattr(key, "name", str(key))
        if (vk == VK_F13 or name == "f13") and core.approval_on():
            core.set_approval(False, source="keyboard")
            print("  ⚪ 拨杆 → OFF（不干预）")

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    return listener


# ============================== 入口 ========================================
def main():
    ap = argparse.ArgumentParser(description="ClaudePad 常驻守护进程")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-keyboard", action="store_true",
                    help="只跑 HTTP 服务，不监听键盘")
    ap.add_argument("--no-token", action="store_true",
                    help="关闭访问令牌校验（仅本机调试用）")
    args = ap.parse_args()

    token = "" if args.no_token else get_or_create_token()
    HookHandler.token = token

    print("=" * 68)
    print("ClaudePad 常驻守护进程")
    print("=" * 68)
    print(f"  HTTP hook 地址 : http://127.0.0.1:{args.port}/hooks/pre-tool-use")
    print(f"  访问令牌       : {'（已关闭）' if not token else token[:8] + '…'}")
    print(f"  当前拨杆状态   : {'🟢 ON' if core.approval_on() else '⚪ OFF'}")
    print()

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", args.port), HookHandler)
    except OSError as e:
        print(f"❌ 端口 {args.port} 无法绑定：{e}")
        print("   换个端口：python claudepad_daemon.py --port 8788")
        return 1

    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    print(f"  ✅ HTTP 服务已启动")

    if not args.no_keyboard:
        kl = start_keyboard_listener()
        if kl:
            print("  ✅ 键盘监听已启动（F13 = 审批拨杆）")
    print()
    print("  按 Ctrl+C 退出")
    print()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n正在退出…")
        srv.shutdown()
        print(f"本次统计：批准 {HookHandler.stats['allow']} ｜ "
              f"放行 {HookHandler.stats['skip']} ｜ "
              f"拒绝令牌 {HookHandler.stats['denied']} ｜ "
              f"错误 {HookHandler.stats['errors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

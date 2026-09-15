#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClaudePad 拨杆控制器（宿主侧）
================================================================================
两个用途：
  1. 【守护模式】监听全局键盘事件，捕捉键盘发来的信号键，维护拨杆状态
  2. 【手动模式】命令行直接开关拨杆，用于**没有键盘硬件时也能测试整条链路**

键盘发来的信号（见 firmware/boards/shields/claudepad/claudepad.keymap）：
  · F13 按下 / 释放  → 审批拨杆 ON / OFF
  · Ctrl+Alt+Shift+F14 → 「循环切换模型」请求
  · Ctrl+Alt+Shift+F13 → 「复位到 default」请求

状态存放：~/.claudepad/
  · approval.on      存在 = 拨杆 ON（hook 只做一次 stat，保证快路径）
  · state.json       详细状态（模式、模型、时间戳），供后续扩展

用法：
    python switchctl.py status          # 查看当前状态
    python switchctl.py on              # 手动打开（模拟拨杆 ON）
    python switchctl.py off             # 手动关闭
    python switchctl.py toggle          # 切换
    python switchctl.py watch           # 守护模式：监听键盘信号键
    python switchctl.py log [N]         # 查看最近 N 条审批日志
    python switchctl.py reset-log       # 清空日志
"""

import json
import os
import sys
import time

STATE_DIR = os.path.join(os.path.expanduser("~"), ".claudepad")
FLAG_FILE = os.path.join(STATE_DIR, "approval.on")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
LOG_FILE = os.path.join(STATE_DIR, "approvals.jsonl")
EVENT_FILE = os.path.join(STATE_DIR, "events.jsonl")

# F13 / F14 的 Windows 虚拟键码（pynput 在某些版本里没有 Key.f13 枚举）
VK_F13 = 0x7C
VK_F14 = 0x7D


def ensure_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def read_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {}


def write_state(**kw):
    ensure_dir()
    st = read_state()
    st.update(kw)
    st["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    return st


def set_approval(on: bool, source: str = "cli"):
    """切换审批拨杆状态。flag 文件的存在性就是状态本身。"""
    ensure_dir()
    if on:
        with open(FLAG_FILE, "w", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        try:
            os.remove(FLAG_FILE)
        except FileNotFoundError:
            pass
    write_state(approval=on, source=source)
    return on


def is_on() -> bool:
    return os.path.exists(FLAG_FILE)


def log_event(kind, detail=""):
    try:
        ensure_dir()
        with open(EVENT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "event": kind, "detail": detail,
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ============================== 命令行 ======================================
def cmd_status():
    on = is_on()
    st = read_state()
    print("=" * 56)
    print("ClaudePad 拨杆状态")
    print("=" * 56)
    print(f"  审批拨杆      : {'🟢 ON（自动批准已启用）' if on else '⚪ OFF（不干预）'}")
    print(f"  状态目录      : {STATE_DIR}")
    print(f"  flag 文件     : {'存在' if on else '不存在'}")
    if st:
        print(f"  最后更新      : {st.get('updated_at', '-')}")
        print(f"  来源          : {st.get('source', '-')}")
        if st.get("permission_mode"):
            print(f"  权限模式      : {st['permission_mode']}")
        if st.get("model"):
            print(f"  当前模型      : {st['model']}")
    if on:
        print()
        print("  ⚠️  自动批准已开启 —— Claude Code 的工具调用将不再询问")
        print("     危险命令（rm -rf / sudo / git push --force 等）仍会询问")
    return 0


def cmd_on():
    set_approval(True)
    log_event("approval_on", "cli")
    print("🟢 审批拨杆 → ON（自动批准已启用）")
    print("   危险命令与 AskUserQuestion 仍会询问")
    return 0


def cmd_off():
    set_approval(False)
    log_event("approval_off", "cli")
    print("⚪ 审批拨杆 → OFF（不干预，一切走原生流程）")
    return 0


def cmd_toggle():
    return cmd_off() if is_on() else cmd_on()


def cmd_log(n=20):
    if not os.path.exists(LOG_FILE):
        print("（暂无审批日志）")
        return 0
    lines = open(LOG_FILE, encoding="utf-8").read().strip().split("\n")
    lines = [l for l in lines if l.strip()]
    print(f"最近 {min(n, len(lines))} 条审批记录（共 {len(lines)} 条）")
    print("-" * 76)
    for l in lines[-n:]:
        try:
            e = json.loads(l)
            d = e.get("decision", "?")
            mark = "✅" if d == "allow" else ("⏭️" if d == "skipped" else "❓")
            extra = e.get("command") or e.get("file") or ""
            print(f"{mark} {e.get('ts','')}  {e.get('tool',''):<16} "
                  f"{d:<8} {e.get('reason','')[:28]:<30} {extra[:34]}")
        except Exception:
            print(l[:100])
    return 0


def cmd_reset_log():
    for f in (LOG_FILE, EVENT_FILE):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    print("日志已清空")
    return 0


# ============================== 守护模式 ====================================
def cmd_watch():
    try:
        from pynput import keyboard
    except ImportError:
        print("❌ 未安装 pynput，无法进入守护模式。")
        print("   安装：pip install pynput")
        print("   或先用手动模式测试：python switchctl.py on")
        return 1

    print("=" * 60)
    print("ClaudePad 拨杆守护进程")
    print("=" * 60)
    print("  监听：F13 = 审批拨杆（按下 ON / 释放 OFF）")
    print("        Ctrl+Alt+Shift+F14 = 循环切换模型")
    print("        Ctrl+Alt+Shift+F13 = 复位到 default")
    print("  按 Ctrl+C 退出")
    print()

    # 修饰键状态（用于区分裸 F13 与 Ctrl+Alt+Shift+F13）
    mods = set()
    MOD_KEYS = {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}

    def vk_of(k):
        return getattr(k, "vk", None)

    def name_of(k):
        return getattr(k, "name", str(k))

    def on_press(key):
        nonlocal mods
        if key in MOD_KEYS:
            mods.add(key)
            return
        vk = vk_of(key)
        combo = len([m for m in mods if "ctrl" in str(m)]) and \
                len([m for m in mods if "alt" in str(m)]) and \
                len([m for m in mods if "shift" in str(m)])

        if vk == VK_F13 or name_of(key) == "f13":
            if combo:
                # Ctrl+Alt+Shift+F13 → 复位请求
                log_event("perm_reset_request", "keyboard")
                write_state(perm_reset_requested=time.strftime("%Y-%m-%dT%H:%M:%S"))
                print("  ⟳ 收到「复位到 default」请求（上位机需执行真正的复位）")
            else:
                set_approval(True, source="keyboard")
                log_event("approval_on", "keyboard")
                print("  🟢 拨杆 → ON（自动批准已启用）")
        elif vk == VK_F14 or name_of(key) == "f14":
            log_event("model_cycle_request", "keyboard")
            write_state(model_cycle_requested=time.strftime("%Y-%m-%dT%H:%M:%S"))
            print("  ⟳ 收到「循环切换模型」请求（上位机需执行真正的切换）")

    def on_release(key):
        nonlocal mods
        if key in MOD_KEYS:
            mods.discard(key)
            return
        vk = vk_of(key)
        if (vk == VK_F13 or name_of(key) == "f13") and is_on():
            set_approval(False, source="keyboard")
            log_event("approval_off", "keyboard")
            print("  ⚪ 拨杆 → OFF（不干预）")

    try:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
            l.join()
    except KeyboardInterrupt:
        print("\n已退出守护进程。")
    return 0


# ============================== 入口 ========================================
COMMANDS = {
    "status": cmd_status,
    "on": cmd_on,
    "off": cmd_off,
    "toggle": cmd_toggle,
    "watch": cmd_watch,
    "log": cmd_log,
    "reset-log": cmd_reset_log,
}


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = args[0]
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"❌ 未知命令：{cmd}")
        print(f"   可用：{', '.join(COMMANDS)}")
        return 1
    if cmd == "log" and len(args) > 1:
        try:
            return fn(int(args[1]))
        except ValueError:
            pass
    return fn()


if __name__ == "__main__":
    sys.exit(main())

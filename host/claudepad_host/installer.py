"""Install/uninstall Claude Code hooks and the status line."""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import time
from pathlib import Path

from . import core

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_SRC = Path(__file__).resolve().parents[1] / "scripts"
DEFAULT_DEST = Path.home() / ".claude" / "claudepad"
DEFAULT_SETTINGS = Path.home() / ".claude" / "settings.json"

PERMISSION_EVENT = "PermissionRequest"
HOOK_EVENTS = ("PermissionRequest", "UserPromptSubmit", "Stop", "SessionStart")
OUR_HOOK_FILES = ("hook_permission.py", "hook_state.py")
COPY_FILES = ("statusline.py", "hook_state.py")


def _as_posix(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _is_our_hook(hook: dict) -> bool:
    if not isinstance(hook, dict):
        return False
    haystack = " ".join(
        [str(hook.get("command", ""))]
        + [str(item) for item in hook.get("args", [])]
    ).lower()
    return "claudepad" in haystack or any(name in haystack for name in OUR_HOOK_FILES)


def _is_our_statusline(status_line: dict | None) -> bool:
    if not isinstance(status_line, dict):
        return False
    return "claudepad" in str(status_line.get("command", "")).lower()


def _hook_entry(script: str, python_exe: str, dest: Path) -> dict:
    return {
        "type": "command",
        "command": _as_posix(python_exe),
        "args": [_as_posix(dest / script)],
        "timeout": 10,
    }


def _strip_our_hooks(settings: dict) -> None:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
        settings["hooks"] = hooks

    for event in HOOK_EVENTS:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            entries = []
        cleaned = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            inner = entry.get("hooks")
            if isinstance(inner, list):
                kept = [hook for hook in inner if not _is_our_hook(hook)]
                if kept:
                    replacement = dict(entry)
                    replacement["hooks"] = kept
                    cleaned.append(replacement)
            else:
                cleaned.append(entry)
        hooks[event] = cleaned


def merge_settings(settings: dict, python_exe: str | None = None, dest: str | Path | None = None) -> dict:
    """Return a copy of settings with ClaudePad hooks and status line."""
    python_exe = python_exe or sys.executable
    dest = Path(dest or DEFAULT_DEST)

    result = copy.deepcopy(settings) if isinstance(settings, dict) else {}
    _strip_our_hooks(result)
    hooks = result["hooks"]

    for event in HOOK_EVENTS:
        hooks.setdefault(event, []).append(
            {"hooks": [_hook_entry("hook_state.py", python_exe, dest)]}
        )

    statusline = f'"{_as_posix(python_exe)}" "{_as_posix(dest / "statusline.py")}"'
    result["statusLine"] = {"type": "command", "command": statusline}
    return result


def _backup_settings(settings_path: Path) -> Path | None:
    if not settings_path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = settings_path.with_name(f"{settings_path.name}.claudepad-backup-{stamp}")
    shutil.copy2(settings_path, backup)
    return backup


def _copy_scripts(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in COPY_FILES:
        shutil.copy2(SCRIPTS_SRC / name, dest / name)
    shutil.copy2(Path(__file__).with_name("core.py"), dest / "claudepad_core.py")
    legacy = dest / "hook_permission.py"
    if legacy.exists():
        legacy.unlink()


def _install_autostart(python_exe: str) -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    startup = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if not startup.exists():
        return None

    python = Path(python_exe)
    pythonw = python.with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else python
    host_dir = PROJECT_ROOT / "host"
    if not host_dir.exists():
        host_dir = Path.cwd()

    vbs = startup / "ClaudePadHost.vbs"
    content = (
        'Set sh = CreateObject("WScript.Shell")\r\n'
        f'sh.CurrentDirectory = "{host_dir}"\r\n'
        f'sh.Run """{_as_posix(runner)}"" -m claudepad_host run", 0, False\r\n'
    )
    # UTF-16 with BOM keeps non-ASCII Windows profile paths intact.
    vbs.write_text(content, encoding="utf-16")
    return vbs


def _remove_autostart() -> None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return
    vbs = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "ClaudePadHost.vbs"
    try:
        vbs.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def install(
    settings_path: str | Path | None = None,
    dest: str | Path | None = None,
    autostart: bool = False,
    python_exe: str | None = None,
) -> int:
    _configure_stdio()
    settings_path = Path(settings_path or DEFAULT_SETTINGS)
    dest = Path(dest or DEFAULT_DEST)
    python_exe = python_exe or sys.executable

    core.ensure_dirs()
    core.ensure_config()
    _copy_scripts(dest)

    settings: dict = {}
    backup = None
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                raise ValueError("settings.json must contain an object")
        except (OSError, ValueError) as exc:
            print(f"无法读取 {settings_path}: {exc}", file=sys.stderr)
            return 1
        backup = _backup_settings(settings_path)

    state_path = core.install_state_path()
    state = core.read_json(state_path, {})
    if not isinstance(state, dict):
        state = {}
    if "previous_status_line" not in state:
        existing = settings.get("statusLine")
        state["previous_status_line"] = None if _is_our_statusline(existing) else existing
    state["settings_backup"] = str(backup) if backup else None
    state["installed_at"] = time.time()
    core.write_json(state_path, state)

    merged = merge_settings(settings, python_exe=python_exe, dest=dest)
    core.write_json(settings_path, merged)

    autostart_path = _install_autostart(python_exe) if autostart else None

    print("ClaudePad hooks 已安装。")
    print(f"  设置文件: {settings_path}")
    print(f"  脚本目录: {dest}")
    if backup:
        print(f"  备份: {backup}")
    if autostart_path:
        print(f"  开机自启: {autostart_path}")
    print("下一步: python -m claudepad_host run")
    return 0


def uninstall(settings_path: str | Path | None = None, dest: str | Path | None = None) -> int:
    _configure_stdio()
    settings_path = Path(settings_path or DEFAULT_SETTINGS)

    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                raise ValueError("settings.json must contain an object")
        except (OSError, ValueError) as exc:
            print(f"无法读取 {settings_path}: {exc}", file=sys.stderr)
            return 1

        _backup_settings(settings_path)
        _strip_our_hooks(settings)

        state = core.read_json(core.install_state_path(), {})
        previous = state.get("previous_status_line") if isinstance(state, dict) else None
        if isinstance(previous, dict):
            settings["statusLine"] = previous
        else:
            settings.pop("statusLine", None)

        core.write_json(settings_path, settings)
        print(f"已移除 ClaudePad hooks / statusLine: {settings_path}")
    else:
        print(f"未找到 {settings_path}，跳过设置文件。")

    _remove_autostart()
    print("完成。")
    return 0

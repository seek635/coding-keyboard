"""Shared state and decision logic for ClaudePad.

This module is standard-library only. The installer copies it next to the
Claude Code hook scripts as ``claudepad_core.py``.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

APP_DIR_NAME = "ClaudePad"
DEFAULT_MODELS = ["opus", "sonnet", "haiku"]
DEFAULT_CYCLE = ["default", "acceptEdits", "plan", "auto"]
MODE_ALIASES = {"manual": "default"}
SESSION_SUFFIX_STATUS = ".status.json"
SESSION_SUFFIX_MODE = ".mode.json"


def state_dir() -> Path:
    override = os.environ.get("CLAUDEPAD_STATE_DIR")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / ".claudepad"


def sessions_dir() -> Path:
    return state_dir() / "sessions"


def config_path() -> Path:
    return state_dir() / "config.json"


def log_path() -> Path:
    return state_dir() / "daemon.log"


def hooks_log_path() -> Path:
    return state_dir() / "hooks.log"


def install_state_path() -> Path:
    return state_dir() / "install.json"


def ensure_dirs() -> None:
    sessions_dir().mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".claudepad-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def default_config() -> dict:
    return {
        "models": list(DEFAULT_MODELS),
        "permission_cycle": list(DEFAULT_CYCLE),
        "assume_mode": "auto",
    }


def load_config() -> dict:
    raw = read_json(config_path(), {})
    cfg = default_config()
    if not isinstance(raw, dict):
        return cfg

    models = raw.get("models")
    if isinstance(models, list):
        cleaned = [str(item).strip() for item in models if str(item).strip()]
        if cleaned:
            cfg["models"] = cleaned

    cycle = raw.get("permission_cycle")
    if isinstance(cycle, list):
        cleaned_cycle = normalize_cycle(cycle)
        if "default" in cleaned_cycle:
            cfg["permission_cycle"] = cleaned_cycle

    assume = normalize_mode(raw.get("assume_mode"))
    if assume and assume in cfg["permission_cycle"]:
        cfg["assume_mode"] = assume
    return cfg


def ensure_config() -> dict:
    if not config_path().exists():
        cfg = default_config()
        write_json(config_path(), cfg)
        return cfg
    return load_config()


def normalize_mode(mode: Any) -> str:
    if mode is None:
        return ""
    value = str(mode).strip()
    if not value:
        return ""
    return MODE_ALIASES.get(value, value)


def normalize_cycle(cycle: list) -> list:
    out: list[str] = []
    for item in cycle or []:
        value = normalize_mode(item)
        if value and value not in out:
            out.append(value)
    if "default" not in out:
        out.insert(0, "default")
    return out


def resolve_mode(current: Any, config: dict) -> str:
    cycle = normalize_cycle(config.get("permission_cycle", DEFAULT_CYCLE))
    mode = normalize_mode(current)
    if mode in cycle:
        return mode
    assumed = normalize_mode(config.get("assume_mode", "auto"))
    if assumed in cycle:
        return assumed
    return "default" if "default" in cycle else cycle[0]


def presses_to_default(current: Any, cycle: list) -> int:
    """Forward Shift+Tab presses needed to land on default."""
    normalized_cycle = normalize_cycle(cycle)
    mode = normalize_mode(current)
    if mode not in normalized_cycle:
        raise ValueError(f"unknown permission mode: {current!r}")
    return (len(normalized_cycle) - normalized_cycle.index(mode)) % len(normalized_cycle)


def next_permission_mode(current: Any, config: dict) -> str:
    """The mode Shift+Tab would move to next."""
    cycle = normalize_cycle(config.get("permission_cycle", DEFAULT_CYCLE))
    mode = normalize_mode(current)
    if mode not in cycle:
        mode = resolve_mode(current, config)
    return cycle[(cycle.index(mode) + 1) % len(cycle)]


def next_model(model_id: Any, model_name: Any, models: list) -> str:
    cleaned = [str(item).strip() for item in (models or []) if str(item).strip()]
    if not cleaned:
        return ""
    haystack = f"{model_id or ''} {model_name or ''}".lower()
    index = -1
    for i, alias in enumerate(cleaned):
        if alias.lower() in haystack:
            index = i
            break
    if index < 0:
        return cleaned[0]
    return cleaned[(index + 1) % len(cleaned)]


def _safe_session_name(session_id: Any) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(session_id or "unknown"))
    value = value.strip("._")
    return (value or "unknown")[:120]


def session_status_path(session_id: Any) -> Path:
    return sessions_dir() / f"{_safe_session_name(session_id)}{SESSION_SUFFIX_STATUS}"


def session_mode_path(session_id: Any) -> Path:
    return sessions_dir() / f"{_safe_session_name(session_id)}{SESSION_SUFFIX_MODE}"


def _merge_session_payload(path: Path, payload: dict) -> None:
    existing = read_json(path, {})
    if not isinstance(existing, dict):
        existing = {}
    for key, value in payload.items():
        if value is not None:
            existing[key] = value
    existing["updated_at"] = time.time()
    write_json(path, existing)


def write_status(payload: dict) -> None:
    session_id = payload.get("session_id") or "unknown"
    _merge_session_payload(session_status_path(session_id), payload)


def write_mode(payload: dict) -> None:
    session_id = payload.get("session_id") or "unknown"
    _merge_session_payload(session_mode_path(session_id), payload)


def _iter_session_payloads() -> dict:
    result: dict[str, dict] = {}
    directory = sessions_dir()
    if not directory.exists():
        return result
    for path in directory.glob("*.json"):
        name = path.name
        if name.endswith(SESSION_SUFFIX_STATUS):
            kind, session_id = "status", name[: -len(SESSION_SUFFIX_STATUS)]
        elif name.endswith(SESSION_SUFFIX_MODE):
            kind, session_id = "mode", name[: -len(SESSION_SUFFIX_MODE)]
        else:
            continue
        data = read_json(path, {})
        if not isinstance(data, dict):
            continue
        try:
            data["_mtime"] = path.stat().st_mtime
        except OSError:
            data["_mtime"] = 0.0
        result.setdefault(session_id, {})[kind] = data
    return result


def read_active_state() -> dict:
    sessions = _iter_session_payloads()
    if not sessions:
        return {}

    def latest_mtime(entry: dict) -> float:
        return max((float(payload.get("_mtime", 0)) for payload in entry.values()), default=0.0)

    session_id = max(sessions, key=lambda key: latest_mtime(sessions[key]))
    entry = sessions[session_id]
    status = entry.get("status", {})
    mode = entry.get("mode", {})

    candidates = []
    for source in (mode, status):
        value = source.get("permission_mode")
        if value:
            candidates.append((float(source.get("_mtime", 0)), value))
    permission_mode = max(candidates, key=lambda item: item[0])[1] if candidates else None

    return {
        "session_id": status.get("session_id") or mode.get("session_id") or session_id,
        "model_id": status.get("model_id"),
        "model_name": status.get("model_name"),
        "permission_mode": permission_mode,
        "cwd": status.get("cwd") or mode.get("cwd"),
        "status_updated_at": float(status.get("_mtime", 0)),
        "mode_updated_at": float(mode.get("_mtime", 0)),
        "updated_at": latest_mtime(entry),
    }


def write_mode_override(session_id: Any, mode: str) -> None:
    if not session_id:
        return
    write_mode({"session_id": str(session_id), "permission_mode": mode, "source": "daemon"})


def write_model_override(session_id: Any, model: str) -> None:
    if not session_id:
        return
    write_status({"session_id": str(session_id), "model_id": model, "model_name": model, "source": "daemon"})


def hook_log(name: str, message: str) -> None:
    try:
        ensure_dirs()
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with hooks_log_path().open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} [{name}] {message}\n")
    except OSError:
        pass

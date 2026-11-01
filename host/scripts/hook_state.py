#!/usr/bin/env python3
"""Write permission_mode/cwd from Claude Code hook events."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import claudepad_core as core
    except Exception:
        return 0

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            return 0
        session_id = data.get("session_id")
        mode = data.get("permission_mode")
        if session_id and mode:
            core.write_mode(
                {
                    "session_id": session_id,
                    "permission_mode": mode,
                    "cwd": data.get("cwd"),
                    "source": data.get("hook_event_name"),
                }
            )
    except Exception as exc:
        try:
            core.hook_log("hook_state", repr(exc))
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

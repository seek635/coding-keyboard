#!/usr/bin/env python3
"""Claude Code statusLine command for ClaudePad.

Writes model/session state and prints the visible status line. Errors never
break the status line.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import claudepad_core as core
    except Exception:
        print("ClaudePad")
        return 0

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            data = {}

        model = data.get("model") or {}
        workspace = data.get("workspace") or {}
        cwd = workspace.get("current_dir") or data.get("cwd")
        session_id = data.get("session_id") or "unknown"

        core.write_status(
            {
                "session_id": session_id,
                "model_id": model.get("id"),
                "model_name": model.get("display_name"),
                "cwd": cwd,
                "permission_mode": data.get("permission_mode"),
            }
        )

        parts = ["ClaudePad"]
        if model.get("display_name"):
            parts.append(str(model["display_name"]))
        if cwd:
            name = Path(str(cwd)).name
            parts.append(name or str(cwd))
        context = data.get("context_window") or {}
        percentage = context.get("used_percentage")
        if isinstance(percentage, (int, float)):
            parts.append(f"{percentage:.0f}% ctx")
        print(" | ".join(parts))
    except Exception as exc:  # never let the status line fail
        try:
            core.hook_log("statusline", repr(exc))
        except Exception:
            pass
        print("ClaudePad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

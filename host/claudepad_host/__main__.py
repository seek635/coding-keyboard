"""Command line entry point for the ClaudePad host."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, core


def _status() -> int:
    config = core.ensure_config()
    state = core.read_active_state()
    payload = {
        "version": __version__,
        "state_dir": str(core.state_dir()),
        "active_session": state,
        "config": config,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="claudepad-host",
        description="ClaudePad companion host for Claude Code on Windows",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="start the background host")
    install_parser = subparsers.add_parser("install", help="install hooks and status line")
    install_parser.add_argument("--autostart", action="store_true", help="start the host at login")
    subparsers.add_parser("uninstall", help="remove hooks and status line")
    subparsers.add_parser("status", help="show the current state as JSON")

    args = parser.parse_args(argv)
    command = args.command or "run"

    if command == "run":
        if sys.platform != "win32":
            print("ClaudePad host requires Windows.", file=sys.stderr)
            return 2
        from .daemon import run

        return run()

    if command == "install":
        from .installer import install

        return install(autostart=args.autostart)

    if command == "uninstall":
        from .installer import uninstall

        return uninstall()

    if command == "status":
        return _status()

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claudepad_host import core, installer  # noqa: E402

HOOK_EVENTS = ("PermissionRequest", "UserPromptSubmit", "Stop", "SessionStart")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings = self.root / "settings.json"
        self.dest = self.root / "claudepad"
        os.environ["CLAUDEPAD_STATE_DIR"] = str(self.root / "state")
        core.ensure_dirs()

    def tearDown(self):
        os.environ.pop("CLAUDEPAD_STATE_DIR", None)
        self.tmp.cleanup()

    def _write_settings(self, data: dict) -> None:
        self.settings.write_text(json.dumps(data), encoding="utf-8")

    def _read_settings(self) -> dict:
        return json.loads(self.settings.read_text(encoding="utf-8"))

    @staticmethod
    def _hook_args(settings: dict, event: str, script: str) -> list:
        found = []
        for entry in settings.get("hooks", {}).get(event, []):
            for hook in entry.get("hooks", []):
                args = hook.get("args", [])
                if any(script in str(item) for item in args):
                    found.append(hook)
        return found

    def test_merge_preserves_unrelated_hooks(self):
        settings = {
            "hooks": {
                "PermissionRequest": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "other.py"}]}
                ],
                "Stop": [{"hooks": [{"type": "command", "command": "other-stop.py"}]}],
            },
            "statusLine": {"type": "command", "command": "old-status"},
        }
        merged = installer.merge_settings(settings, python_exe="C:/python.exe", dest=self.dest)

        commands = [
            hook.get("command")
            for entry in merged["hooks"]["PermissionRequest"]
            for hook in entry.get("hooks", [])
        ]
        self.assertIn("other.py", commands)
        self.assertEqual(len(self._hook_args(merged, "PermissionRequest", "hook_state.py")), 1)
        self.assertEqual(self._hook_args(merged, "PermissionRequest", "hook_permission.py"), [])

        stop_commands = [
            hook.get("command")
            for entry in merged["hooks"]["Stop"]
            for hook in entry.get("hooks", [])
        ]
        self.assertIn("other-stop.py", stop_commands)
        self.assertEqual(len(self._hook_args(merged, "Stop", "hook_state.py")), 1)

        self.assertIn("statusline.py", merged["statusLine"]["command"])
        self.assertNotEqual(merged["statusLine"]["command"], "old-status")

    def test_merge_is_idempotent(self):
        settings: dict = {}
        for _ in range(2):
            settings = installer.merge_settings(settings, python_exe="C:/python.exe", dest=self.dest)

        for event in HOOK_EVENTS:
            self.assertEqual(len(self._hook_args(settings, event, "hook_state.py")), 1)
            self.assertEqual(self._hook_args(settings, event, "hook_permission.py"), [])

    def test_legacy_permission_hook_is_removed(self):
        settings = {
            "hooks": {
                "PermissionRequest": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "C:/python.exe",
                                "args": ["C:/claudepad/hook_permission.py"],
                            }
                        ]
                    }
                ]
            }
        }
        merged = installer.merge_settings(settings, python_exe="C:/python.exe", dest=self.dest)
        self.assertEqual(self._hook_args(merged, "PermissionRequest", "hook_permission.py"), [])
        self.assertEqual(len(self._hook_args(merged, "PermissionRequest", "hook_state.py")), 1)

    def test_install_uninstall_roundtrip(self):
        self._write_settings(
            {
                "statusLine": {"type": "command", "command": "my-old-status"},
                "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "keep-me"}]}]},
            }
        )

        rc = installer.install(
            settings_path=self.settings,
            dest=self.dest,
            autostart=False,
            python_exe=sys.executable,
        )
        self.assertEqual(rc, 0)

        data = self._read_settings()
        self.assertIn("claudepad", data["statusLine"]["command"].lower())
        self.assertTrue((self.dest / "hook_state.py").exists())
        self.assertTrue((self.dest / "statusline.py").exists())
        self.assertTrue((self.dest / "claudepad_core.py").exists())
        self.assertFalse((self.dest / "hook_permission.py").exists())

        rc = installer.uninstall(settings_path=self.settings, dest=self.dest)
        self.assertEqual(rc, 0)

        data = self._read_settings()
        self.assertEqual(data["statusLine"]["command"], "my-old-status")
        stop_commands = [
            hook.get("command")
            for entry in data["hooks"]["Stop"]
            for hook in entry.get("hooks", [])
        ]
        self.assertEqual(stop_commands, ["keep-me"])
        for event in HOOK_EVENTS:
            self.assertEqual(self._hook_args(data, event, "hook_state.py"), [])


if __name__ == "__main__":
    unittest.main()

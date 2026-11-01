from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claudepad_host import core  # noqa: E402


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["CLAUDEPAD_STATE_DIR"] = self.tmp.name
        core.ensure_dirs()

    def tearDown(self):
        os.environ.pop("CLAUDEPAD_STATE_DIR", None)
        self.tmp.cleanup()

    def test_presses_to_default(self):
        cycle = ["default", "acceptEdits", "plan", "auto"]
        self.assertEqual(core.presses_to_default("auto", cycle), 1)
        self.assertEqual(core.presses_to_default("plan", cycle), 2)
        self.assertEqual(core.presses_to_default("acceptEdits", cycle), 3)
        self.assertEqual(core.presses_to_default("default", cycle), 0)
        self.assertEqual(core.presses_to_default("manual", cycle), 0)

    def test_presses_with_bypass(self):
        cycle = ["default", "acceptEdits", "plan", "bypassPermissions", "auto"]
        self.assertEqual(core.presses_to_default("auto", cycle), 1)
        self.assertEqual(core.presses_to_default("bypassPermissions", cycle), 2)

    def test_resolve_mode(self):
        config = {"permission_cycle": ["default", "acceptEdits", "plan", "auto"], "assume_mode": "auto"}
        self.assertEqual(core.resolve_mode("plan", config), "plan")
        self.assertEqual(core.resolve_mode("dontAsk", config), "auto")
        self.assertEqual(core.resolve_mode(None, config), "auto")

    def test_next_permission_mode(self):
        config = {"permission_cycle": ["default", "acceptEdits", "plan", "auto"]}
        self.assertEqual(core.next_permission_mode("default", config), "acceptEdits")
        self.assertEqual(core.next_permission_mode("acceptEdits", config), "plan")
        self.assertEqual(core.next_permission_mode("plan", config), "auto")
        self.assertEqual(core.next_permission_mode("auto", config), "default")
        self.assertEqual(core.next_permission_mode("dontAsk", config), "default")

    def test_next_model(self):
        models = ["opus", "sonnet", "haiku"]
        self.assertEqual(core.next_model("claude-opus-5-5", "Opus", models), "sonnet")
        self.assertEqual(core.next_model("claude-sonnet-5", "Sonnet", models), "haiku")
        self.assertEqual(core.next_model("claude-haiku-4-5", "Haiku", models), "opus")
        self.assertEqual(core.next_model("mystery", "Mystery", models), "opus")

    def test_active_state_merges_status_and_mode(self):
        core.write_status(
            {
                "session_id": "s1",
                "model_id": "claude-opus-5-5",
                "model_name": "Opus",
                "cwd": "D:/a",
            }
        )
        time.sleep(0.04)
        core.write_mode({"session_id": "s1", "permission_mode": "plan", "cwd": "D:/a"})
        time.sleep(0.04)
        core.write_status(
            {
                "session_id": "s2",
                "model_id": "claude-sonnet-5",
                "model_name": "Sonnet",
                "cwd": "D:/b",
            }
        )

        state = core.read_active_state()
        self.assertEqual(state["session_id"], "s2")
        self.assertEqual(state["model_name"], "Sonnet")

        time.sleep(0.04)
        core.write_mode({"session_id": "s1", "permission_mode": "auto", "cwd": "D:/a"})
        state = core.read_active_state()
        self.assertEqual(state["session_id"], "s1")
        self.assertEqual(state["permission_mode"], "auto")
        self.assertEqual(state["model_name"], "Opus")

    def test_session_paths_are_sanitized(self):
        path = core.session_status_path("../../evil")
        self.assertEqual(path.parent, core.sessions_dir())
        self.assertNotIn("..", path.name)


if __name__ == "__main__":
    unittest.main()

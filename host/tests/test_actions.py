from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claudepad_host import core  # noqa: E402


CONFIG = {
    "permission_cycle": ["default", "acceptEdits", "plan", "auto"],
    "assume_mode": "auto",
    "models": ["opus", "sonnet", "haiku"],
}


class FakeInjector:
    def __init__(self):
        self.combos = []
        self.text = []
        self.taps = []

    def combo(self, modifiers, vk):
        self.combos.append((tuple(modifiers), vk))

    def type_text(self, text):
        self.text.append(text)

    def tap(self, vk):
        self.taps.append(vk)


@unittest.skipUnless(sys.platform == "win32", "Windows-only host actions")
class ActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["CLAUDEPAD_STATE_DIR"] = self.tmp.name
        core.ensure_dirs()

    def tearDown(self):
        os.environ.pop("CLAUDEPAD_STATE_DIR", None)
        self.tmp.cleanup()

    def test_reset_from_accept_edits_presses_three_times(self):
        from claudepad_host import actions

        core.write_mode({"session_id": "s1", "permission_mode": "acceptEdits"})
        injector = FakeInjector()
        presses = actions.reset_permissions(injector, CONFIG)

        self.assertEqual(presses, 3)
        self.assertEqual(len(injector.combos), 3)
        state = core.read_active_state()
        self.assertEqual(state["permission_mode"], "default")

    def test_reset_from_auto_presses_once(self):
        from claudepad_host import actions

        core.write_mode({"session_id": "s1", "permission_mode": "auto"})
        injector = FakeInjector()
        presses = actions.reset_permissions(injector, CONFIG)

        self.assertEqual(presses, 1)
        self.assertEqual(len(injector.combos), 1)

    def test_cycle_model_sends_next_alias(self):
        from claudepad_host import actions
        from claudepad_host.winapi import VK_RETURN

        core.write_status(
            {
                "session_id": "s1",
                "model_id": "claude-opus-5-5",
                "model_name": "Opus",
            }
        )
        injector = FakeInjector()
        alias = actions.cycle_model(injector, CONFIG)

        self.assertEqual(alias, "sonnet")
        self.assertEqual(injector.text, ["/model sonnet"])
        self.assertEqual(injector.taps, [VK_RETURN])
        self.assertEqual(core.read_active_state()["model_name"], "sonnet")

    def test_perm_tap_sync_advances_mode(self):
        from claudepad_host.daemon import Daemon

        core.write_mode({"session_id": "s1", "permission_mode": "plan"})
        daemon = Daemon()
        daemon._do_mode_sync()
        self.assertEqual(core.read_active_state()["permission_mode"], "auto")


if __name__ == "__main__":
    unittest.main()

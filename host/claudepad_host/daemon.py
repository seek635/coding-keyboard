"""Background daemon: F15 permission reset, F14 model cycle, F16 mode sync."""

from __future__ import annotations

import logging
import logging.handlers
import sys
import threading

from . import core
from .actions import cycle_model, reset_permissions
from .winapi import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    VK_CONTROL,
    VK_F14,
    VK_F15,
    VK_F16,
    VK_MENU,
    VK_SHIFT,
    Injector,
    acquire_single_instance,
    is_key_down,
    message_loop,
    register_hotkey,
    release_single_instance,
    unregister_hotkey,
)

LOG = logging.getLogger("claudepad")
HOTKEY_RESET = 1
HOTKEY_MODEL = 2
HOTKEY_PERM_TAP = 3
SIGNAL_MODS = MOD_CONTROL | MOD_ALT | MOD_SHIFT


def setup_logging() -> None:
    core.ensure_dirs()
    if LOG.handlers:
        return
    LOG.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(
        str(core.log_path()), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    LOG.addHandler(file_handler)
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        LOG.addHandler(console)


class Daemon:
    def __init__(self) -> None:
        core.ensure_config()
        self.config = core.load_config()
        self.injector = Injector()
        self.stop_event = threading.Event()
        self.action_lock = threading.Lock()
        self.registered: set[int] = set()
        self.fallback: set[str] = set()
        self.mutex: int | None = None

    def _dispatch(self, name: str, func) -> None:
        def runner() -> None:
            if not self.action_lock.acquire(timeout=2):
                LOG.warning("action %s skipped: another action is running", name)
                return
            try:
                LOG.info("action %s", name)
                func()
            except Exception:
                LOG.exception("action %s failed", name)
            finally:
                self.action_lock.release()

        threading.Thread(target=runner, name=f"action-{name}", daemon=True).start()

    def _do_reset(self) -> None:
        reset_permissions(self.injector, self.config)

    def _do_cycle_model(self) -> None:
        cycle_model(self.injector, self.config)

    def _do_mode_sync(self) -> None:
        state = core.read_active_state()
        session_id = state.get("session_id")
        if not session_id:
            LOG.info("PERM tap sync skipped: no active session")
            return
        mode = core.next_permission_mode(state.get("permission_mode"), self.config)
        core.write_mode_override(session_id, mode)
        LOG.info("PERM tap sync: permission mode -> %s", mode)

    def _register_hotkeys(self) -> None:
        if register_hotkey(HOTKEY_RESET, SIGNAL_MODS, VK_F15):
            self.registered.add(HOTKEY_RESET)
        else:
            self.fallback.add("reset")
            LOG.warning("RegisterHotKey Ctrl+Alt+Shift+F15 failed; polling F15 instead")
        if register_hotkey(HOTKEY_MODEL, SIGNAL_MODS, VK_F14):
            self.registered.add(HOTKEY_MODEL)
        else:
            self.fallback.add("model")
            LOG.warning("RegisterHotKey Ctrl+Alt+Shift+F14 failed; polling F14 instead")
        if register_hotkey(HOTKEY_PERM_TAP, 0, VK_F16):
            self.registered.add(HOTKEY_PERM_TAP)
        else:
            LOG.warning("RegisterHotKey F16 failed; permission mode sync is hook-only")

    def _on_hotkey(self, hotkey_id: int) -> None:
        if hotkey_id == HOTKEY_RESET:
            self._dispatch("permission-reset", self._do_reset)
        elif hotkey_id == HOTKEY_MODEL:
            self._dispatch("model-cycle", self._do_cycle_model)
        elif hotkey_id == HOTKEY_PERM_TAP:
            self._dispatch("perm-tap-sync", self._do_mode_sync)

    def _fallback_loop(self) -> None:
        if not self.fallback:
            return
        prev_f14 = is_key_down(VK_F14)
        prev_f15 = is_key_down(VK_F15)
        while not self.stop_event.is_set():
            mods = is_key_down(VK_CONTROL) and is_key_down(VK_MENU) and is_key_down(VK_SHIFT)
            f14 = is_key_down(VK_F14)
            f15 = is_key_down(VK_F15)
            if "reset" in self.fallback and mods and f15 and not prev_f15:
                self._dispatch("permission-reset-fallback", self._do_reset)
            if "model" in self.fallback and mods and f14 and not prev_f14:
                self._dispatch("model-cycle-fallback", self._do_cycle_model)
            prev_f14, prev_f15 = f14, f15
            self.stop_event.wait(0.04)

    def run(self) -> int:
        setup_logging()
        self.mutex = acquire_single_instance()
        if self.mutex is None:
            LOG.error("another ClaudePad host is already running")
            return 1

        self._register_hotkeys()
        if self.fallback:
            threading.Thread(target=self._fallback_loop, name="fallback-poll", daemon=True).start()
        LOG.info("ClaudePad host running (reset F15, model F14, sync F16)")

        try:
            message_loop(self._on_hotkey, self.stop_event)
        except KeyboardInterrupt:
            LOG.info("interrupted")
        finally:
            self.stop_event.set()
            for hotkey_id in self.registered:
                unregister_hotkey(hotkey_id)
            release_single_instance(self.mutex)
            LOG.info("ClaudePad host stopped")
        return 0


def run() -> int:
    return Daemon().run()

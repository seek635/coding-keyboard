"""High-level actions triggered by the hardware signals."""

from __future__ import annotations

import logging
import time

from . import core
from .winapi import VK_RETURN, VK_SHIFT, VK_TAB, Injector, foreground_title

log = logging.getLogger("claudepad.actions")


def reset_permissions(injector: Injector, config: dict) -> int:
    """Press Shift+Tab until Claude Code's cycle reaches default."""
    state = core.read_active_state()
    mode = core.resolve_mode(state.get("permission_mode"), config)
    presses = core.presses_to_default(mode, config.get("permission_cycle", core.DEFAULT_CYCLE))

    log.info(
        "permission reset: %s -> default (%d press(es)), foreground=%r",
        mode,
        presses,
        foreground_title(),
    )
    for _ in range(presses):
        injector.combo([VK_SHIFT], VK_TAB)
        time.sleep(0.08)

    if state.get("session_id"):
        core.write_mode_override(state["session_id"], "default")
    return presses


def cycle_model(injector: Injector, config: dict) -> str:
    """Send /model <next-alias> + Enter and optimistically update state."""
    state = core.read_active_state()
    alias = core.next_model(
        state.get("model_id"),
        state.get("model_name"),
        config.get("models", core.DEFAULT_MODELS),
    )
    if not alias:
        log.warning("model cycle skipped: no models configured")
        return ""

    log.info(
        "model cycle: %r -> %s, foreground=%r",
        state.get("model_name") or state.get("model_id"),
        alias,
        foreground_title(),
    )
    injector.type_text(f"/model {alias}")
    time.sleep(0.05)
    injector.tap(VK_RETURN)

    if state.get("session_id"):
        core.write_model_override(state["session_id"], alias)
    return alias

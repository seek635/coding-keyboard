#!/usr/bin/env python3
"""Static checks for the ClaudePad shield, keymap and build files.

Pure Python; does not need Zephyr or OpenSCAD. This cannot replace a real
firmware build, but it catches position/order drift during edits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHIELD = ROOT / "config" / "boards" / "shields" / "claudepad"
OVERLAY = SHIELD / "claudepad.overlay"
KEYMAP = SHIELD / "claudepad.keymap"

EXPECTED_RC = [
    (0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
    (1, 0), (1, 2), (1, 3), (1, 4),
    (2, 0), (2, 2),
]
EXPECTED_BINDINGS = [
    "perm_ht", "model_ht", "cmd_ht", "kp", "voice_td", "stop_td",
    "kp", "kp", "kp", "enter_td", "space_ht",
]
BUILTIN_BEHAVIORS = {
    "kp", "kt", "mo", "to", "tog", "trans", "none", "mt", "lt", "sk", "sl",
    "bt", "out", "bootloader", "reset", "studio_unlock",
    "macro_tap", "macro_press", "macro_release", "macro_wait_time",
    "macro_tap_time", "macro_pause_for_release", "macro_param_1to1",
    "macro_param_1to2", "macro_param_2to1", "macro_param_2to2",
}


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    overlay = OVERLAY.read_text(encoding="utf-8")
    keymap = KEYMAP.read_text(encoding="utf-8")

    rc_values = [tuple(map(int, pair)) for pair in re.findall(r"RC\((\d+),\s*(\d+)\)", overlay)]
    check(rc_values == EXPECTED_RC, f"matrix transform order mismatch: {rc_values}", errors)
    check(len(set(rc_values)) == 11, "matrix transform must use 11 unique intersections", errors)

    keys_block = re.search(r"keys\s*=\s*<(.*?)>;", overlay, re.S)
    check(keys_block is not None, "physical layout keys block missing", errors)
    if keys_block:
        attrs = re.findall(
            r"&key_physical_attrs\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", keys_block.group(1)
        )
        parsed = [tuple(map(int, item)) for item in attrs]
        check(len(parsed) == 11, f"physical layout must have 11 keys, got {len(parsed)}", errors)
        rows = {}
        for width, height, x, y in parsed:
            rows.setdefault(y, []).append((width, x))
        check(sorted(rows.get(0, [])) == sorted([(100, x) for x in (0, 100, 200, 300, 400)]),
              "top row must have five 1u keys", errors)
        check(sorted(rows.get(94, [])) == sorted(
            [(100, 0), (100, 200), (100, 300), (100, 400)]
        ), "middle row must have STOP, LEFT, DOWN, RIGHT", errors)
        check(sorted(rows.get(188, [])) == sorted([(200, 0), (300, 200)]),
              "bottom row must be a 2u ENTER and a 3u SPACE", errors)

    for pin in ("0", "1", "2"):
        check(f"&xiao_d {pin} " in overlay, f"missing row pin D{pin}", errors)
    for pin in ("6", "7", "8", "9", "10"):
        check(f"&xiao_d {pin} " in overlay, f"missing column pin D{pin}", errors)

    layer = re.search(r"default_layer\s*\{(.*?)\n\s*\};", keymap, re.S)
    check(layer is not None, "default_layer block missing", errors)
    if layer:
        actual = re.findall(r"&([A-Za-z_][A-Za-z0-9_]*)", layer.group(1))
        check(actual == EXPECTED_BINDINGS, f"keymap order mismatch: {actual}", errors)

    definitions = set(re.findall(r"^\s*([a-z_][a-z0-9_]*)\s*:\s*[a-z_][\w-]*\s*\{", keymap, re.M))
    references = set(re.findall(r"&([A-Za-z_][A-Za-z0-9_]*)", keymap))
    missing = sorted(references - definitions - BUILTIN_BEHAVIORS)
    check(not missing, f"undefined behavior references: {missing}", errors)

    for signal in ("LC(LA(LS(F15)))", "LC(LA(LS(F14)))", "&kp F16"):
        check(signal in keymap, f"missing signal binding: {signal}", errors)
    check("&mac_perm_cycle" in keymap, "PERM sync macro is not referenced", errors)
    check("&kp F13" not in keymap, "approval toggle F13 should be removed", errors)

    build = (ROOT / "build.yaml").read_text(encoding="utf-8")
    check("xiao_ble" in build and "claudepad" in build, "build.yaml target mismatch", errors)
    west = (ROOT / "config" / "west.yml").read_text(encoding="utf-8")
    check("zmkfirmware" in west and "import: app/west.yml" in west, "west.yml manifest mismatch", errors)
    for name in ("Kconfig.shield", "Kconfig.defconfig", "claudepad.conf"):
        check((SHIELD / name).exists(), f"missing {name}", errors)

    if errors:
        print("FAIL")
        for error in errors:
            print("  -", error)
        return 1
    print("OK: 11 intersections, 11 keys, 11 bindings, pins and signals match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

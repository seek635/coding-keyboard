#!/usr/bin/env python3
"""Check that the PCB generator and the OpenSCAD case use the same layout."""

from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAD = (ROOT / "cad" / "params.scad").read_text(encoding="utf-8")
PCB_PY = ROOT / "pcb" / "generate_pcb.py"


def scad_numbers(name: str) -> list[float]:
    match = re.search(rf"^{name}\s*=\s*\[([^\]]+)\];", SCAD, re.M)
    if not match:
        raise ValueError(f"missing SCAD array {name}")
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]


def scad_pairs(name: str) -> list[tuple[float, float]]:
    match = re.search(rf"^{name}\s*=\s*\[(.*?)\n\];", SCAD, re.M | re.S)
    if not match:
        raise ValueError(f"missing SCAD array {name}")
    return [(float(a), float(b)) for a, b in re.findall(r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]", match.group(1))]


def scad_keycaps() -> list[tuple[float, float, int, str]]:
    match = re.search(r"^KEYCAPS\s*=\s*\[(.*?)\n\];", SCAD, re.M | re.S)
    if not match:
        raise ValueError("missing KEYCAPS")
    return [
        (float(cx), float(cy), int(u), label)
        for cx, cy, u, label in re.findall(
            r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(\d+)\s*,\s*\"([^\"]+)\"\s*\]",
            match.group(1),
        )
    ]


def scad_scalar(name: str) -> float:
    match = re.search(rf"^{name}\s*=\s*(-?\d+(?:\.\d+)?)\s*;", SCAD, re.M)
    if not match:
        raise ValueError(f"missing SCAD scalar {name}")
    return float(match.group(1))


def load_pcb_module():
    # generate_pcb imports pcbnew only for constants/classes at import time.
    stub = types.SimpleNamespace(F_Cu=0, In1_Cu=1, In2_Cu=2, B_Cu=3,
                                  F_SilkS=4, B_SilkS=5, F_Fab=6, B_Fab=7,
                                  Edge_Cuts=8)
    sys.modules["pcbnew"] = stub
    spec = importlib.util.spec_from_file_location("claudepad_pcb_gen", PCB_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    errors = []
    gen = load_pcb_module()

    if (gen.BOARD_X0, gen.BOARD_Y0) != (scad_scalar("PCB_X0"), scad_scalar("PCB_Y0")):
        errors.append("PCB origin mismatch")
    if (gen.BOARD_X1 - gen.BOARD_X0, gen.BOARD_Y1 - gen.BOARD_Y0) != (
        scad_scalar("PCB_W"), scad_scalar("PCB_D")
    ):
        errors.append("PCB size mismatch")

    pcb_switches = {(round(k[1], 3), round(k[2], 3)) for k in gen.KEYS}
    scad_switches = {(round(x, 3), round(y, 3)) for x, y in scad_pairs("SWITCHES")}
    if pcb_switches != scad_switches:
        errors.append(f"switch positions differ: PCB={sorted(pcb_switches)} CAD={sorted(scad_switches)}")

    # Derive keycap centers from PCB groups
    groups: dict[str, list[tuple[float, float]]] = {}
    for name, x, y, row, col, group, has_diode in gen.KEYS:
        groups.setdefault(group, []).append((x, y))
    pcb_caps = set()
    for group, positions in groups.items():
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        label = "ENTER" if group == "ENTER" else "SPACE" if group == "SPACE" else group
        if group in ("ENTER", "SPACE"):
            pcb_caps.add((round(sum(xs) / len(xs), 3), round(ys[0], 3), len(positions), label))
        else:
            pcb_caps.add((round(xs[0], 3), round(ys[0], 3), 1, label))

    cad_caps = {(round(cx, 3), round(cy, 3), u, label) for cx, cy, u, label in scad_keycaps()}
    if pcb_caps != cad_caps:
        errors.append(f"keycaps differ: PCB={sorted(pcb_caps)} CAD={sorted(cad_caps)}")

    if (gen.XIAO_X, gen.XIAO_Y) != (scad_scalar("XIAO_X"), scad_scalar("XIAO_Y")):
        errors.append("XIAO position mismatch")

    case_w = scad_scalar("CASE_W")
    case_d = scad_scalar("CASE_D")
    if case_w <= scad_scalar("PCB_X0") + scad_scalar("PCB_W"):
        errors.append("case is narrower than the PCB")
    if case_d <= scad_scalar("PCB_Y0") + scad_scalar("PCB_D"):
        errors.append("case is shallower than the PCB")

    if errors:
        print("FAIL")
        for error in errors:
            print("  -", error)
        return 1
    print("OK: PCB and CAD key positions, keycaps, XIAO and board dimensions match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

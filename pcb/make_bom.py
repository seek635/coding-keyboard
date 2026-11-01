#!/usr/bin/env python3
"""Write the PCB-only BOM from claudepad.kicad_pcb.

Run with KiCad's bundled Python:
  D:/kicad/bin/python.exe pcb/make_bom.py
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
BOARD = ROOT / "claudepad.kicad_pcb"
OUT = ROOT / "output" / "claudepad-bom.csv"

# BAT1 is a pair of bare solder pads, not a purchased component.
EXCLUDE = {"BAT1"}


def natural_key(ref: str) -> tuple[str, int]:
    match = re.match(r"([A-Za-z]+)(\d+)", ref)
    return (match.group(1), int(match.group(2))) if match else (ref, 0)


def main() -> int:
    board = pcbnew.LoadBoard(str(BOARD))
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in EXCLUDE:
            continue
        groups[(fp.GetValue(), fp.GetFPIDAsString())].append(ref)

    rows = []
    for (value, footprint), refs in groups.items():
        refs.sort(key=natural_key)
        rows.append(
            {
                "References": " ".join(refs),
                "Value": value,
                "Footprint": footprint,
                "Quantity": len(refs),
            }
        )
    rows.sort(key=lambda row: natural_key(row["References"].split()[0]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["References", "Value", "Footprint", "Quantity"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {OUT} ({len(rows)} line items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

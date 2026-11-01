#!/usr/bin/env python3
"""Strip decorative silk/courtyard graphics that DRC flags on this board.

Run once after copying the footprints:
  python pcb/clean_footprints.py
"""

from __future__ import annotations

from pathlib import Path

LIB = Path(__file__).resolve().parent / "footprints" / "ClaudePad.pretty"


def remove_balanced_blocks(text: str, starter: str, must_contain: str | None = None) -> str:
    pos = 0
    out = []
    while True:
        idx = text.find(starter, pos)
        if idx < 0:
            out.append(text[pos:])
            break
        depth = 0
        i = idx
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        block = text[idx:i]
        if must_contain is None or must_contain in block:
            out.append(text[pos:idx])
        else:
            out.append(text[pos:i])
        pos = i
    return "".join(out)


def clean_switch(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    for starter in ('(fp_line', '(fp_arc', '(fp_circle', '(fp_rect'):
        s = remove_balanced_blocks(s, starter, "F.SilkS")
        s = remove_balanced_blocks(s, starter, "F.CrtYd")
    s = remove_balanced_blocks(s, '(fp_text reference')
    s = remove_balanced_blocks(s, '(fp_text value')
    path.write_text(s, encoding="utf-8")


def clean_diode(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    for starter in ('(fp_line', '(fp_arc', '(fp_circle', '(fp_rect'):
        s = remove_balanced_blocks(s, starter, "B.SilkS")
        s = remove_balanced_blocks(s, starter, "B.CrtYd")
    s = remove_balanced_blocks(s, '(fp_text reference')
    s = remove_balanced_blocks(s, '(fp_text value')
    path.write_text(s, encoding="utf-8")


def clean_xiao(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    for starter in ('(fp_line', '(fp_arc', '(fp_circle', '(fp_rect'):
        s = remove_balanced_blocks(s, starter, "F.SilkS")
        s = remove_balanced_blocks(s, starter, "F.CrtYd")
    for prop in ("Reference", "Value"):
        s = remove_balanced_blocks(s, f'(property "{prop}"')
    s = remove_balanced_blocks(s, '(fp_text reference')
    s = remove_balanced_blocks(s, '(fp_text value')
    path.write_text(s, encoding="utf-8")


def clean_jst(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    for starter in ('(fp_line', '(fp_arc', '(fp_circle', '(fp_rect'):
        s = remove_balanced_blocks(s, starter, "F.SilkS")
    for starter in ('(fp_text reference', '(fp_text value', '(fp_text user'):
        s = remove_balanced_blocks(s, starter)
    path.write_text(s, encoding="utf-8")


def clean_bat(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    for starter in ('(fp_line', '(fp_arc', '(fp_circle', '(fp_rect'):
        s = remove_balanced_blocks(s, starter, "B.SilkS")
    for starter in ('(fp_text reference', '(fp_text value', '(fp_text user'):
        s = remove_balanced_blocks(s, starter)
    path.write_text(s, encoding="utf-8")


def main() -> int:
    clean_switch(LIB / "SW_Kailh_Choc_V2_1.00u.kicad_mod")
    clean_diode(LIB / "D_1N4148_DO35.kicad_mod")
    clean_xiao(LIB / "XIAO-nRF52840-SMD-ClaudePad.kicad_mod")
    clean_jst(LIB / "JST_PH_2.00mm_THT.kicad_mod")
    clean_bat(LIB / "BAT_WIRE_PADS.kicad_mod")
    print("cleaned silk/courtyard graphics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the self-contained ClaudePad PCB design package."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "claudepad-pcb-design.zip"

FILES = [
    (ROOT / "PACKAGE-README.md", "README.md"),
    (ROOT / "claudepad.kicad_pro", "claudepad.kicad_pro"),
    (ROOT / "claudepad.kicad_pcb", "claudepad.kicad_pcb"),
    (ROOT / "claudepad.kicad_dru", "claudepad.kicad_dru"),
    (ROOT / "generate_pcb.py", "generate_pcb.py"),
    (ROOT / "make_bom.py", "make_bom.py"),
    (ROOT / "clean_footprints.py", "clean_footprints.py"),
    (ROOT.parent / "docs" / "pcb.md", "PCB-GUIDE.md"),
    (ROOT / "output" / "claudepad-gerbers.zip", "output/claudepad-gerbers.zip"),
    (ROOT / "output" / "claudepad-jlcpcb-gerbers.zip", "output/claudepad-jlcpcb-gerbers.zip"),
    (ROOT / "output" / "claudepad-pos.csv", "output/claudepad-pos.csv"),
    (ROOT / "output" / "claudepad-bom.csv", "output/claudepad-bom.csv"),
    (ROOT / "output" / "drc.rpt", "output/drc.rpt"),
    (ROOT / "output" / "claudepad-stats.txt", "output/claudepad-stats.txt"),
    (ROOT / "output" / "3d" / "claudepad-pcb.step", "output/3d/claudepad-pcb.step"),
    (ROOT / "output" / "3d" / "claudepad-pcb-3d.pdf", "output/3d/claudepad-pcb-3d.pdf"),
]

DIRS = [
    (ROOT / "footprints", "footprints"),
    (ROOT / "output" / "gerbers", "output/gerbers"),
    (ROOT / "output" / "preview", "output/preview"),
]


def main() -> int:
    missing = [str(src) for src, _ in FILES if not src.exists()]
    for src, _ in DIRS:
        if not src.is_dir():
            missing.append(str(src))
    if missing:
        print("missing inputs:")
        for path in missing:
            print("  -", path)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for src, arcname in FILES:
            archive.write(src, arcname)
            count += 1
        for directory, prefix in DIRS:
            for src in sorted(directory.rglob("*")):
                if src.is_file():
                    archive.write(src, f"{prefix}/{src.relative_to(directory).as_posix()}")
                    count += 1

    print(f"wrote {OUT} ({count} files, {OUT.stat().st_size / 1024 / 1024:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

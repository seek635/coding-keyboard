# -*- coding: utf-8 -*-
"""从板文件导出 Specctra DSN（给 FreeRouting 自动布线用）
运行：D:\\kicad\\bin\\python.exe tools\\export_dsn.py
"""
import os
import sys

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "pcb", "claudepad.kicad_pcb")
OUTDIR = os.environ.get("FR_DIR") or os.path.join(
    os.environ.get("TEMP", ROOT), "kicad_install")
DSN = os.path.join(OUTDIR, "claudepad.dsn")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    board = pcbnew.LoadBoard(BOARD)
    ok = pcbnew.ExportSpecctraDSN(board, DSN)
    # KiCad 的返回值有的版本是 None，以文件是否生成 + 非空为准
    exists = os.path.exists(DSN) and os.path.getsize(DSN) > 1000
    print(f"{'✅' if exists else '❌'} ExportSpecctraDSN -> {DSN}"
          f"（返回 {ok}，{os.path.getsize(DSN) if os.path.exists(DSN) else 0} bytes）")
    if not exists:
        return 1
    with open(DSN, encoding="utf-8", errors="replace") as f:
        head = f.read(400)
    print(head.split("\n")[1][:120] if "\n" in head else head[:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())

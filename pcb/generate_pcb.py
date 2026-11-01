#!/usr/bin/env python3
"""Generate the ClaudePad PCB with KiCad's pcbnew API.

Run with KiCad's bundled Python:
  D:/kicad/bin/python.exe pcb/generate_pcb.py

WARNING: the routing below still targets the ORIGINAL 4-layer stack, with
ROW0/ROW1 on In1.Cu and ROW2 on In2.Cu.  The shipped board -- the checked-in
pcb/claudepad.kicad_pcb and the 2026-10-27 Gerbers in pcb/output/gerbers/ --
is the 2-layer revision, which routes the row buses on B.Cu.  Running this
script overwrites claudepad.kicad_pcb with the old 4-layer design, so port
the row buses to B.Cu (and drop In1.Cu/In2.Cu) before regenerating.

Legacy 4-layer stack:
  F.Cu  : columns + XIAO pad fan-out
  In1.Cu: ROW0 / ROW1
  In2.Cu: ROW2
  B.Cu  : switch-to-diode links, parallel groups, battery traces

2-layer shipped stack:
  F.Cu  : columns + XIAO pad fan-out
  B.Cu  : ROW0/ROW1/ROW2 row buses, switch-to-diode links, parallel groups,
          battery traces
"""

from __future__ import annotations

import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "footprints" / "ClaudePad.pretty"
OUT = ROOT / "claudepad.kicad_pcb"

# Board / mechanical layout (mm, absolute coordinates)
BOARD_X0, BOARD_Y0, BOARD_X1, BOARD_Y1 = 9.0, 3.0, 99.0, 79.0
KEY_X = [18.0, 36.0, 54.0, 72.0, 90.0]
KEY_Y = [30.5, 47.5, 64.5]
XIAO_X, XIAO_Y = 54.0, 12.0
JST_X, JST_Y = 74.0, 12.0
BAT_X, BAT_Y = 70.0, 17.5
CABLE_SLOT = (83.5, 10.0, 87.5, 18.0)

F = pcbnew.F_Cu
IN1 = pcbnew.In1_Cu
IN2 = pcbnew.In2_Cu
B = pcbnew.B_Cu

# Human-readable part values for the PCB BOM.
VALUES = {
    "SW_Kailh_Choc_V2_1.00u": "Kailh Choc V2 1u",
    "D_1N4148_DO35": "1N4148 DO-35",
    "XIAO-nRF52840-THT-ClaudePad": "Seeed XIAO nRF52840 (THT headers)",
    "JST_PH_2.00mm_THT": "JST-PH 2.0 2P",
    "BAT_WIRE_PADS": "PCB solder pads",
}

# key name, x, y, row, col, group, has_diode
KEYS = [
    ("PERM",  KEY_X[0], KEY_Y[0], 0, 0, "PERM",  True),
    ("MODEL", KEY_X[1], KEY_Y[0], 0, 1, "MODEL", True),
    ("CMD",   KEY_X[2], KEY_Y[0], 0, 2, "CMD",   True),
    ("UP",    KEY_X[3], KEY_Y[0], 0, 3, "UP",    True),
    ("VOICE", KEY_X[4], KEY_Y[0], 0, 4, "VOICE", True),
    ("STOP",  KEY_X[0], KEY_Y[1], 1, 0, "STOP",  True),
    ("LEFT",  KEY_X[2], KEY_Y[1], 1, 2, "LEFT",  True),
    ("DOWN",  KEY_X[3], KEY_Y[1], 1, 3, "DOWN",  True),
    ("RIGHT", KEY_X[4], KEY_Y[1], 1, 4, "RIGHT", True),
    ("ENTER_A", KEY_X[0], KEY_Y[2], 2, 0, "ENTER", True),
    ("ENTER_B", KEY_X[1], KEY_Y[2], 2, 0, "ENTER", False),
    ("SPACE_A", KEY_X[2], KEY_Y[2], 2, 2, "SPACE", False),
    ("SPACE_B", KEY_X[3], KEY_Y[2], 2, 2, "SPACE", True),
    ("SPACE_C", KEY_X[4], KEY_Y[2], 2, 2, "SPACE", False),
]

# Diodes sit in the open bands between switch rows, clear of the Choc V2
# centre posts and side pegs.  ref, x, y, group, row, rotation
DIODES = [
    ("D1",  18.0, 38.5, "PERM",  0, 0),
    ("D2",  36.0, 38.5, "MODEL", 0, 0),
    ("D3",  54.0, 38.5, "CMD",   0, 0),
    ("D4",  72.0, 38.5, "UP",    0, 0),
    ("D5",  90.0, 38.5, "VOICE", 0, 0),
    ("D6",  18.0, 55.5, "STOP",  1, 0),
    ("D7",  54.0, 55.5, "LEFT",  1, 0),
    ("D8",  72.0, 55.5, "DOWN",  1, 0),
    ("D9",  90.0, 55.5, "RIGHT", 1, 0),
    ("D10", 27.0, 74.5, "ENTER", 2, 180),
    ("D11", 63.0, 74.5, "SPACE", 2, 180),
]


class Builder:
    def __init__(self) -> None:
        self.board = pcbnew.BOARD()
        self.board.SetCopperLayerCount(4)
        self.board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.6))
        title = self.board.GetTitleBlock()
        title.SetTitle("ClaudePad")
        title.SetRevision("v1.0")
        title.SetDate("2026-10-26")
        title.SetCompany("ClaudePad")
        title.SetComment(0, "11-key ZMK macropad for Claude Code")
        self.nets: dict[str, pcbnew.NETINFO_ITEM] = {}

    def net(self, name: str) -> pcbnew.NETINFO_ITEM:
        if name not in self.nets:
            item = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(item)
            self.nets[name] = item
        return self.nets[name]

    def add_outline_rect(self, x0: float, y0: float, x1: float, y1: float) -> None:
        shape = pcbnew.PCB_SHAPE(self.board)
        shape.SetShape(pcbnew.SHAPE_T_RECT)
        shape.SetStart(pcbnew.VECTOR2I_MM(x0, y0))
        shape.SetEnd(pcbnew.VECTOR2I_MM(x1, y1))
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(pcbnew.FromMM(0.1))
        self.board.Add(shape)

    def text(self, text: str, x: float, y: float, layer: int = pcbnew.F_SilkS,
             size: float = 1.0, angle: float = 0.0) -> None:
        item = pcbnew.PCB_TEXT(self.board)
        item.SetText(text)
        item.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        item.SetLayer(layer)
        item.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
        item.SetTextThickness(pcbnew.FromMM(0.15))
        item.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
        if layer == pcbnew.B_SilkS:
            item.SetMirrored(True)
        self.board.Add(item)

    def line(self, x0: float, y0: float, x1: float, y1: float, layer: int,
             width: float = 0.15) -> None:
        shape = pcbnew.PCB_SHAPE(self.board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetStart(pcbnew.VECTOR2I_MM(x0, y0))
        shape.SetEnd(pcbnew.VECTOR2I_MM(x1, y1))
        shape.SetLayer(layer)
        shape.SetWidth(pcbnew.FromMM(width))
        self.board.Add(shape)

    def footprint(self, name: str, ref: str, x: float, y: float,
                  netmap: dict[str, str] | None = None,
                  angle: float = 0.0) -> pcbnew.FOOTPRINT:
        fp = pcbnew.FootprintLoad(str(LIB), name)
        if fp is None:
            raise RuntimeError(f"cannot load footprint {name}")
        fp.SetReference(ref)
        fp.SetValue(VALUES.get(name, name))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        if angle:
            fp.SetOrientation(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
        self.board.Add(fp)
        if netmap:
            for pad in fp.Pads():
                number = pad.GetNumber()
                if number in netmap:
                    pad.SetNet(self.net(netmap[number]))
        return fp

    def track(self, x0: float, y0: float, x1: float, y1: float, layer: int,
              width: float = 0.25, net: str | None = None) -> None:
        track = pcbnew.PCB_TRACK(self.board)
        track.SetStart(pcbnew.VECTOR2I_MM(x0, y0))
        track.SetEnd(pcbnew.VECTOR2I_MM(x1, y1))
        track.SetWidth(pcbnew.FromMM(width))
        track.SetLayer(layer)
        if net:
            track.SetNet(self.net(net))
        self.board.Add(track)

    def polyline(self, points: list[tuple[float, float]], layer: int,
                 width: float = 0.25, net: str | None = None) -> None:
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            self.track(x0, y0, x1, y1, layer, width, net)

    def via(self, x: float, y: float, top: int = F, bottom: int = IN1,
            diameter: float = 0.6, drill: float = 0.3, net: str | None = None) -> None:
        via = pcbnew.PCB_VIA(self.board)
        via.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        via.SetWidth(pcbnew.FromMM(diameter))
        via.SetDrill(pcbnew.FromMM(drill))
        via.SetLayerPair(top, bottom)
        if net:
            via.SetNet(self.net(net))
        self.board.Add(via)

    def save(self, path: Path) -> None:
        pcbnew.SaveBoard(str(path), self.board)


def main() -> int:
    b = Builder()

    # ---- board outline and cutouts -----------------------------------------
    b.add_outline_rect(BOARD_X0, BOARD_Y0, BOARD_X1, BOARD_Y1)
    b.add_outline_rect(*CABLE_SLOT)

    # ---- footprints ---------------------------------------------------------
    for index, (name, x, y, row, col, group, has_diode) in enumerate(KEYS, start=1):
        switch_nets = {"1": f"ANODE_{group}", "2": f"COL{col}"}
        b.footprint("SW_Kailh_Choc_V2_1.00u", f"SW{index}", x, y, switch_nets)
        b.text(name, x, y + 8.6, pcbnew.F_SilkS, 1.0)
        # switch pin 1 is at (x, y-5.9); mark the pin-1 side
        b.line(x - 2.6, y - 7.1, x - 1.4, y - 7.1, pcbnew.F_SilkS, 0.2)

    for ref, x, y, group, row, angle in DIODES:
        b.footprint(
            "D_1N4148_DO35",
            ref,
            x,
            y,
            {"1": f"ANODE_{group}", "2": f"ROW{row}"},
            angle,
        )

    b.footprint(
        "XIAO-nRF52840-THT-ClaudePad",
        "U1",
        XIAO_X,
        XIAO_Y,
        {
            "1": "ROW0",
            "2": "ROW1",
            "3": "ROW2",
            "7": "COL0",
            "8": "COL1",
            "9": "COL2",
            "10": "COL3",
            "11": "COL4",
        },
    )
    b.footprint("JST_PH_2.00mm_THT", "J1", JST_X, JST_Y, {"1": "BAT+", "2": "BAT-"})
    b.footprint("BAT_WIRE_PADS", "BAT1", BAT_X, BAT_Y, {"1": "BAT+", "2": "BAT-"})

    # ---- F.Cu: columns and XIAO fan-out ------------------------------------
    b.polyline([(46.38, 19.62), (23.0, 19.62), (23.0, 60.7), (41.0, 60.7)],
               F, net="COL0")
    b.polyline([(61.62, 19.62), (65.5, 19.62), (65.5, 23.0), (41.0, 23.0),
                (41.0, 26.7)], F, net="COL1")
    b.polyline([(61.62, 17.08), (66.5, 17.08), (66.5, 24.0), (59.0, 24.0),
                (59.0, 60.7)], F, net="COL2")
    b.polyline([(59.0, 57.0), (95.0, 57.0)], F, net="COL2")
    b.track(77.0, 57.0, 77.0, 60.7, F, net="COL2")
    b.track(95.0, 57.0, 95.0, 60.7, F, net="COL2")
    b.polyline([(61.62, 14.54), (77.0, 14.54), (77.0, 43.7)], F, net="COL3")
    b.polyline([(61.62, 12.0), (67.5, 12.0), (67.5, 8.0), (95.0, 8.0),
                (95.0, 43.7)], F, net="COL4")

    # XIAO row pads to vias (vias kept away from the board edge)
    b.polyline([(46.38, 4.38), (39.0, 4.38), (39.0, 6.0)], F, net="ROW0")
    b.track(46.38, 6.92, 42.0, 6.92, F, net="ROW1")
    b.track(46.38, 9.46, 40.5, 9.46, F, net="ROW2")

    # ---- In1.Cu: ROW0 and ROW1 ---------------------------------------------
    b.polyline([(39.0, 6.0), (39.0, 33.6)], IN1, net="ROW0")
    b.track(21.5, 33.6, 93.5, 33.6, IN1, net="ROW0")

    b.polyline([(42.0, 6.92), (42.0, 4.0), (10.5, 4.0), (10.5, 50.6),
                (21.5, 50.6)], IN1, net="ROW1")
    b.track(21.5, 50.6, 93.5, 50.6, IN1, net="ROW1")

    # ---- In2.Cu: ROW2 -------------------------------------------------------
    b.polyline([(40.5, 9.46), (40.5, 21.5), (97.4, 21.5), (97.4, 67.6),
                (59.5, 67.6)], IN2, net="ROW2")
    b.track(23.5, 67.6, 59.5, 67.6, IN2, net="ROW2")

    # ---- diode cathodes: short stub up to the row bus ----------------------
    for ref, x, y, group, row, angle in DIODES:
        cath_x = x - 3.5 if angle else x + 3.5
        layer = IN1 if row < 2 else IN2
        bus_y = 33.6 if row == 0 else (50.6 if row == 1 else 67.6)
        b.track(cath_x, y, cath_x, bus_y, layer, net=f"ROW{row}")

    # ---- vias ---------------------------------------------------------------
    b.via(39.0, 6.0, F, IN1, net="ROW0")
    b.via(42.0, 6.92, F, IN1, net="ROW1")
    b.via(40.5, 9.46, F, IN2, net="ROW2")

    # ---- B.Cu: switch-to-diode anode routes --------------------------------
    # Row 0/1: wrap around the left side of the switch (the right side is
    # occupied by pin 2), then down into the open diode band.
    for ref, x, y, group, row, angle in DIODES:
        if row < 2:
            sy = y - 8.0
            b.polyline(
                [(x, sy - 5.9), (x - 6.9, sy - 5.2), (x - 6.9, sy + 7.0),
                 (x - 3.5, y)],
                B, net=f"ANODE_{group}",
            )
    # parallel groups: ENTER and SPACE share one diode each
    b.track(18.0, 58.6, 36.0, 58.6, B, net="ANODE_ENTER")
    b.track(54.0, 58.6, 90.0, 58.6, B, net="ANODE_SPACE")
    b.polyline([(27.0, 58.6), (27.0, 73.0), (30.5, 74.5)], B, net="ANODE_ENTER")
    b.polyline([(63.0, 58.6), (63.0, 73.0), (66.5, 74.5)], B, net="ANODE_SPACE")

    # ---- B.Cu: battery traces ----------------------------------------------
    b.polyline([(74.0, 12.0), (70.0, 12.0), (70.0, 17.5)],
               B, 0.5, net="BAT+")
    b.polyline([(76.0, 12.0), (76.0, 19.5), (70.0, 19.5)],
               B, 0.5, net="BAT-")

    # ---- silkscreen ---------------------------------------------------------
    for x, label in zip(KEY_X, ["C0", "C1", "C2", "C3", "C4"]):
        b.text(label, x, 76.3, pcbnew.F_SilkS, 0.9)
    for y, label in zip(KEY_Y, ["R0", "R1", "R2"]):
        b.text(label, 11.2, y, pcbnew.F_SilkS, 0.9)
    b.text("ClaudePad PCB v1  2026-10-25", 44.0, 76.3, pcbnew.F_Fab, 1.1)
    b.text("4L 1.6mm", 84.5, 76.3, pcbnew.F_Fab, 0.8)
    b.text("USB-C / RESET", 54.0, 5.1, pcbnew.F_Fab, 0.8)
    b.text("BAT+", 66.0, 17.5, pcbnew.B_SilkS, 0.8)
    b.text("BAT-", 66.0, 19.5, pcbnew.B_SilkS, 0.8)
    b.text("JST +", 71.5, 8.6, pcbnew.F_Fab, 0.8)
    b.text("JST -", 71.5, 15.2, pcbnew.F_Fab, 0.8)
    b.text("cable slot", 85.5, 19.2, pcbnew.F_Fab, 0.8)
    b.text("1", 43.6, 4.0, pcbnew.F_SilkS, 0.8)
    b.text("+ JST", 70.2, 10.2, pcbnew.F_SilkS, 0.8)
    b.text("- JST", 70.2, 13.8, pcbnew.F_SilkS, 0.8)

    b.save(OUT)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""补一条自动布线没走完的走线（ROW3：SW13.pad2 ↔ SW14.pad2）。
绕开两个 Ø5 中心孔（(49,43) 与 (67,43)），走 B.Cu。
坐标用文档坐标系（y 向上），写入时转 KiCad（y_k = 板高 − y_doc）。
运行：D:\\kicad\\bin\\python.exe tools\\patch_route.py
"""
import os
import sys

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "pcb", "claudepad.kicad_pcb")
H = 50.0
NET = "ROW3"
WIDTH = 0.25

# 文档坐标折线：从 SW13.pad2 出来，向下绕开中心孔，横穿到 SW14.pad2
PATH_DOC = [(43.10, 43.00), (43.10, 39.50), (72.90, 39.50), (72.90, 43.00)]
LAYER = pcbnew.B_Cu


def main():
    board = pcbnew.LoadBoard(BOARD)
    net = None
    for ni in board.GetNetsByNetcode().values():
        if ni.GetNetname() == NET:
            net = ni
            break
    if net is None:
        print(f"❌ 板上没有网络 {NET}")
        return 1

    n = 0
    for (x1, y1), (x2, y2) in zip(PATH_DOC, PATH_DOC[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(H - y1)))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(H - y2)))
        t.SetWidth(pcbnew.FromMM(WIDTH))
        t.SetLayer(LAYER)
        t.SetNet(net)
        board.Add(t)
        n += 1
    pcbnew.SaveBoard(BOARD, board)
    print(f"✅ 补了 {n} 段 {NET} 走线（B.Cu {WIDTH}mm）→ {BOARD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

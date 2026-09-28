# -*- coding: utf-8 -*-
"""
SES（Specctra Session）导入器
================================================================================
背景：KiCad 10 的 ImportSpecctraSES() 对 FreeRouting v2.4.1 输出返回 False
（解析器不兼容），故自写 SES → pcbnew 走线/过孔导入。

SES 坐标 → KiCad 内部坐标（实测标定，验证见下）：
    x_k = x_ses * 0.1 μm → mm          （resolution um 10 → 1 单位 = 0.1 μm）
    y_k = −y_ses * 0.1 μm → mm         （FreeRouting 内部 y 翻转）
  验证：COL4 首点 SES (632000,-380700) → KiCad (63.2, 38.07) = CMD 轴 pad1 ✓

用法：
  "D:\kicad\bin\python.exe" tools/import_ses.py
  → 读 pcb/claudepad.kicad_pcb + claudepad.ses，写回含走线的板文件

运行后必须重跑 DRC 验证。
================================================================================
"""

import os
import sys

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD_PCB = os.path.join(ROOT, "pcb", "claudepad.kicad_pcb")
SES_PATH = os.path.join(os.environ.get("TEMP", os.path.dirname(BOARD_PCB)),
                        "kicad_install", "claudepad.ses")


# ============================== S 表达式解析 =================================
def tokenize(text):
    return text.replace("(", " ( ").replace(")", " ) ").split()


def parse_sexpr(tokens):
    """返回嵌套 list：['session', [...], ...]；原子为 str。"""
    stack, cur = [], []
    for tok in tokens:
        if tok == "(":
            stack.append(cur)
            cur = []
        elif tok == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(tok)
    return cur[0]


def find_all(node, key):
    """在嵌套 list 里找所有 key 开头的子表。"""
    out = []
    for item in node:
        if isinstance(item, list) and item and item[0] == key:
            out.append(item)
    return out


def find_first(node, key):
    for item in node:
        if isinstance(item, list) and item and item[0] == key:
            return item
    return None


# ============================== SES → 板 =====================================
def ses_to_mm(v):
    return float(v) * 0.1 / 1000.0    # 单位 0.1μm → mm


def main():
    ses = parse_sexpr(tokenize(open(SES_PATH, encoding="utf-8").read()))
    routes = find_first(ses, "routes")
    if routes is None:
        print("❌ SES 里没有 routes 段")
        return 1
    res = find_first(routes, "resolution")
    print(f"resolution: {res[1]} {res[2]}")

    # padstack 表：via 名 → (pad_mm, drill_mm)
    lib = find_first(routes, "library_out")
    padstacks = {}
    for ps in find_all(lib, "padstack"):
        name = ps[1]
        shapes = find_all(ps, "shape")
        dia = 0.6
        for sh in shapes:
            if sh[1] == "circle":
                dia = ses_to_mm(sh[3]) * 2
        m = name  # "Via[0-1]_600:300_um" → drill 在名字里
        drill = 0.3
        if "_600:300_" in name:
            drill = 0.3
        padstacks[name] = (dia, drill)

    board = pcbnew.LoadBoard(BOARD_PCB)
    net_map = {}
    for ni in board.GetNetsByNetcode().values():
        net_map[ni.GetNetname()] = ni

    n_track, n_via = 0, 0
    network_out = find_first(routes, "network_out")
    if network_out is None:
        print("❌ SES 里没有 network_out 段")
        return 1
    for netnode in find_all(network_out, "net"):
        netname = netnode[1].strip('"')   # FreeRouting 会给部分网络名加引号
        net = net_map.get(netname)
        if net is None:
            print(f"⚠️ SES 网络 {netname} 在板上不存在，跳过")
            continue
        for wire in find_all(netnode, "wire"):
            path = find_first(wire, "path")
            layer_name = path[1]
            width_mm = ses_to_mm(path[2])
            pts = [ses_to_mm(v) for v in path[3:]]
            if len(pts) % 2 != 0:
                print(f"⚠️ {netname} path 坐标数异常，跳过")
                continue
            layer = pcbnew.F_Cu if layer_name == "F.Cu" else pcbnew.B_Cu
            for i in range(0, len(pts) - 2, 2):
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(pts[i]), pcbnew.FromMM(-pts[i + 1])))
                tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(pts[i + 2]), pcbnew.FromMM(-pts[i + 3])))
                tr.SetWidth(pcbnew.FromMM(width_mm))
                tr.SetLayer(layer)
                tr.SetNet(net)
                board.Add(tr)
                n_track += 1
        for via in find_all(netnode, "via"):
            vname = via[1]
            x, y = ses_to_mm(via[2]), ses_to_mm(via[3])
            dia, drill = padstacks.get(vname, (0.6, 0.3))
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(-y)))
            v.SetWidth(pcbnew.FromMM(dia))
            v.SetDrill(pcbnew.FromMM(drill))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(net)
            board.Add(v)
            n_via += 1

    pcbnew.SaveBoard(BOARD_PCB, board)
    print(f"✅ 导入 {n_track} 段走线 + {n_via} 个过孔 → {BOARD_PCB}")
    print("⚠️ 运行后必须重跑 DRC 验证：kicad-cli pcb drc")
    return 0


if __name__ == "__main__":
    sys.exit(main())

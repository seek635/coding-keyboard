# -*- coding: utf-8 -*-
"""
ClaudePad KiCad PCB 生成器
================================================================================
用 KiCad 自带 Python + pcbnew API 生成整块 PCB（spec §6 技术路线）：

  "D:\kicad\bin\python.exe" tools/gen_kicad.py
  → pcb/claudepad.kicad_pcb

设计约束（spec §6.2）：
  · 只读 pcb/netlist.json（gen_pcb.py 从 params.scad 生成），不重算轴体坐标
  · 封装从 KiCad 官方库 FootprintLoad 加载，几何不手抄
  · Choc V2 官方库没有 → 按 datasheet 像素标定坐标自建（见 CHOC_PINS 来源 gen_pcb.py）

坐标系约定：
  netlist.json / 文档：原点=板左下角，Y 向上
  KiCad：Y 向下
  转换 T（视角转换，非实物镜像）：x_k = x_doc, y_k = H − y_doc
  旋转换算：θ_kicad = −θ_doc（文档逆时针 → KiCad 顺时针同值）

输出后验证：
  · 本文件自带自检（焊盘间距/缺口/板缘/主控区 NPTH/网络对照）
  · kicad-cli pcb drc（unconnected 为布线阶段预期项，其余须 0 错误）
================================================================================
"""

import json
import os
import sys

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETLIST = os.path.join(ROOT, "pcb", "netlist.json")
OUT_PCB = os.path.join(ROOT, "pcb", "claudepad.kicad_pcb")
KICAD_LIB = r"D:\kicad\share\kicad\footprints"

DIODE_FP_LIB = os.path.join(KICAD_LIB, "Diode_THT.pretty")
DIODE_FP_NAME = "D_DO-35_SOD27_P7.62mm_Horizontal"
HDR_FP_LIB = os.path.join(KICAD_LIB, "Connector_PinHeader_2.54mm.pretty")
HDR_FP_NAME = "PinHeader_1x12_P2.54mm_Vertical"


def mm(v):
    return pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1]))


def to_mm(iu):
    return (pcbnew.ToMM(iu.x), pcbnew.ToMM(iu.y))


# ---- 主控（NoLogo ProMicro NRF52840，背面直焊）常量 -------------------------
# 本体（文档坐标）x[79.70,97.48] y[12.50,45.50]；USB 端朝文档 +y。
# ★ y 位置两轮校正（2026-09-26）：
#   原 y[8.5,41.5]：右排最下 3 孔（COL4/5/6）落入拨杆缺口 → 上移；
#   y[12,45]：STOP 0° pad1 (81.2,11.93) 距左排首孔 (80.97,14.53) 仅 0.11mm → 下移 0.5；
#   终值 y[12.5,45.5]：左排孔带 y≥15.03，STOP 0° 焊盘间距 0.61 ✓；
#   外壳右壁 USB 开孔 y 位置联动（z 不变）。
# 排针 12 孔 ×2.54，跨距 27.94，两端余 2.53 → 孔 y 文档 15.03~42.97；
# 两排间距 15.24 → x = 79.70+1.27 = 80.97（左）与 96.21（右）。
MCU_X_L, MCU_X_R = 80.97, 96.21
MCU_PAD_Y1 = 42.97          # 文档 y（pad1，USB 端）
MCU_PAD_STEP = 2.54
# net 映射（标准 Pro Micro 引脚序，USB 端起 pad1..pad12；★ 打板前对实物复核）
JP1_NETS = [None, None, "GND", "GND", None, None,
            "ROW1", "ROW2", "ROW3", "COL1", "COL2", "COL3"]   # D1 D0 GND GND D2 D3 D4..D9
JP2_NETS = [None, "GND", "RST", None, None, None, None, None,
            "RGB_DIN", "COL6", "COL5", "COL4"]                # RAW GND RST VCC 21 20 19 18 15 14 16 10

# ---- 其他焊盘（spec §6.3 生成器自选位，注释=依据）----------------------------
# 拨杆引线：缺口上缘附近（y>14 出 SW5 底座投影带 [78,92]×[0,14]），
# 避开 STOP(-90°) 电气焊盘 (89.93,10.8)/(85,12.9) 与中心孔 Ø5
PAD_LEVER_NO = (89.0, 16.5)     # net APPROVE_MID（拨杆常开端）
PAD_LEVER_COM = (85.5, 15.8)    # net ROW1（拨杆公共端）
# 复位按钮：主控左侧空白（x<79.7），避开走廊1 二极管（STOP 位 65.4±4.56）
PAD_RST = (74.0, 17.0)          # net RST
PAD_GND = (78.0, 17.0)          # net GND
# D15 预留：避开 ENTER(67,25) 底座 [60,74] 与主控（x<79.7）
PAD_D15 = (76.0, 22.0)          # net RGB_DIN
# 电源开关：飞线转接件（开关引脚焊住，电池+/VBAT 走飞线，PCB 无网络需求）→ 无 net
PAD_PWR_SW = [(3.0, 23.0), (3.0, 27.0)]

# NPTH 定位孔省略清单（孔位无法避开主控区/缺口 → 定位脚悬空，机械靠定位板卡扣）：
#   ("ENTER",1) = (85,25) 180°：NPTH 落主控区，4 个正交角均避不开
#   ("STOP",0)  = (85,7)  0°：  NPTH (90.15,2) 落入缺口区（x≥90）
NPTH_SKIP = {("ENTER", 1), ("STOP", 0)}

ERRS = []
WARNS = []


def err(msg):
    ERRS.append(msg)


def warn(msg):
    WARNS.append(msg)


# ============================== 封装构造 =====================================
def make_choc_fp(board, ref, pos_doc, rot_doc, nets, skip_nth):
    """自建 Choc V2 封装（原点=轴芯中心）。
    pos_doc: 文档坐标轴心；nets: (col_net, row_net)；skip_nth: 省略的孔序号集合。
    pad1 = 电气脚1 → COL；pad2 = 电气脚2 → ROW；pad3 = 定位脚 NPTH；中心孔 NPTH。
    """
    x, y = pos_doc[0], 50.0 - pos_doc[1]
    fp = pcbnew.FOOTPRINT(board)
    board.Add(fp)
    fp.SetPosition(mm((x, y)))
    fp.SetReference(ref)
    fp.SetValue("ChocV2")
    # 两套坐标的"视觉逆时针"语义一致（y 约定与渲染视角同时反转，抵消）
    # 实测验证：SetOrientationDegrees(θ_doc) 即正确
    fp.SetOrientationDegrees(rot_doc)

    # 不画 courtyard：轴体间距由 18mm 网格数学保证（底座 13.95 + 走廊 4.05），
    # 且底座悬空于定位板（PCB 上方 5mm），courtyard 投影与正面元件重叠属结构性误报。

    pads = [
        # (number, x_doc, y_doc, drill, pad_d, type, net)
        ("1", -3.80, 4.93, 1.20, 2.0, "pth", nets[0]),
        ("2", -5.90, 0.00, 1.20, 2.0, "pth", nets[1]),
        ("3", 5.15, -5.00, 1.50, 1.50, "npth", None),
        ("", 0.0, 0.0, 5.00, 5.00, "npth", None),
    ]
    for i, (num, px, py, drill, dia, typ, net) in enumerate(pads):
        if i in skip_nth or (typ == "npth" and ("NPTH" in skip_nth)):
            continue
        pad = pcbnew.PAD(fp)
        fp.Add(pad)
        pad.SetNumber(num)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        if typ == "pth":
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        else:
            pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
        pad.SetSize(mm((dia, dia)))
        pad.SetDrillSize(mm((drill, drill)))
        # 相对坐标：T2 → y 取反
        pad.SetFPRelativePosition(mm((px, -py)))
        lset = pcbnew.LSET()
        lset.AddLayer(pcbnew.F_Cu)
        lset.AddLayer(pcbnew.B_Cu)
        lset.AddLayer(pcbnew.F_Mask)
        lset.AddLayer(pcbnew.B_Mask)
        pad.SetLayerSet(lset)
        if net:
            pad.SetNet(net_for(board, net))
    return fp


def add_edge(board, x1, y1, x2, y2):
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetStart(mm((x1, y1)))
    seg.SetEnd(mm((x2, y2)))
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetWidth(pcbnew.FromMM(0.1))
    board.Add(seg)


def add_silk_text(board, text, pos_doc, layer=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(layer or pcbnew.F_SilkS)
    t.SetPosition(mm(pos_doc))
    t.SetTextSize(mm((1.2, 1.2)))
    board.Add(t)


def add_fab_rect(board, x1, y1, x2, y2):
    """B.Fab 矩形（背面装配轮廓），文档坐标。"""
    for (a, b) in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)),
                   ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(mm((a[0], 50.0 - a[1])))
        seg.SetEnd(mm((b[0], 50.0 - b[1])))
        seg.SetLayer(pcbnew.B_Fab)
        seg.SetWidth(pcbnew.FromMM(0.1))
        board.Add(seg)


_NETS = {}


def net_for(board, name):
    if name not in _NETS:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        _NETS[name] = n
    return _NETS[name]


# ============================== 构建 =========================================
def build():
    nl = json.load(open(NETLIST, encoding="utf-8"))
    W = nl["pcb"]["width"]
    H = nl["pcb"]["height"]
    ny0, ny1 = nl["pcb"]["notch_y0"], nl["pcb"]["notch_y1"]
    nd = nl["pcb"]["notch_depth"]
    fpinfo = nl["switch_footprint"]

    board = pcbnew.BOARD()

    # ---- 板框（Edge.Cuts，KiCad 坐标）------------------------------------
    # 文档板 (0,0)-(98,50) + 右缘缺口 x[90,98] y[0,17.5]
    # T2 后：缺口 x[90,98] y'[H−17.5, 50]
    y0k, y1k = H - ny1, H - ny0
    x0k = W - nd
    add_edge(board, 0, 0, W, 0)
    add_edge(board, W, 0, W, y0k)
    add_edge(board, W, y0k, x0k, y0k)
    add_edge(board, x0k, y0k, x0k, H)
    add_edge(board, x0k, H, 0, H)
    add_edge(board, 0, H, 0, 0)

    # ---- 14 个轴体 --------------------------------------------------------
    sw_n = 0
    for k in sorted(nl["keys"], key=lambda x: (x["row"], x["col"])):
        for i, (x, y) in enumerate(k.get("pcb_positions") or []):
            sw_n += 1
            rot_doc = nl_switch_rot(k["label"], i)
            skip = {2} if (k["label"], i) in NPTH_SKIP else set()
            make_choc_fp(board, f"SW{sw_n}", (x, y), rot_doc,
                         (k["net_col"], k["net_row"]), skip)

    # ---- 12 只二极管（官方库加载，pad1=K→ROW、pad2=A→COL）----------------
    # ★ 该封装原点在 pad1（K），pad2 在 +7.62 → 放置点 = 中心 − 3.81
    d_n = 0
    for k in sorted(nl["keys"], key=lambda x: (x["row"], x["col"])):
        dp = k.get("diode_pcb_pos") or None
        if not dp:
            continue
        d_n += 1
        fp = pcbnew.FootprintLoad(DIODE_FP_LIB, DIODE_FP_NAME)
        board.Add(fp)
        fp.SetPosition(mm((dp[0] - 3.81, H - dp[1])))
        fp.SetReference(f"D{d_n}")
        fp.SetValue("1N4148")
        pad_k = fp.FindPadByNumber("1")
        pad_a = fp.FindPadByNumber("2")
        pad_k.SetNet(net_for(board, k["net_row"]))
        pad_a.SetNet(net_for(board, k["net_col"]))

    # ---- 主控排针 ×2（正面 PTH，主控本体在背面）---------------------------
    for col_x, nets, ref in [(MCU_X_L, JP1_NETS, "JP1"), (MCU_X_R, JP2_NETS, "JP2")]:
        fp = pcbnew.FootprintLoad(HDR_FP_LIB, HDR_FP_NAME)
        board.Add(fp)
        # ★ 该封装原点在 pad1，孔沿 +y 排列 0..27.94 → SetPosition 即 pad1 位置
        # pad1 = USB 端：文档 y = MCU_PAD_Y1 → KiCad y = 50 − 42.47 = 7.53
        fp.SetPosition(mm((col_x, H - MCU_PAD_Y1)))
        fp.SetReference(ref)
        fp.SetValue("MCU")
        # 删除排针自带 courtyard：主控位置定死、孔位已逐对校验，courtyard 只会与
        # 轴体中心让位孔（NPTH Ø5 阻焊圈）产生结构性误报
        for d in list(fp.GraphicalItems()):
            if d.GetLayer() == pcbnew.F_CrtYd:
                fp.Remove(d)
        for j, netname in enumerate(nets):
            pad = fp.FindPadByNumber(str(j + 1))
            if pad is None:
                err(f"{ref} 找不到 pad {j+1}")
                continue
            if netname:
                pad.SetNet(net_for(board, netname))

    # ---- 主控本体轮廓（B.Fab，装配标注）----------------------------------
    add_fab_rect(board, 79.70, 12.50, 97.48, 45.50)
    add_silk_text(board, "MCU on BACK (NoLogo ProMicro NRF52840)",
                  (58.0, 8.0))
    add_silk_text(board, "USB -> RIGHT WALL", (78.0, 45.5))

    # ---- 拨杆 / 复位 / D15 / 电源开关焊盘（1.5mm 孔 + 2.5mm 焊盘）---------
    aux = [
        ("LEV1", PAD_LEVER_NO, "APPROVE_MID", "拨杆 NO"),
        ("LEV2", PAD_LEVER_COM, "ROW1", "拨杆 COM"),
        ("RST1", PAD_RST, "RST", "复位按钮"),
        ("GND1", PAD_GND, "GND", "复位按钮"),
        ("RGB1", PAD_D15, "RGB_DIN", "D15 预留"),
        ("PWR1", PAD_PWR_SW[0], None, "电源开关(飞线)"),
        ("PWR2", PAD_PWR_SW[1], None, "电源开关(飞线)"),
    ]
    for ref, pos_doc, netname, note in aux:
        fp = pcbnew.FOOTPRINT(board)
        board.Add(fp)
        fp.SetPosition(mm((pos_doc[0], H - pos_doc[1])))
        fp.SetReference(ref)
        fp.SetValue(note)
        pad = pcbnew.PAD(fp)
        fp.Add(pad)
        pad.SetNumber("1")
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
        pad.SetSize(mm((2.5, 2.5)))
        pad.SetDrillSize(mm((1.5, 1.5)))
        pad.SetFPRelativePosition(mm((0, 0)))
        lset = pcbnew.LSET()
        for ly in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask):
            lset.AddLayer(ly)
        pad.SetLayerSet(lset)
        if netname:
            pad.SetNet(net_for(board, netname))

    os.makedirs(os.path.dirname(OUT_PCB), exist_ok=True)
    pcbnew.SaveBoard(OUT_PCB, board)
    print(f"✅ {OUT_PCB}")
    return board, nl


def nl_switch_rot(label, idx):
    """从 gen_pcb.py 的 SWITCH_ROT 语义读取（文档视角逆时针）。"""
    # 与 gen_pcb.py 保持一致的硬拷贝（避免 import 装饰器开销）；改动需两处同步
    table = {("STOP", 0): 0.0, ("ENTER", 1): 180.0, ("VOICE", 0): 180.0}
    return table.get((label, idx), 0.0)


# ============================== 自检（纯数据）================================
def verify(board, nl):
    H = nl["pcb"]["height"]
    W = nl["pcb"]["width"]
    ny0, ny1 = nl["pcb"]["notch_y0"], nl["pcb"]["notch_y1"]
    nd = nl["pcb"]["notch_depth"]
    mcu = (79.70, 12.50, 97.48, 45.50)   # 主控本体（文档坐标）

    pads = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            x, y = to_mm(pad.GetPosition())
            y_doc = H - y
            pads.append({
                "ref": fp.GetReference(), "num": pad.GetNumber(),
                "x": x, "y_doc": y_doc,
                "net": pad.GetNetname() if pad.GetNetname() else None,
                "drill": pcbnew.ToMM(pad.GetDrillSize().x),
                "npth": pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
            })

    # 1) 网络对照：每键 2 个电气 pad = COL/ROW
    keymap = {}
    for k in nl["keys"]:
        for pos in k.get("pcb_positions") or []:
            keymap[(round(pos[0], 2), round(pos[1], 2))] = (k["net_col"], k["net_row"], k["label"])
    for p in pads:
        if p["npth"] or p["drill"] > 3:
            continue
        key = keymap.get((round(p["x"], 2), round(p["y_doc"], 2)))
        if key and p["net"] not in key[:2]:
            err(f"{p['ref']}.{p['num']} net={p['net']} ≠ 期望 {key[:2]} @({p['x']},{p['y_doc']})")

    # 2) 异 net PTH 焊盘间距 ≥ 0.3mm
    pth = [p for p in pads if not p["npth"]]
    for i in range(len(pth)):
        for j in range(i + 1, len(pth)):
            a, b = pth[i], pth[j]
            if a["net"] and b["net"] and a["net"] == b["net"]:
                continue
            d2 = (a["x"] - b["x"]) ** 2 + (a["y_doc"] - b["y_doc"]) ** 2
            if d2 < 0.45 ** 2:  # 0.45mm 中心距硬下限（含焊盘半径后约 0.2 间隙）
                err(f"焊盘过近: {a['ref']}.{a['num']}({a['net']}) ↔ "
                    f"{b['ref']}.{b['num']}({b['net']}) 距 {d2 ** 0.5:.2f}mm")

    # 3) PTH 焊盘不得落入缺口 / 出板
    for p in pth:
        if not p["npth"]:
            if p["x"] >= W - nd and ny0 <= p["y_doc"] <= ny1:
                err(f"{p['ref']}.{p['num']} 落入缺口 ({p['x']},{p['y_doc']})")
        if p["x"] < 0 or p["x"] > W or p["y_doc"] < 0 or p["y_doc"] > H:
            err(f"{p['ref']}.{p['num']} 出板 ({p['x']},{p['y_doc']})")

    # 4) NPTH 定位孔（drill<3，不含中心让位孔）不得在主控区——
    #    定位脚会顶到背面主控板体；中心孔 Ø5 是凸台让位孔，凸台不长穿，允许在主控区
    for p in pads:
        if p["npth"] and p["ref"].startswith("SW") and p["drill"] < 3:
            if mcu[0] < p["x"] < mcu[2] and mcu[1] < p["y_doc"] < mcu[3]:
                err(f"{p['ref']} NPTH 定位孔在主控区 ({p['x']},{p['y_doc']})")

    # 5) 数量
    n_sw = sum(1 for p in pads if p["ref"].startswith("SW"))
    n_d = sum(1 for fp in board.GetFootprints() if fp.GetReference().startswith("D"))
    print(f"  轴体 pad 数: {n_sw}（期望 14×(4−省略)）；二极管: {n_d}（期望 12）")
    if n_d != 12:
        err(f"二极管数量 {n_d} ≠ 12")

    print()
    if WARNS:
        print("⚠️ 警告:")
        for w in WARNS:
            print(f"  {w}")
    if ERRS:
        print(f"❌ 自检 {len(ERRS)} 项失败:")
        for e in ERRS:
            print(f"  {e}")
        return False
    print("✅ 自检通过：网络对照 / 焊盘间距 / 缺口 / 板缘 / 主控区")
    return True


def main():
    board, nl = build()
    ok = verify(board, nl)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

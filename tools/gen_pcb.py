#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClaudePad PCB 网表与接线图生成器
================================================================================
从 cad/lib/params.scad 读取键位表（单一数据源），生成：

  pcb/netlist.json  机器可读网表
  pcb/netlist.md    人读网表（焊接对照表）
  pcb/wiring.svg    接线图（矢量，可打印放大）
  pcb/wiring.png    接线图（位图，快速预览）

绘图采用「一份布局描述 + 两个渲染后端」：所有图元先记录到 Canvas，
再分别由 SVG 和 Pillow 渲染，保证两张图内容完全一致。

关键数据（已交叉验证两个独立开源封装库，坐标完全一致）：

  Kailh Choc V1 (PG1350) PCB 焊盘坐标（原点 = 轴芯中心）：
    电气引脚 1   (0, 5.9)    孔径 1.27
    电气引脚 2   (-5, 3.8)   孔径 1.27
    轴芯中心孔   (0, 0)      孔径 3.429  （非金属化）
    侧固定孔     (±5.5, 0)   孔径 1.7018 （非金属化）

  二极管方向 col2row：阳极接列、阴极接行，电流 列 → 行
    列 = 输出驱动（GPIO_ACTIVE_HIGH）
    行 = 输入读取（GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN）

运行：python tools/gen_pcb.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scad_params import load, load_keymap, find_project_root     # noqa: E402

ROOT = find_project_root() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "pcb")

P = load()
KEYMAP = load_keymap()

# ---- 引脚分配（必须与 firmware/.../claudepad.overlay 一致）------------------
ROW_PINS = ["D4", "D5", "D6"]
COL_PINS = ["D7", "D8", "D9", "D10", "D16", "D14"]
APPROVE_PIN = "D14"

# ---- Choc V1 PCB 焊盘（原点 = 轴芯中心，mm）---------------------------------
CHOC_PAD1 = (0.0, 5.9)
CHOC_PAD2 = (-5.0, 3.8)
CHOC_PAD_DRILL = 1.27

PITCH = P["PITCH"]
BORDER = P["PLATE_BORDER"]
# PCB 相对定位板的偏移（PCB 比定位板小一圈，居中放置）
PCB_W, PCB_H = P["PCB_W"], P["PCB_H"]
PCB_OX = (P["PLATE_W"] - PCB_W) / 2      # = 8.0
PCB_OY = (P["PLATE_H"] - PCB_H) / 2      # = 8.0
PCB_NOTCH_D, PCB_NOTCH_L = P["PCB_NOTCH_D"], P["PCB_NOTCH_L"]

# 配色
C_COL, C_ROW = "#dc2626", "#2563eb"
C_TEXT, C_MUTED, C_LINE = "#111827", "#6b7280", "#e5e7eb"
C_KEY1, C_KEYN, C_SW = "#e0f2fe", "#dcfce7", "#fef3c7"
S_KEY1, S_KEYN, S_SW = "#0284c7", "#16a34a", "#d97706"


# ============================== 网表构建 ====================================
def build():
    def n_switch(u):
        return 1 if u <= 1 else (2 if u == 2 else 3)

    def axis_x(c, u, i):
        """第 i 个轴体的 x（相对定位板左缘）"""
        if u <= 1:
            return BORDER + (c - 1) * PITCH + PITCH * 0.5
        return BORDER + (c - 1) * PITCH + PITCH * (0.5 + i * (u - 1) / (n_switch(u) - 1))

    keys = []
    for (c, r, u, tag) in sorted(KEYMAP, key=lambda k: (k[1], k[0])):
        plate_pos = [(round(axis_x(c, u, i), 2),
                      round(BORDER + (r - 1) * PITCH + PITCH / 2, 2))
                     for i in range(n_switch(u))]
        keys.append({
            "label": tag, "row": r, "col": c, "width_u": u,
            "switches": n_switch(u),
            "net_row": f"ROW{r}", "net_col": f"COL{c}",
            "pin_row": ROW_PINS[r - 1], "pin_col": COL_PINS[c - 1],
            "diode": "1N4148",
            # 相对定位板左下角
            "positions": plate_pos,
            # 相对 PCB 左下角（画板子用这个）
            "pcb_positions": [(round(x - PCB_OX, 2), round(y - PCB_OY, 2))
                              for (x, y) in plate_pos],
        })

    keys.append({
        "label": "APPROVE", "row": 1, "col": 6, "width_u": 1, "switches": 1,
        "net_row": "ROW1", "net_col": "COL6",
        "pin_row": ROW_PINS[0], "pin_col": APPROVE_PIN,
        "diode": "1N4148（建议）", "positions": [], "pcb_positions": [],
        "note": "SPDT 拨动开关，不是轴体。装在右壁，本体在壳内，公共端接 ROW1、常开端接 COL6",
    })

    rows = [{"name": f"ROW{i}", "pin": p, "keys": [k["label"] for k in keys if k["row"] == i]}
            for i, p in enumerate(ROW_PINS, 1)]
    cols = [{"name": f"COL{i}", "pin": p, "keys": [k["label"] for k in keys if k["col"] == i]}
            for i, p in enumerate(COL_PINS, 1)]

    return {
        "board": "ClaudePad",
        "matrix": {"rows": len(ROW_PINS), "cols": len(COL_PINS)},
        "pinout": {"rows": ROW_PINS, "cols": COL_PINS,
                   "approve": APPROVE_PIN, "rgb_data": "D15"},
        "diode_direction": "col2row",
        "diode_rule": "阳极接列线，阴极接行线（电流 列 → 行）",
        "switch_footprint": {
            "name": "Kailh Choc V1 (PG1350)",
            "pad1": CHOC_PAD1, "pad2": CHOC_PAD2,
            "center_hole": (0.0, 0.0), "side_holes": [(-5.5, 0.0), (5.5, 0.0)],
            "pad_drill_mm": CHOC_PAD_DRILL, "pad_size_mm": 2.0,
        },
        "rows": rows, "cols": cols, "keys": keys,
        "total_switches": sum(k["switches"] for k in keys if k["label"] != "APPROVE"),
        "pcb": {
            "width": PCB_W, "height": PCB_H, "thickness": P["PCB_T"],
            "origin_offset_from_plate": [PCB_OX, PCB_OY],
            "notch_depth": PCB_NOTCH_D, "notch_length": PCB_NOTCH_L,
            "notch_note": "右侧开缺口让位给拨杆本体，纵向对准拨杆位置",
        },
    }


# ============================== 画布 ========================================
# 画布与渲染后端抽在 tools/canvas.py，与「按键行程图」共用
from canvas import Canvas, render_svg, render_png     # noqa: E402

# ============================== 接线图布局 ==================================
def draw_wiring(nl):
    W, H = 1280, 940
    c = Canvas(W, H)
    X0, Y0, DX, DY = 300, 300, 150, 150
    cx = [X0 + i * DX for i in range(6)]
    cy = [Y0 + j * DY for j in range(3)]

    # 标题
    c.text(40, 46, "ClaudePad 接线图 · 3 行 × 6 列矩阵", 24, C_TEXT, "start", True)
    c.text(40, 74, "二极管方向 col2row：阳极接列、阴极接行，电流 列 → 行 ｜ 由 tools/gen_pcb.py 生成",
           14, C_MUTED)

    # 列线（垂直）与行线（水平）——先画线，方块后画以遮住线
    # 列线长度按「该列最后一个用到的行」决定，避免悬空线头
    keymap0 = {(k["row"], k["col"]) for k in nl["keys"]}
    for i, x in enumerate(cx):
        last_row = max((r for (r, cc) in keymap0 if cc == i + 1), default=1)
        c.line(x, 150, x, cy[last_row - 1] + 42, C_COL, 2.5)
    for y in cy:
        c.line(cx[0] - 70, y, cx[5] + 70, y, C_ROW, 2.5)

    # 列引脚标签（顶部）
    for i, (x, pin) in enumerate(zip(cx, COL_PINS)):
        c.text(x, 88, "输出驱动", 10, "#9ca3af", "middle")
        c.rect(x - 34, 96, 68, 40, "#fef2f2", C_COL, 1.5, 7)
        c.text(x, 114, f"COL{i+1}", 13, "#991b1b", "middle", True)
        c.text(x, 130, pin, 12, "#b91c1c", "middle")

    # 行引脚标签（右侧）
    for j, (y, pin) in enumerate(zip(cy, ROW_PINS)):
        c.rect(cx[5] + 80, y - 20, 72, 40, "#eff6ff", C_ROW, 1.5, 7)
        c.text(cx[5] + 116, y - 4, f"ROW{j+1}", 13, "#1e40af", "middle", True)
        c.text(cx[5] + 116, y + 12, pin, 12, "#1d4ed8", "middle")
        c.text(cx[5] + 116, y + 34, "输入读取", 10, "#9ca3af", "middle")

    # 矩阵交点
    keymap = {(k["row"], k["col"]): k for k in nl["keys"]}
    for j, y in enumerate(cy):
        for i, x in enumerate(cx):
            k = keymap.get((j + 1, i + 1))
            if not k:
                c.line(x - 9, y - 9, x + 9, y + 9, "#d1d5db", 2)
                c.line(x + 9, y - 9, x - 9, y + 9, "#d1d5db", 2)
                continue

            is_sw = k["label"] == "APPROVE"
            fill = C_SW if is_sw else (C_KEY1 if k["switches"] == 1 else C_KEYN)
            stroke = S_SW if is_sw else (S_KEY1 if k["switches"] == 1 else S_KEYN)

            # 二极管：画在列线上、两行方块之间的空隙中央
            # 行距 150，方块高 60 → 空隙 90，符号占约 44，居中放
            dy = y - 75
            c.rect(x - 13, dy - 22, 26, 44, "#ffffff")          # 遮住列线
            c.line(x, dy - 24, x, dy - 11, C_COL, 2)
            c.poly([(x - 8, dy - 11), (x + 8, dy - 11), (x, dy + 3)], C_COL)   # 阳极朝下
            c.line(x - 8, dy + 3, x + 8, dy + 3, C_COL, 2.8)                    # 阴极横杠
            c.line(x, dy + 3, x, dy + 22, C_ROW, 2)

            # 轴体方块（后画，遮住行线/列线，形成"线接入方块"的视觉）
            c.rect(x - 52, y - 30, 104, 60, fill, stroke, 2, 9)
            c.text(x, y - 4, k["label"], 14, C_TEXT, "middle", True)
            sub = ("拨动开关" if is_sw
                   else (f'{k["switches"]} 轴并联' if k["switches"] > 1 else "1 轴"))
            c.text(x, y + 14, sub, 11, stroke, "middle")

    # 图例
    lx, ly = 40, 780
    c.rect(lx, ly, 580, 126, "#f9fafb", C_LINE, 1, 10)
    c.text(lx + 16, ly + 26, "图例", 14, "#374151", "start", True)
    c.line(lx + 16, ly + 48, lx + 56, ly + 48, C_COL, 2.5)
    c.text(lx + 66, ly + 52, "列线（输出驱动，ACTIVE_HIGH）", 12, "#4b5563")
    c.line(lx + 16, ly + 74, lx + 56, ly + 74, C_ROW, 2.5)
    c.text(lx + 66, ly + 78, "行线（输入读取，ACTIVE_HIGH | PULL_DOWN）", 12, "#4b5563")
    c.poly([(lx + 30, ly + 92), (lx + 42, ly + 92), (lx + 36, ly + 104)], C_COL)
    c.line(lx + 30, ly + 104, lx + 42, ly + 104, C_COL, 2.4)
    c.text(lx + 66, ly + 104, "1N4148 · 阳极接列、阴极接行（col2row）", 12, "#4b5563")

    # 单键回路说明
    rx, ry = 660, 780
    c.rect(rx, ry, 580, 126, "#f9fafb", C_LINE, 1, 10)
    c.text(rx + 16, ry + 26, "单个按键回路", 14, "#374151", "start", True)
    c.text(rx + 16, ry + 58, "列线 → 二极管阳极 → 阴极 → 轴体 → 行线", 13, C_TEXT)
    c.text(rx + 16, ry + 84, "按下时回路导通，列被驱动为高 → 行读到高 → 固件判定按下",
           12, C_MUTED)
    c.text(rx + 16, ry + 108, "注意：二极管接反不会烧毁，但矩阵读不出来。修正：全部掉头，或改 diode-direction",
           12, "#b45309")
    return c


# ============================== 输出 ========================================
def write_json(nl):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "netlist.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(nl, f, ensure_ascii=False, indent=2)
    return p


def write_md(nl):
    L = []
    A = L.append
    A("# ClaudePad PCB 网表\n")
    A(f"矩阵 **{nl['matrix']['rows']} 行 × {nl['matrix']['cols']} 列**"
      f"｜轴体 **{nl['total_switches']} 个**（含大键并联）｜审批拨杆 **1 个**\n")
    A("> 本文件由 `tools/gen_pcb.py` 从 `cad/lib/params.scad` 自动生成，不要手改。\n")

    A("## 1. 引脚分配\n")
    A("| 信号 | nice!nano 引脚 | 说明 |")
    A("|---|---|---|")
    for r in nl["rows"]:
        A(f"| {r['name']} | **{r['pin']}** | 行，输入（`ACTIVE_HIGH \\| PULL_DOWN`） |")
    for c in nl["cols"]:
        A(f"| {c['name']} | **{c['pin']}** | 列，输出（`ACTIVE_HIGH`） |")
    A(f"| RGB 数据 | {nl['pinout']['rgb_data']} | WS2812 数据线 |")
    A("")

    A("## 2. 二极管方向\n")
    A(f"`diode-direction = \"{nl['diode_direction']}\"`\n")
    A(f"**{nl['diode_rule']}**\n")
    A("即每个按键回路：**列线 → 二极管阳极 → 二极管阴极 → 轴体 → 行线**\n")
    A("> 接反不会烧，但矩阵读不出来。修正二选一：所有二极管掉头，"
      "或把固件 `diode-direction` 改成 `\"row2col\"`。\n")

    A("## 3. 按键接线对照表\n")
    A("| # | 按键 | 矩阵位置 | 行线 | 列线 | 轴体数 | 二极管 |")
    A("|---|---|---|---|---|---|---|")
    for i, k in enumerate(nl["keys"], 1):
        A(f"| {i} | **{k['label']}** | 行{k['row']}·列{k['col']} | "
          f"{k['net_row']}({k['pin_row']}) | {k['net_col']}({k['pin_col']}) | "
          f"{k['switches']} | {k['diode']} |")
    A("")

    big = [k for k in nl["keys"] if k["switches"] > 1]
    if big:
        A("### 大键并联接法（重要）\n")
        for k in big:
            A(f"**{k['label']}**（{k['width_u']}u）—— 定位板开 {k['switches']} 个轴孔，"
              f"**{k['switches']} 个轴体电气并联**到同一个矩阵交点 "
              f"（{k['net_row']} × {k['net_col']}）：\n")
            A("```")
            A(f"  轴体① 引脚 → {k['net_col']} ｜ 轴体① 另一脚 → 二极管 → {k['net_row']}")
            for n in range(2, k["switches"] + 1):
                A(f"  轴体{'①②③④'[n-1]} 引脚 → 与轴体① 同一条线（并联）")
            A("```")
            A("")
        A("> PCB：这几个轴体的焊盘用铜箔连到同一条行/列线。")
        A("> 手焊洞洞板：用一根导线把它们的引脚串起来。\n")

    A("## 4. Choc V1 轴体 PCB 封装\n")
    A("原点 = 轴芯中心。坐标已交叉验证两个独立开源封装库（daprice / siderakb），完全一致。\n")
    A("| 特征 | 坐标 (x, y) mm | 孔径 mm | 类型 |")
    A("|---|---|---|---|")
    A(f"| 电气引脚 1 | ({CHOC_PAD1[0]}, {CHOC_PAD1[1]}) | {CHOC_PAD_DRILL} | 金属化 |")
    A(f"| 电气引脚 2 | ({CHOC_PAD2[0]}, {CHOC_PAD2[1]}) | {CHOC_PAD_DRILL} | 金属化 |")
    A("| 轴芯中心孔 | (0, 0) | 3.429 | 非金属化 |")
    A("| 侧固定孔 ×2 | (±5.5, 0) | 1.7018 | 非金属化 |")
    A("")
    A("> 两电气引脚间距 = √(5² + 2.1²) = **5.42 mm**\n")

    A("## 5. 其他元件\n")
    A("| 元件 | 连接 |")
    A("|---|---|")
    A("| 审批拨杆 SPDT | 公共端 → ROW1；常开端 → COL6。**串一只 1N4148 防鬼影** |")
    A("| 电池 | JST 1.25 插座 → nice!nano 的 BAT 焊盘（注意极性） |")
    A("| 电源开关 | 串在电池正极与主控之间 |")
    A("| 复位按钮 | 并联到 nice!nano 的 RST 焊盘 |")
    A("| WS2812 | 数据线 → D15，电源接 3.3V/VCC，地接 GND |")
    A("")

    p = os.path.join(OUT, "netlist.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return p


def main():
    nl = build()
    os.makedirs(OUT, exist_ok=True)

    errs = []
    used = set()
    for k in nl["keys"]:
        pos = (k["row"], k["col"])
        if pos in used:
            errs.append(f"矩阵位置冲突：{pos}")
        used.add(pos)
        if not (1 <= k["row"] <= len(ROW_PINS)):
            errs.append(f"{k['label']} 行号越界")
        if not (1 <= k["col"] <= len(COL_PINS)):
            errs.append(f"{k['label']} 列号越界")

    print("=" * 72)
    print("ClaudePad PCB 网表生成")
    print("=" * 72)
    print(f"  矩阵        : {nl['matrix']['rows']} 行 × {nl['matrix']['cols']} 列")
    print(f"  矩阵交点    : {len(nl['keys'])} 个（含审批拨杆）")
    print(f"  轴体总数    : {nl['total_switches']} 个（9 单键 + 回车 2 + 空格 3）")
    print(f"  审批拨杆    : 1 个（SPDT 拨动开关）")
    print(f"  行引脚      : {', '.join(ROW_PINS)}")
    print(f"  列引脚      : {', '.join(COL_PINS)}")
    print()
    print(f"{'按键':<10}{'位置':<12}{'行线':<16}{'列线':<16}{'轴数'}")
    print("-" * 72)
    for k in nl["keys"]:
        rn = f"{k['net_row']}({k['pin_row']})"
        cn = f"{k['net_col']}({k['pin_col']})"
        pos = f"行{k['row']}·列{k['col']}"
        print(f"{k['label']:<10}{pos:<12}{rn:<16}{cn:<16}{k['switches']}")

    # 生成文件
    c = draw_wiring(nl)
    files = [write_json(nl), write_md(nl)]
    svg_p = os.path.join(OUT, "wiring.svg")
    with open(svg_p, "w", encoding="utf-8") as f:
        f.write(render_svg(c))
    files.append(svg_p)
    try:
        files.append(render_png(c, os.path.join(OUT, "wiring.png")))
    except Exception as e:
        print(f"⚠️  PNG 渲染失败（不影响 SVG）：{e}")

    print()
    for p in files:
        print(f"✅ {os.path.relpath(p, ROOT)}")

    print()
    if errs:
        print(f"❌ {len(errs)} 个问题：")
        for e in errs:
            print(f"   · {e}")
        return 1
    print(f"✅ 自检通过：{len(nl['keys'])} 个矩阵位置无冲突，引脚分配在范围内")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按键行程剖面图
================================================================================
画一张侧向剖面，说明「键帽为什么必须离定位板一整个键程的距离」。

这张图回答的问题：
  键帽裙边（17.6mm）比定位板轴孔（13.8mm）宽 → 塞不进孔里
  → 键帽只能悬在定位板上方
  → 所以「键帽底面到定位板顶面」的距离必须 ≥ 轴体键程，否则按不下去

图里画两个状态：
  · 实线 = 静止
  · 虚线 = 按到底（整体下移一个键程）

生成：docs/按键行程图.svg / .png
运行：python tools/draw_travel.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scad_params import load, find_project_root     # noqa: E402
from canvas import Canvas, render_svg, render_png, C_TEXT, C_MUTED   # noqa: E402

ROOT = find_project_root() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs")

P = load()
f = lambda v: f"{v:.2f}"

# ---- 尺寸（mm，从 params.scad 取）------------------------------------------
PLATE_T = P["PLATE_T"]
CASE_INNER_H = P["CASE_INNER_H"]
CASE_BOTTOM_T = P["CASE_BOTTOM_T"]
CAP_GAP = P["CAP_GAP"]
CAP_H = P["CAP_H"]
CAP_WALL = P["CAP_WALL"]
TRAVEL = P["SWITCH_TRAVEL"]
PITCH = P["PITCH"]
SKIRT = PITCH - 0.40
HOLE = P["SWITCH_CUTOUT"]

# ---- 布局 ----------------------------------------------------------------
# 竖直方向按比例放大显示（真实 3.3mm 太小看不清），横向也压缩
SCALE_Z = 46          # 每毫米多少像素
W, H = 1180, 900
CX = 430              # 剖面中心 x
PLATE_TOP_Y = 560     # 定位板顶面的 y 像素

def zy(z_from_plate_top):
    """把「相对定位板顶面」的高度换成像素 y（向上为正）"""
    return PLATE_TOP_Y - z_from_plate_top * SCALE_Z


def draw():
    c = Canvas(W, H)

    # ---- 标题 ----
    c.text(40, 46, "按键行程剖面图", 24, C_TEXT, "start", True)
    c.text(40, 74, "键帽裙边比定位板轴孔宽，塞不进孔里 —— 所以键帽必须整体悬在板上方，"
                   "下压时不能撞到板", 13, C_MUTED)

    # ---- 定位板（剖面：一条横条）----
    plate_y = PLATE_TOP_Y
    c.rect(CX - 330, plate_y, 660, PLATE_T * SCALE_Z, "#d8c88c", "#a68a3f", 1.5)
    # 轴孔（中间断开）
    c.rect(CX - HOLE / 2 * 10, plate_y, HOLE * 10, PLATE_T * SCALE_Z, "#ffffff", "none")

    # ---- 轴体（剖面：本体 + 轴芯）----
    sw_w = 13.5 * 10          # 轴体宽（横向放大 10 倍便于观看）
    body_h = 2.4 * SCALE_Z    # 定位板之上的本体高度（示意）
    c.rect(CX - sw_w / 2, zy(0) - body_h, sw_w, body_h, "#cfe3f7", "#4a86c8", 1.5)
    # 轴芯
    stem_w = 11
    stem_h = 1.8 * SCALE_Z
    c.rect(CX - stem_w / 2, zy(1.8), stem_w, stem_h, "#9dc0e8", "#2f6ba8", 1.5)
    # 标注放左侧（键帽内腔是白的，文字清楚）
    c.line(CX - stem_w / 2 - 4, zy(1.8) + 8, CX - stem_w / 2 - 40, zy(1.8) + 8, "#2f6ba8", 1)
    c.text(CX - stem_w / 2 - 46, zy(1.8) + 12, "轴芯", 11, "#2f6ba8", "end")

    # ---- 键帽（静止，实线）----
    cap_bot = zy(CAP_GAP)
    cap_top = zy(CAP_GAP + CAP_H)
    cap_w = SKIRT * 10
    # 外壳轮廓（下大上小）
    inset = 6
    c.poly([(CX - cap_w / 2, cap_bot), (CX + cap_w / 2, cap_bot),
            (CX + cap_w / 2 - inset, cap_top), (CX - cap_w / 2 + inset, cap_top)],
           "#f5d0c0", "#c4633c", 2)
    # 内腔（挖空）
    c.poly([(CX - cap_w / 2 + CAP_WALL * 10, cap_bot + 2),
            (CX + cap_w / 2 - CAP_WALL * 10, cap_bot + 2),
            (CX + cap_w / 2 - inset - CAP_WALL * 8, cap_top - 2),
            (CX - cap_w / 2 + inset + CAP_WALL * 8, cap_top - 2)],
           "#ffffff", "none")
    # 榫槽（套在轴芯上）
    c.rect(CX - stem_w / 2 - 2, cap_bot, stem_w + 4, CAP_H * SCALE_Z, "#ffffff", "none")
    c.text(CX + cap_w / 2 + 14, (cap_bot + cap_top) / 2, "键帽（静止）", 13, "#c4633c")

    # ---- 键帽（按到底，虚线）----
    d_bot = zy(CAP_GAP - TRAVEL)
    d_top = zy(CAP_GAP - TRAVEL + CAP_H)
    for (x1, y1, x2, y2) in [
        (CX - cap_w / 2, d_bot, CX + cap_w / 2, d_bot),
        (CX - cap_w / 2, d_bot, CX - cap_w / 2 + inset, d_top),
        (CX + cap_w / 2, d_bot, CX + cap_w / 2 - inset, d_top),
        (CX - cap_w / 2 + inset, d_top, CX + cap_w / 2 - inset, d_top),
    ]:
        c.line(x1, y1, x2, y2, "#c4633c", 2, dash="7 5")
    c.text(CX + cap_w / 2 + 14, (d_bot + d_top) / 2, "键帽（按到底）", 13, "#c4633c")

    # ---- 行程标注 ----
    ax = CX - cap_w / 2 - 60
    c.line(ax, cap_bot, ax, d_bot, "#0f6e56", 2)
    c.arrow(ax, cap_bot + 4, ax, d_bot - 4, "#0f6e56", 2)
    c.text(ax - 12, (cap_bot + d_bot) / 2, f"键程 {f(TRAVEL)}", 13, "#0f6e56", "end", True)

    # ---- 间隙标注（关键）----
    gx = CX + cap_w / 2 + 130
    c.line(gx, plate_y, gx, cap_bot, "#b45309", 2)
    c.arrow(gx, plate_y + 4, gx, cap_bot - 4, "#b45309", 2)
    c.text(gx + 12, (plate_y + cap_bot) / 2, f"键帽底面离定位板 {f(CAP_GAP)}", 13,
           "#b45309", "start", True)

    # ---- 关键尺寸标注 ----
    c.text(40, 690, f"键帽裙边宽 {f(SKIRT)} mm", 13, "#c4633c")
    c.text(40, 712, f"定位板轴孔宽 {f(HOLE)} mm", 13, "#a68a3f")
    c.text(40, 734, f"→ 裙边比孔宽 {f(SKIRT - HOLE)} mm，塞不进孔里", 13, C_TEXT)

    c.text(40, 772, "结论：键帽只能悬在定位板上方，所以", 13, C_TEXT)
    c.text(40, 794, f"  ① 键帽底面离定位板 ≥ 轴体键程（{f(CAP_GAP)} ≥ {f(TRAVEL)}）", 13, C_TEXT)
    c.text(40, 816, "  ② 否则裙边会撞在定位板上，按不下去", 13, C_TEXT)

    # ---- 对比框：错 vs 对 ----
    bx = 700
    c.rect(bx, 660, 440, 190, "#f9fafb", "#e5e7eb", 1, 10)
    c.text(bx + 18, 688, "这次的 bug", 14, "#b91c1c", "start", True)
    c.text(bx + 18, 714, "原来：间隙 0.30mm，键程需要 3.00mm", 12, "#4b5563")
    c.text(bx + 18, 734, "→ 按 0.3mm 就顶死，行程全废", 12, "#b91c1c")
    c.text(bx + 18, 766, "修正后：间隙 3.30mm ≥ 键程 3.00mm", 12, "#4b5563")
    c.text(bx + 18, 786, "→ 完整 3mm 行程可用", 12, "#0f6e56")
    c.text(bx + 18, 818, "代价：整机高度 20.1 → 23.1mm", 12, "#6b7280")
    c.text(bx + 18, 838, "（这 3mm 是物理上必须的）", 12, "#6b7280")

    # ---- 定位板标注 ----
    c.line(CX - 330, plate_y - 8, CX - 330, plate_y + PLATE_T * SCALE_Z + 8, "#a68a3f", 1)
    c.text(CX - 340, plate_y + PLATE_T * SCALE_Z / 2, "定位板", 12, "#a68a3f", "end")

    return c


def main():
    c = draw()
    os.makedirs(OUT, exist_ok=True)
    svg = os.path.join(OUT, "按键行程图.svg")
    png = os.path.join(OUT, "按键行程图.png")
    open(svg, "w", encoding="utf-8").write(render_svg(c))
    print(f"✅ {os.path.relpath(svg, ROOT)}")
    try:
        render_png(c, png)
        print(f"✅ {os.path.relpath(png, ROOT)}")
    except Exception as e:
        print(f"⚠️  PNG 渲染失败（不影响 SVG）：{e}")

    print()
    print("=" * 64)
    print("按键行程核算")
    print("=" * 64)
    print(f"  键帽底面离定位板顶面 : {f(CAP_GAP)} mm")
    print(f"  轴体键程             : {f(TRAVEL)} mm")
    ok = CAP_GAP >= TRAVEL
    print(f"  → {'✅ 行程完整' if ok else '❌ 按不下去'}（可用 {f(min(CAP_GAP, TRAVEL))} mm）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

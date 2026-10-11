#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClaudePad 板子标注图生成器
========================================================================
从生成物直接画图（不写死坐标）：

  轴体/二极管  <- pcb/placement.csv        （tools/gen_pcb.py 生成）
  主控/排针/焊盘 <- pcb/claudepad.kicad_pcb （取真实封装坐标）
  板框/缺口    <- cad/lib/params.scad

产出：
  docs/img/board-annotated.png / .svg       带标注的板子俯视图（列号 / 键名 / 主控区 / 缺口）
  docs/img/space-row-before-after.png/.svg  空格行「贴左排」改前改后示意

运行：python tools/render_board_annotated.py
（上一版这两张图是临时脚本画的，改板后没重生成 —— 这次固化成脚本，跟数据源同步。）
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from canvas import Canvas, render_svg, render_png      # noqa: E402
from scad_params import load as load_params            # noqa: E402
from render_assembly import SWITCHES, JP_XS, JP_N, JP_PITCH, JP_Y0, NANO, PADS, _ITEMS   # noqa: E402

P = load_params()
IMG = os.path.join(ROOT, "docs", "img")
PCB_W, PCB_H = P["PCB_W"], P["PCB_H"]
ND, NY0, NY1 = P["PCB_NOTCH_D"], P["PCB_NOTCH_Y0"], P["PCB_NOTCH_Y1"]

PI = ((-3.80, 4.93), (-5.90, 0.00), (5.15, -5.00))     # Choc V2 三根脚（文档坐标）


def circle(c, x, y, r, fill="none", stroke="none", sw=1.0, n=28):
    pts = [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n))
           for i in range(n)]
    c.poly(pts, fill, stroke, sw)


def render_board():
    sc, mg = 16.0, 78.0
    W = int(PCB_W * sc + mg * 2)
    H = int(PCB_H * sc + mg * 2 + 70)
    c = Canvas(W, H, "#ffffff")
    X = lambda x: mg + x * sc
    Y = lambda y: mg + (PCB_H - y) * sc          # 文档 y 向上 → 屏幕 y 向下

    # ---- 板框（含右缘缺口）----
    poly = [(0, 0), (PCB_W - ND, 0), (PCB_W - ND, NY1), (PCB_W, NY1), (PCB_W, PCB_H), (0, PCB_H)]
    c.poly([(X(x), Y(y)) for x, y in poly], "#1f6b3d", "#2f9e5f", 2)

    # ---- 主控区（背面）+ 排针 ----
    c.rect(X(NANO[0]), Y(NANO[3]), (NANO[2] - NANO[0]) * sc, (NANO[3] - NANO[1]) * sc,
           "none", "#e05252", 2, 0)
    c.text(X((NANO[0] + NANO[2]) / 2), Y(NANO[3]) - 8, "主控 NoLogo（装在背面）",
           13, "#b91c1c", "middle", True)
    for i, jx in enumerate(JP_XS):
        for k in range(JP_N):
            jy = JP_Y0 + k * JP_PITCH
            circle(c, X(jx), Y(jy), 0.85 * sc, "#f0c419", "#a67c00", 0.8)
        c.text(X(jx), Y(JP_Y0) + 20, f"JP{i+1} ×{JP_N}", 11, "#7a5c00", "middle", True)

    # ---- 轴体：中心孔 + 三根脚（按真实旋转角）----
    for label, x, y, rot in SWITCHES:
        th = math.radians(rot)
        ct, st = math.cos(th), math.sin(th)
        c.rect(X(x) - 7.5 * sc, Y(y) - 7.5 * sc, 15 * sc, 15 * sc, "#e8eef5", "#9fb3c8", 1.5, 6)
        circle(c, X(x), Y(y), 2.5 * sc, "#dfe6ee", "#7b8b9c", 1.5)
        for dx, dy in PI:
            hx, hy = x + dx * ct - dy * st, y + dx * st + dy * ct
            anchor = (dx, dy) == (5.15, -5.0)
            circle(c, X(hx), Y(hy), (0.75 if anchor else 0.6) * sc,
                   "none" if anchor else "#f0c419", "#a67c00", 1.2)
        c.text(X(x), Y(y) + 4, label, 12, "#1b3a5c", "middle", True)
        if rot:
            c.text(X(x), Y(y) + 18, f"{rot:g}°", 10, "#b45309", "middle")

    # ---- 飞线焊盘 ----
    for ref, x, y, _side in PADS:
        circle(c, X(x), Y(y), 0.75 * sc, "#f0c419", "#7a5c00", 1.0)
        c.text(X(x) + 9, Y(y) + 4, ref, 9, "#7a5c00")

    # ---- 列号 + 网格 ----
    col_x = [13, 31, 49, 67, 85]
    for i, cx in enumerate(col_x):
        c.text(X(cx), Y(0) + 22, f"列{i+1}", 12, "#1f2937", "middle", True)
        c.text(X(cx), Y(0) + 36, f"x={cx}", 10, "#6b7280", "middle")

    # ---- 空格行第 5 列（空出来的那一格）----
    c.rect(X(85) - 9 * sc, Y(43) - 7.5 * sc, 18 * sc, 15 * sc, "none", "#c02626", 1.5, 6)
    c.text(X(85), Y(43) + 4, "空", 13, "#c02626", "middle", True)
    c.text(X(85), Y(43) + 20, "列5 空出", 10, "#c02626", "middle")

    # ---- 标题 ----
    c.text(mg, 34, f"ClaudePad PCB {PCB_W:.0f} × {PCB_H:.0f} × {P['PCB_T']} mm（俯视，正面朝上）",
           17, "#111827", "start", True)
    c.text(mg, 56, "黄点＝镀铜孔 ｜ 空心圈＝不通电定位孔 ｜ 灰圆＝轴芯中心孔 Ø5 ｜ "
                   "红框＝主控（背面）｜ 缺口＝拨杆让位", 12, "#6b7280")
    c.text(mg, 74, "★ 本图按板子的文档坐标画：上方 = +y = 空格那一行；下方 = 键盘远端（停止那一行）。"
                   "空格行 4 颗键贴左排，列 5 空出。", 12, "#b45309")
    c.text(W - mg, H - 14, "由 tools/render_board_annotated.py 从 placement.csv / 板文件生成",
           10, "#9ca3af", "end")
    return c


def render_space_row():
    """空格行改前 / 改后（只画轴心 + 列号）"""
    sc, mg = 26.0, 70.0
    cols = [13, 31, 49, 67, 85]
    W = int(5 * 18 * sc + mg * 2 + 40)
    H = 330
    c = Canvas(W, H, "#ffffff")
    X = lambda x: mg + (x - 4) * sc
    c.text(mg, 34, "空格那一行：4 颗键「贴左排」（2026-10-11 按用户要求改）", 17, "#111827", "start", True)

    panels = [
        (110, "改之前（列 2-4 + 列 5）", [(31, "SPACE", "#cfe3ff"), (49, "SPACE", "#cfe3ff"),
                                       (67, "SPACE", "#cfe3ff"), (85, "VOICE", "#ffe8c2")],
         "列 1 空着 → 左边缺一块"),
        (225, "改之后（列 1-3 + 列 4）", [(13, "SPACE", "#cfe3ff"), (31, "SPACE", "#cfe3ff"),
                                       (49, "SPACE", "#cfe3ff"), (67, "VOICE", "#ffe8c2")],
         "贴左排，列 5 空出 → 主控上方不再压轴体"),
    ]
    for y0, title, keys, note in panels:
        c.text(mg, y0 - 14, title, 13, "#374151", "start", True)
        for i, cx in enumerate(cols):
            c.text(X(cx), y0 + 52, f"列{i+1}", 10, "#9ca3af", "middle")
            c.line(X(cx), y0 - 4, X(cx), y0 + 42, "#e5e7eb", 1)
        for cx, name, fill in keys:
            c.rect(X(cx) - 9 * sc, y0 - 2, 18 * sc, 44, fill, "#7b8b9c", 1.5, 6)
            c.text(X(cx), y0 + 24, name, 11, "#1b3a5c", "middle", True)
        c.text(mg, y0 + 74, note, 11, "#b45309")
    c.text(mg, H - 16, "空格 3u 跨列 1-3（3 根轴并联到同一矩阵点 ROW3×COL1）；语音键列 4",
           11, "#6b7280")
    return c


def main():
    os.makedirs(IMG, exist_ok=True)
    for name, canvas in (("board-annotated", render_board()),
                         ("space-row-before-after", render_space_row())):
        with open(os.path.join(IMG, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(render_svg(canvas))
        render_png(canvas, os.path.join(IMG, f"{name}.png"))
        print(f"OK -> docs/img/{name}.png / .svg")


if __name__ == "__main__":
    main()

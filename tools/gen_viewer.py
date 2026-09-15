#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三维查看器尺寸注入器
================================================================================
把 cad/output/viewer.html 里所有写死的尺寸，替换成从 cad/lib/params.scad
实时算出来的值。

为什么需要它：
  viewer.html 是手写的 HTML，里面有尺寸链、整机外形、常量定义。
  这些值如果手抄，改了 params.scad 之后就会漂移 —— 本项目最忌讳「多源」。
  所以用标记圈出待生成区块，由本脚本回填。

标记区块（内联）：
  <!--GEN:SIZE-->…<!--/GEN:SIZE-->        整机外形尺寸（副标题）
标记区块（整行）：
  <!--GEN:CHAIN-->…<!--/GEN:CHAIN-->      垂直尺寸链
  <!--GEN:INNER-->…<!--/GEN:INNER-->      内腔净高分解
  //GEN:CONST … //GEN:CONST-END           three.js 用的常量

运行：python tools/gen_viewer.py
改尺寸后必跑（和 check_dims.py 一样）
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scad_params import load, find_project_root      # noqa: E402

ROOT = find_project_root()
if not ROOT:
    print("❌ 找不到项目根目录（向上搜索 cad/lib/params.scad 失败）")
    sys.exit(1)

VIEWER = os.path.join(ROOT, "cad", "output", "viewer.html")

P = load()
f2 = lambda v: f"{v:.2f}"


# ---- 派生尺寸（全部由 params.scad 推导，不手写）---------------------------
CASE_WALL = P["CASE_WALL"]
CASE_TOP_TOL = P["CASE_TOP_TOL"]
PLATE_W, PLATE_H, PLATE_T = P["PLATE_W"], P["PLATE_H"], P["PLATE_T"]
CASE_BOTTOM_T = P["CASE_BOTTOM_T"]
CASE_INNER_H = P["CASE_INNER_H"]
PCB_STANDOFF_H, PCB_T = P["PCB_STANDOFF_H"], P["PCB_T"]
CAP_GAP, CAP_H = P["CAP_GAP"], P["CAP_H"]
PITCH, BORDER = P["PITCH"], P["PLATE_BORDER"]
SWITCH_PLATE_GAP = P["SWITCH_PLATE_GAP"]

CASE_W = PLATE_W + CASE_TOP_TOL * 2 + CASE_WALL * 2
CASE_D = PLATE_H + CASE_TOP_TOL * 2 + CASE_WALL * 2

PLATE_BOTTOM_Z = CASE_BOTTOM_T + CASE_INNER_H
PLATE_TOP_Z = PLATE_BOTTOM_Z + PLATE_T
CAP_BOTTOM_Z = PLATE_TOP_Z + CAP_GAP
CAP_TOP_Z = CAP_BOTTOM_Z + CAP_H
PCB_BOTTOM_Z = CASE_BOTTOM_T + PCB_STANDOFF_H
PCB_TOP_Z = PCB_BOTTOM_Z + PCB_T
TOTAL_H = CAP_TOP_Z


def _indent(lines, pad):
    """把若干行按给定缩进拼起来"""
    return "\n".join(pad + ln for ln in lines)


# 每个区块的「内层内容」，直接替换标记之间的部分
# 注意：整行区块的首尾要带换行 + 缩进，保持 HTML 整洁
INNER = {
    "SIZE": f"尺寸 {f2(CASE_W)} × {f2(CASE_D)} × {f2(TOTAL_H)} mm",

    "CHAIN": "\n" + _indent([
        f'<span class="k">键帽顶面</span> <b>z = {f2(CAP_TOP_Z)}</b><br>',
        f'<span class="k">键帽底面</span> <b>z = {f2(CAP_BOTTOM_Z)}</b><br>',
        f'<span class="k">定位板顶面</span> <b>z = {f2(PLATE_TOP_Z)}</b><br>',
        f'<span class="k">定位板底面</span> <b>z = {f2(PLATE_BOTTOM_Z)}</b><br>',
        f'<span class="k">PCB 上表面</span> <b>z = {f2(PCB_TOP_Z)}</b><br>',
        f'<span class="k">PCB 下表面</span> <b>z = {f2(PCB_BOTTOM_Z)}</b><br>',
        f'<span class="k">底板上表面</span> <b>z = {f2(CASE_BOTTOM_T)}</b><br>',
        '<span class="k">桌面</span> <b>z = 0.00</b>',
    ], "        ") + "\n        ",

    "INNER": "\n" + _indent([
        f'<label class="title">内腔净高 {CASE_INNER_H:.1f} mm</label>',
        '<div class="spec">',
        f'  <span class="k">电池/走线层</span> <b>{PCB_STANDOFF_H:.1f}</b><br>',
        f'  <span class="k">PCB</span> <b>{PCB_T:.1f}</b><br>',
        f'  <span class="k">轴体卡扣间隙</span> <b>{SWITCH_PLATE_GAP:.1f}</b>',
        '</div>',
    ], "      ") + "\n      ",

    "CONST": "\n" + _indent([
        f'const PITCH = {PITCH:.1f}, CASE_WALL = {CASE_WALL:.1f}, BORDER = {BORDER:.1f};',
        f'const PLATE_BOTTOM_Z = {PLATE_BOTTOM_Z:.1f}, PLATE_T = {PLATE_T:.1f}, '
        f'CAP_GAP = {CAP_GAP:.1f};',
        f'const CAP_Z = PLATE_BOTTOM_Z + PLATE_T + CAP_GAP;   // {CAP_BOTTOM_Z:.1f}',
    ], "") + "\n",
}

# 每个区块的完整匹配正则（含标记）
PATTERNS = {
    "SIZE":  re.compile(r"(<!--GEN:SIZE-->)(.*?)(<!--/GEN:SIZE-->)", re.S),
    "CHAIN": re.compile(r"(<!--GEN:CHAIN-->)(.*?)(<!--/GEN:CHAIN-->)", re.S),
    "INNER": re.compile(r"(<!--GEN:INNER-->)(.*?)(<!--/GEN:INNER-->)", re.S),
    "CONST": re.compile(r"(//GEN:CONST)(.*?)(//GEN:CONST-END)", re.S),
}


def patch(text):
    """替换所有标记区块，返回 (新文本, [(区块名, 状态, 是否改动)])"""
    report = []
    for name, inner in INNER.items():
        m = PATTERNS[name].search(text)
        if not m:
            report.append((name, "未找到标记", False))
            continue
        old = m.group(2)
        if old == inner:
            report.append((name, "已是最新", False))
        else:
            report.append((name, "已更新", True))
        text = text[:m.start(2)] + inner + text[m.end(2):]
    return text, report


def main():
    if not os.path.exists(VIEWER):
        print(f"❌ 找不到 {VIEWER}")
        return 1

    text = open(VIEWER, encoding="utf-8").read()
    new, report = patch(text)

    print("=" * 68)
    print("三维查看器尺寸注入")
    print("=" * 68)
    print("  数据源：cad/lib/params.scad")
    print(f"  目标  ：{os.path.relpath(VIEWER, ROOT)}")
    print()
    for name, msg, did in report:
        print(f"  {'✏️ ' if did else '   '}{name:8} {msg}")
    print()

    n = sum(1 for _, _, d in report if d)
    if n:
        open(VIEWER, "w", encoding="utf-8").write(new)
        print(f"✅ 已写入（{n} 个区块更新）")
    else:
        print("✅ 无需改动，已是最新")

    print()
    print("当前尺寸：")
    print(f"  整机   {f2(CASE_W)} × {f2(CASE_D)} × {f2(TOTAL_H)} mm")
    print(f"  尺寸链 键帽顶 {f2(CAP_TOP_Z)} ← 键帽底 {f2(CAP_BOTTOM_Z)} "
          f"← 定位板 {f2(PLATE_TOP_Z)}/{f2(PLATE_BOTTOM_Z)} "
          f"← PCB {f2(PCB_TOP_Z)}/{f2(PCB_BOTTOM_Z)} ← 底板 {f2(CASE_BOTTOM_T)}")
    print(f"  键程   {CAP_GAP:.2f} mm（需 ≥ {P['SWITCH_TRAVEL']:.2f}）")

    missing = [n_ for n_, m, _ in report if m == "未找到标记"]
    if missing:
        print()
        print(f"⚠️  以下标记未找到：{', '.join(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
固件 ↔ 结构 一致性校验
----------------------
键盘项目最容易出的错：改了 CAD 布局忘了改固件键位（或反过来）。
本脚本把两边对齐验证。

校验内容：
  1. overlay 的矩阵变换 map 数量 == keymap 的 bindings 数量
  2. 两个数量 == params.scad 的键位数 + 1（审批拨杆）
  3. 键位顺序逐项比对（params.scad 的 KEYMAP 顺序 vs keymap 的 bindings 顺序）
  4. 每个键绑定的行为是否与 PRD 定义的功能相符
  5. 所有自定义行为的 #binding-cells 与实际传参个数是否匹配

运行：python tools/check_keymap.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scad_params import load_keymap     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIELD = os.path.join(ROOT, "firmware", "boards", "shields", "claudepad")
OVERLAY = os.path.join(SHIELD, "claudepad.overlay")
KEYMAP = os.path.join(SHIELD, "claudepad.keymap")

# ZMK 内建行为的参数个数（只列本项目用到的）
BUILTIN_CELLS = {
    "kp": 1, "none": 0, "trans": 0, "mo": 1, "tog": 1, "to": 1,
    "bt": 2, "rgb_ug": 2, "bootloader": 0, "sys_reset": 0,
}

# 每个键位标签「应该」绑定什么行为（依据 PRD 第 3 章）
EXPECTED = {
    "PERM":    "perm",
    "UP":      "kp",
    "MODEL":   "model",
    "CMD":     "cmd",
    "STOP":    "stop",
    "LEFT":    "kp",
    "DOWN":    "kp",
    "RIGHT":   "kp",
    "ENTER":   "ent_td",
    "SPACE":   "spc_tab",
    "VOICE":   "voice",
}
# 审批拨杆（不在 KEYMAP 里，单独列出）
APPROVE_BEHAVIOR = "kp"

errors = []
warns = []


def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    return t


def parse_behavior_cells(text):
    """从 keymap 文件里解析所有自定义行为的 #binding-cells"""
    cells = {}
    # 抓取每个节点块： label: node_name { ... };
    for m in re.finditer(r"([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)\s*\{(.*?)\n\s*\};",
                         text, flags=re.S):
        label, body = m.group(1), m.group(3)
        cm = re.search(r"#binding-cells\s*=\s*<(\d+)>", body)
        if cm:
            cells[label] = int(cm.group(1))
    return cells


def tokenize_bindings(text, cells):
    """把 keymap 里 default_layer 的 bindings 解析成 [(行为名, [参数...]), ...]

    ⚠️ 必须限定在 default_layer 块内查找 —— 文件里前面的宏也有 bindings，
       直接全局搜会抓到宏的 bindings（这是个真实踩过的坑）。
    """
    lm = re.search(r"default_layer\s*\{(.*?)\n\s*\};", text, flags=re.S)
    scope = lm.group(1) if lm else text

    m = re.search(r"bindings\s*=\s*<(.*?)>\s*;", scope, flags=re.S)
    if not m:
        return []
    body = m.group(1)
    # 切成 token：&name 或普通标识符/数字/括号表达式
    tokens = re.findall(r"&[A-Za-z_]\w*|[A-Za-z_]\w*\([^)]*\)|[A-Za-z_]\w*|\d+", body)

    out = []
    i = 0
    all_cells = {**BUILTIN_CELLS, **cells}
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("&"):
            name = tok[1:]
            n = all_cells.get(name)
            if n is None:
                errors.append(f"未定义的行为：&{name}（无法确定参数个数）")
                i += 1
                continue
            params = tokens[i + 1: i + 1 + n]
            if len(params) < n:
                errors.append(f"&{name} 需要 {n} 个参数，实际只给了 {len(params)} 个")
            out.append((name, params))
            i += 1 + n
        else:
            i += 1
    return out


def main():
    for p in (OVERLAY, KEYMAP):
        if not os.path.exists(p):
            print(f"❌ 文件不存在：{p}")
            return 1

    overlay = strip_comments(open(OVERLAY, encoding="utf-8").read())
    keymap_raw = open(KEYMAP, encoding="utf-8").read()
    keymap = strip_comments(keymap_raw)

    print("=" * 74)
    print("固件 ↔ 结构 一致性校验")
    print("=" * 74)

    # ---- 1. 矩阵变换 map ----
    tm = re.search(r"map\s*=\s*<(.*?)>\s*;", overlay, flags=re.S)
    if not tm:
        print("❌ overlay 里没找到 matrix-transform 的 map")
        return 1
    rc_list = re.findall(r"RC\((\d+),(\d+)\)", tm.group(1))
    print(f"\n【矩阵变换】map 里有 {len(rc_list)} 个 RC() 交点")
    for idx, (r, c) in enumerate(rc_list):
        print(f"  [{idx:>2}] 行{int(r)+1} 列{int(c)+1}")

    # 行/列数声明
    cols_decl = re.search(r"columns\s*=\s*<(\d+)>", overlay)
    rows_decl = re.search(r"rows\s*=\s*<(\d+)>", overlay)
    if cols_decl and rows_decl:
        nc, nr = int(cols_decl.group(1)), int(rows_decl.group(1))
        print(f"  声明矩阵 = {nr} 行 × {nc} 列")
        # 检查 col-gpios / row-gpios 数量
        n_col = len(re.findall(r"&pro_micro\s+\d+", overlay.split("col-gpios")[1].split(";")[0]))
        n_row = len(re.findall(r"&pro_micro\s+\d+", overlay.split("row-gpios")[1].split(";")[0]))
        print(f"  row-gpios = {n_row} 个，col-gpios = {n_col} 个")
        if n_row != nr:
            errors.append(f"rows 声明 {nr} 但 row-gpios 有 {n_row} 个")
        if n_col != nc:
            errors.append(f"columns 声明 {nc} 但 col-gpios 有 {n_col} 个")
        # 每个 RC 必须落在范围内
        for r, c in rc_list:
            if int(r) >= nr or int(c) >= nc:
                errors.append(f"RC({r},{c}) 超出 {nr}×{nc} 矩阵范围")

    # ---- 2. 解析 bindings ----
    cells = parse_behavior_cells(keymap)
    print(f"\n【自定义行为】解析到 {len(cells)} 个")
    for k, v in sorted(cells.items()):
        print(f"  &{k:<16} 参数个数 = {v}")

    bindings = tokenize_bindings(keymap, cells)
    print(f"\n【键位绑定】共 {len(bindings)} 个")

    # ---- 3. 数量比对 ----
    km = load_keymap()          # CAD 侧的键位表
    expect_count = len(km) + 1  # +1 = 审批拨杆
    print(f"\n【数量比对】")
    print(f"  CAD 键位      : {len(km)} 个 + 审批拨杆 1 个 = {expect_count}")
    print(f"  矩阵变换 map  : {len(rc_list)}")
    print(f"  keymap 绑定   : {len(bindings)}")
    if len(rc_list) != expect_count:
        errors.append(f"矩阵 map 数量 {len(rc_list)} ≠ 期望 {expect_count}")
    if len(bindings) != expect_count:
        errors.append(f"keymap 绑定数量 {len(bindings)} ≠ 期望 {expect_count}")
    if len(rc_list) != len(bindings):
        errors.append(f"map 数量 {len(rc_list)} ≠ 绑定数量 {len(bindings)}（键位会错位）")

    # ---- 4. 顺序与功能比对 ----
    print(f"\n【逐项比对】")
    print(f"{'#':<4}{'CAD 键位':<12}{'期望行为':<12}{'实际绑定':<20}{'结果'}")
    print("-" * 74)

    # CAD 侧顺序：按 (行, 列) 排序，审批拨杆插在行1末尾
    ordered = sorted(km, key=lambda k: (k[1], k[0]))
    expected_seq = []
    for (c, r, u, tag) in ordered:
        if r == 1:
            expected_seq.append((tag, EXPECTED.get(tag, "?")))
            if c == 5:      # 行1 最后一格之后插审批拨杆
                expected_seq.append(("APPROVE", APPROVE_BEHAVIOR))
        else:
            expected_seq.append((tag, EXPECTED.get(tag, "?")))

    for i, (tag, exp) in enumerate(expected_seq):
        if i >= len(bindings):
            print(f"{i:<4}{tag:<12}{exp:<12}{'(缺失)':<20}❌")
            errors.append(f"键位 {tag} 没有对应绑定")
            continue
        actual, params = bindings[i]
        ok = (actual == exp)
        mark = "✅" if ok else "❌"
        pstr = " ".join(params) if params else ""
        print(f"{i:<4}{tag:<12}&{exp:<11}&{actual} {pstr:<16}{mark}")
        if not ok:
            errors.append(f"键位 {tag}：期望 &{exp}，实际 &{actual}")

    # ---- 5. 大键并联检查 ----
    print(f"\n【大键并联】")
    for (c, r, u, tag) in km:
        if u > 1:
            n_axis = 3 if u >= 3 else 2
            print(f"  {tag}（{u}u）：定位板开 {n_axis} 个轴孔，电气上并联到同一矩阵交点")
    print("  ⚠️ 这要求 PCB 把大键的多个轴体焊盘接到同一条行线/列线")

    # ---- 汇总 ----
    print("\n" + "=" * 74)
    if errors:
        print(f"❌ 发现 {len(errors)} 个问题：")
        for e in errors:
            print(f"   · {e}")
        return 1
    print("✅ 固件与结构完全一致")
    print(f"   {len(bindings)} 个键位、矩阵 {nr if cols_decl else '?'}×{nc if cols_decl else '?'}、"
          f"顺序与功能均与 PRD 相符")
    return 0


if __name__ == "__main__":
    sys.exit(main())

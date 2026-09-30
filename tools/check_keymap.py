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

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scad_params import load_keymap     # noqa: E402
from console_utf8 import enable         # noqa: E402

enable()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIELD = os.path.join(ROOT, "firmware", "config", "boards", "shields", "claudepad")
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

    # ---- 6. zmk-config 布局自检（决定 CI 能不能编译）----
    # 这些是 2026-10-01 实际踩过的坑：布局错一处，GitHub Actions 就编不出来，
    # 而且报错信息很绕（"shield not found"）。固化成检查，避免再犯。
    print(f"\n【zmk-config 布局自检】")
    fw = os.path.join(ROOT, "firmware")

    want = os.path.join("config", "boards", "shields", "claudepad")
    actual = os.path.relpath(SHIELD, fw).replace("\\", "/")
    if actual == want.replace("\\", "/"):
        print(f"  ✅ shield 位置正确：{actual}")
    else:
        print(f"  ❌ shield 位置错误：{actual}（应为 {want}）")
        errors.append(f"shield 不在 <ZMK_CONFIG>/boards/shields/ 下：{actual}")

    module_yml = os.path.join(fw, "zephyr", "module.yml")
    if os.path.exists(module_yml):
        print("  ❌ 存在 firmware/zephyr/module.yml —— 官方 CI 会改走「模块」分支")
        errors.append("firmware/zephyr/module.yml 存在，会让 CI 走模块路径而找不到 shield")
    else:
        print("  ✅ 无 zephyr/module.yml（保持标准 zmk-config，CI 走默认路径）")

    build_yaml = os.path.join(fw, "build.yaml")
    shields = []
    if os.path.exists(build_yaml):
        with open(build_yaml, encoding="utf-8") as f:
            shields = re.findall(r"^\s*shield:\s*(\S+)", f.read(), re.M)
    if shields == ["claudepad"]:
        print("  ✅ build.yaml 声明 shield = claudepad")
    else:
        print(f"  ❌ build.yaml 的 shield = {shields}（应为 ['claudepad']）")
        errors.append(f"build.yaml 的 shield 声明与目录名不符：{shields}")

    west = os.path.join(fw, "config", "west.yml")
    wf = os.path.join(fw, ".github", "workflows", "build.yml")
    rev = ref = None
    if os.path.exists(west):
        with open(west, encoding="utf-8") as f:
            m = re.search(r"name:\s*zmk\b.*?revision:\s*(\S+)", f.read(), re.S)
            rev = m.group(1) if m else None
    if not os.path.exists(wf):
        print("  ❌ 缺少 .github/workflows/build.yml —— 推上去不会触发构建")
        errors.append("缺少 GitHub Actions 工作流文件，推送后不会有任何构建")
    else:
        with open(wf, encoding="utf-8") as f:
            m = re.search(r"build-user-config\.yml@(\S+)", f.read())
            ref = m.group(1) if m else None
        if rev and ref and rev == ref:
            print(f"  ✅ ZMK 版本一致：west.yml 与 workflow 均为 {rev}")
        else:
            print(f"  ❌ ZMK 版本不一致：west.yml={rev}，workflow={ref}")
            errors.append(f"west.yml({rev}) 与 workflow({ref}) 的 ZMK 版本不一致")

    # ---- 7. 引脚交叉校验（固件 ↔ PCB 网表）----
    # docs/PCB设计规格书.md 第 100 行原本写着：「check_keymap 会检查键位顺序但
    # 不检查引脚，需人工确认」。这里补上自动校验。
    # 引脚错了的后果很隐蔽：固件能编译、板子也焊得出来，但整机完全不工作。
    print(f"\n【引脚交叉校验（固件 ↔ PCB 网表）】")
    netlist = os.path.join(ROOT, "pcb", "netlist.json")
    if not os.path.exists(netlist):
        print("  ⚠️ 找不到 pcb/netlist.json，跳过")
    else:
        with open(netlist, encoding="utf-8") as f:
            nl = json.load(f)
        with open(OVERLAY, encoding="utf-8") as f:
            ov = strip_comments(f.read())

        # `&pro_micro N` 在 nice_nano / Pro Micro 兼容板上就是 D N
        # （依据 ZMK app/boards/arm/nice_nano/arduino_pro_micro_pins.dtsi：
        #   4→gpio0 22、7→gpio0 11、16→gpio0 10、14→gpio1 11，正是 D4/D7/D16/D14）
        def gpio_pins(prop):
            m = re.search(prop + r"([^;]*);", ov, re.S)
            if not m:
                return []
            return [f"D{n}" for n in re.findall(r"&pro_micro\s+(\d+)", m.group(1))]

        for prop, key, label in (("row-gpios", "rows", "行"), ("col-gpios", "cols", "列")):
            got = gpio_pins(prop)
            want = nl["pinout"][key]
            if got == want:
                print(f"  ✅ {label}引脚一致：{' '.join(got)}")
            else:
                print(f"  ❌ {label}引脚不一致")
                print(f"       固件：{' '.join(got) or '(未解析到)'}")
                print(f"       PCB ：{' '.join(want)}")
                errors.append(f"{label}引脚 固件({got}) ≠ PCB 网表({want})")

        m = re.search(r'diode-direction\s*=\s*"(\w+)"', ov)
        got_dir = m.group(1) if m else None
        want_dir = nl.get("diode_direction")
        if got_dir == want_dir:
            print(f"  ✅ 二极管方向一致：{got_dir}（阳极接列、阴极接行）")
        else:
            print(f"  ❌ 二极管方向不一致：固件={got_dir}，PCB={want_dir}")
            errors.append(f"二极管方向 固件({got_dir}) ≠ PCB({want_dir})")

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

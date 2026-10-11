# -*- coding: utf-8 -*-
"""按焊接步骤生成板文件变体，并渲染进度图
----------------------------------------------------------------------
用法（纯 Python，内部调用 kicad-cli）：
  C:\\Users\\尚\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/render_steps.py

产出：
  pcb/steps/step{0..5}-*.kicad_pcb          各步骤板文件变体（自打样原文件派生）
  docs/img/step{0..5}-*.png                 正面等轴测进度图
  docs/img/step2-mcu-back.png / step3-wires-back.png   背面图（主控/电池在背面）

步骤（对应 docs/焊接指南.md §1 的 ①~⑤）：
  step0 裸板 → step1 +二极管 → step2 +排针/主控 → step3 +飞线/电池/开关
  → step4 +轴体 → step5 +拨杆（最终）
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "pcb", "claudepad.kicad_pcb")
STEPDIR = os.path.join(ROOT, "pcb", "steps")
IMGDIR = os.path.join(ROOT, "docs", "img")
KICAD_CLI = r"D:\kicad\bin\kicad-cli.exe"
M = lambda n: os.path.join(ROOT, "cad", "models", n).replace("\\", "/")

CHOC, PINS, PLASTIC = M("choc_v2.step"), M("header_pins_front.step"), M("header_plastic_back.step")
MCU, BATT, AUX, LEVER = M("promicro_at_JP1.step"), M("battery_at_PWR1.step"), M("aux_parts_at_PWR1.step"), M("lever_at_LEV1.step")

# (步骤名, 保留二极管官方模型, 挂载表 ref前缀/精确 → 模型列表)
HEADERS = {"JP1": [PINS, PLASTIC, MCU], "JP2": [PINS, PLASTIC]}
WIRED = {**HEADERS, "PWR1": [BATT, AUX]}
SWITCHED = {**WIRED, "SW": [CHOC]}
STEPS = [
    ("step0-bare",     False, {}),
    ("step1-diodes",   True,  {}),
    ("step2-mcu",      True,  HEADERS),
    ("step3-wires",    True,  WIRED),
    ("step4-switches", True,  SWITCHED),
    ("step5-final",    True,  {**SWITCHED, "LEV1": [LEVER]}),
]
BACK_STEPS = {"step2-mcu", "step3-wires"}     # 额外渲染背面图的步骤


def iter_model_blocks(block):
    """产出 footprint 块内所有 (model ...) 的 (起,止) 位置"""
    i = 0
    while True:
        i = block.find("(model ", i)
        if i < 0:
            return
        j, d = i, 0
        while j < len(block):
            if block[j] == "(":
                d += 1
            elif block[j] == ")":
                d -= 1
                if d == 0:
                    break
            j += 1
        yield i, j + 1
        i = j + 1


def strip_models(block, remove_fn):
    """删除 remove_fn(seg) 判定为真的 (model ...) 块"""
    out, last, removed = [], 0, 0
    for a, b in iter_model_blocks(block):
        seg = block[a:b]
        if remove_fn(seg):
            out.append(block[last:a])
            last = b
            removed += 1
    out.append(block[last:])
    return "".join(out), removed


def build_variant(name, keep_diodes, attach):
    text = open(SRC, encoding="utf-8").read()
    out, i, n, depth, added = [], 0, len(text), 0, 0
    while i < n:
        if text.startswith("(footprint", i) and depth == 1:
            j, d = i, 0
            while j < n:
                if text[j] == "(":
                    d += 1
                elif text[j] == ")":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            block = text[i:j + 1]
            # 官方 PinHeader 永远剥掉（胶条与轴体底座穿模）；不保留二极管时全剥
            block, _ = strip_models(block, lambda s: "PinHeader" in s or not keep_diodes)
            mref = re.search(r'\(property "Reference" "([^"]+)"', block)
            if mref:
                ref = mref.group(1)
                paths = attach.get(ref) or (attach.get("SW") if re.match(r"^SW\d+$", ref) else None) or []
                extra = ""
                for path in paths:
                    extra += (f'\n\t(model "{path}"\n\t\t(offset (xyz 0 0 0))\n'
                              f'\t\t(scale (xyz 1 1 1))\n\t\t(rotate (xyz 0 0 0)))\n')
                    added += 1
                if extra:
                    block = block[:-1].rstrip("\t") + extra + "\n\t)"
            out.append(block)
            i = j + 1
            continue
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        out.append(text[i])
        i += 1
    path = os.path.join(STEPDIR, f"{name}.kicad_pcb")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(out))
    return path, added


def render(board, img, side):
    rotate = "-30,0,20" if side == "top" else "-30,0,-160"
    cmd = [KICAD_CLI, "pcb", "render", board, "-o", img,
           "--side", side, "--rotate", rotate, "--perspective", "--floor",
           "--background", "opaque", "--width", "1600", "--height", "1000",
           "--quality", "basic"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = "成功" in (r.stdout + r.stderr)
    print(f"  {'OK' if ok else 'FAIL'} {os.path.basename(img)}")
    return ok


def main():
    os.makedirs(STEPDIR, exist_ok=True)
    os.makedirs(IMGDIR, exist_ok=True)
    for name, keep, attach in STEPS:
        board, added = build_variant(name, keep, attach)
        print(f"{name}: 挂载 {added} 个模型")
        render(board, os.path.join(IMGDIR, f"{name}.png"), "top")
        if name in BACK_STEPS:
            render(board, os.path.join(IMGDIR, f"{name}-back.png"), "bottom")
    return 0


if __name__ == "__main__":
    sys.exit(main())

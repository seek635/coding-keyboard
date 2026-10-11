# -*- coding: utf-8 -*-
"""把元件 3D 模型挂到 ClaudePad 板文件副本上（供 kicad-cli pcb render 用）
----------------------------------------------------------------------
运行（必须用 KiCad 自带 Python）：
  D:\\kicad\\bin\\python.exe tools/attach_3d_models.py

流程：读 pcb/claudepad.kicad_pcb → 文本级手术 → 存 pcb/claudepad_render.kicad_pcb
  1. 剥掉 JP 封装自带的官方 PinHeader STEP（胶条朝正面，与轴体底座穿模）
  2. 保留二极管自带的官方 DO-35 STEP（比自建模型精细）
  3. 按位号插入自建 WRL 模型（偏移已烘焙进几何，全部 (0,0,0) 挂载）
（不动打样原文件；渲染副本只多了 model 条目，不影响 Gerber/网表）

模型 → 封装 映射（KiCad 10 渲染对 WRL 的 (offset) 条目不生效 → 偏移烘进模型）：
  SW1..SW14   choc_v2.wrl
  JP1/JP2     header_pins_front.wrl + header_plastic_back.wrl
  JP1         promicro_at_JP1.wrl（已含 +7.62,+13.97,-2.5 偏移）
  PWR1        battery_at_PWR1.wrl（已含 +13,-2,0 偏移）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "pcb", "claudepad.kicad_pcb")
DST = os.path.join(ROOT, "pcb", "claudepad_render.kicad_pcb")
MODELS = os.path.join(ROOT, "cad", "models")

M = lambda name: os.path.join(MODELS, name).replace("\\", "/")

# ref 精确/前缀 → 模型路径列表（STEP 版本；偏移已烘焙进几何）
ATTACH_EXACT = {
    "JP1": [M("header_pins_front.step"), M("header_plastic_back.step"), M("promicro_at_JP1.step")],
    "PWR1": [M("battery_at_PWR1.step")],
}
ATTACH_PREFIX = {
    "SW": [M("choc_v2.step")],
    "JP": [M("header_pins_front.step"), M("header_plastic_back.step")],
}
PATTERN = re.compile(r"^(SW\d+|JP\d+)$")


def models_for(ref):
    if ref in ATTACH_EXACT:
        return ATTACH_EXACT[ref]
    for prefix, items in ATTACH_PREFIX.items():
        if ref.startswith(prefix) and PATTERN.match(ref):
            return items
    return []


def strip_official_header_models(block):
    """删除 footprint 块内引用 PinHeader 官方 STEP 的 (model ...) 块（配平括号扫描）"""
    out, i, removed = [], 0, 0
    while i < len(block):
        if block.startswith("(model ", i):
            j, d = i, 0
            while j < len(block):
                if block[j] == "(":
                    d += 1
                elif block[j] == ")":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            seg = block[i:j + 1]
            if "PinHeader" not in seg:
                out.append(seg)
            else:
                removed += 1
            i = j + 1
            continue
        out.append(block[i])
        i += 1
    return "".join(out), removed


def main():
    text = open(SRC, encoding="utf-8").read()
    out, i, n, depth, added, stripped = [], 0, len(text), 0, 0, 0
    while i < n:
        if text.startswith("(footprint", i) and depth == 1:
            j, d = i, 0                       # 扫描整个 footprint 块
            while j < n:
                if text[j] == "(":
                    d += 1
                elif text[j] == ")":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            block = text[i:j + 1]
            block, k = strip_official_header_models(block)
            stripped += k
            mref = re.search(r'\(property "Reference" "([^"]+)"', block)
            if mref:
                extra = ""
                for path in models_for(mref.group(1)):
                    extra += (f'\n\t(model "{path}"\n'
                              f'\t\t(offset (xyz 0 0 0))\n'
                              f'\t\t(scale (xyz 1 1 1))\n'
                              f'\t\t(rotate (xyz 0 0 0)))\n')
                    added += 1
                # 插进 footprint 闭合括号之前（块尾是 "\n\t)"）
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
    open(DST, "w", encoding="utf-8", newline="\n").write("".join(out))
    print(f"OK -> {DST}（插入 {added} 个模型，剥掉官方排针模型 {stripped} 个）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

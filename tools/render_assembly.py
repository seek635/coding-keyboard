# -*- coding: utf-8 -*-
"""ClaudePad 焊接参考图生成器
--------------------------
从焊盘坐标数据渲染「焊好之后长什么样」的参考图（无外部依赖，纯 SVG）：
  1. 正面等轴测 3D 视图（PCB + 二极管 + 排针 + 轴体）
  2. 背面等轴测 3D 视图（主控 + 电池，左右镜像 = 从板底往上看）
  3. 正俯视标注图（位号 / 键名 / 二极管方向 / 飞线焊盘）

输出：docs/焊接参考图.html（单文件，浏览器直接打开）
      docs/img/焊接参考-{正面,背面,俯视}.svg（内嵌展示用）

重跑命令（数据改动后）：
  C:\\Users\\尚\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/render_assembly.py

数据来源（★ 本文件不写死任何坐标，全部读生成物 —— 改坐标请改源头）：
  轴体/二极管  <- pcb/placement.csv       （tools/gen_pcb.py 生成）
  主控/排针    <- cad/lib/params.scad     （NANO_* / NANO_PIN_*）
  飞线焊盘     <- pcb/claudepad.kicad_pcb （取 RST1/GND1/RGB1/PWR1/PWR2/LEV1/LEV2 的真实坐标）
  板框/缺口    <- cad/lib/params.scad §4

★ 2026-10-11（用户第二次改板）：原先这里写死了一整份坐标副本（板宽 98、JP 80.97/96.21、
  NANO 79.70、空格 31/49/67…）。改板后它继续画**旧板子** —— 正是本项目的老教训
  「展示层会自信地展示错误信息」。已全部改为读生成物；同时修掉俯视图只按 180° 镜像、
  把 STOP(270°)/ENTER(90°) 的孔画错位置的 bug。
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from scad_params import load as load_params        # noqa: E402

P = load_params()
BOARD = os.path.join(ROOT, "pcb", "claudepad.kicad_pcb")
PLACEMENT = os.path.join(ROOT, "pcb", "placement.csv")

C = math.cos(math.radians(30.0))
S = 0.5


# ---------------- 数据（全部来自生成物） ----------------
def _load_placement():
    """读 pcb/placement.csv → (轴体, 二极管)。轴体=(键名,x,y,旋转°)，二极管=(位号,x,y,键名)"""
    sw, dio, section = [], [], None
    with open(PLACEMENT, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("ref,type,label,"):
                section = "sw"
                continue
            if line.startswith("ref,type,matrix,"):
                section = "dio"
                continue
            p = line.split(",")
            if section == "sw" and p[1] == "switch":
                sw.append((p[2], float(p[4]), float(p[5]), float(p[8] or 0)))
            elif section == "dio" and p[1] == "diode":
                dio.append((p[0], float(p[3]), float(p[4]), p[7] if len(p) > 7 else ""))
    return sw, dio


def _load_board_items():
    """读 pcb/claudepad.kicad_pcb，返回 {位号: (x_doc, y_doc, 旋转)}"""
    text = open(BOARD, encoding="utf-8").read()
    items, i, n = {}, 0, len(text)
    while True:
        i = text.find("(footprint", i)
        if i < 0:
            break
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
        mref = re.search(r'\(property "Reference" "([^"]+)"', block)
        mat = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", block)
        if mref and mat:
            items[mref.group(1)] = (float(mat.group(1)),
                                    P["PCB_H"] - float(mat.group(2)),
                                    float(mat.group(3) or 0))
        i = j + 1
    return items


PCB_W, PCB_H, PCB_T = P["PCB_W"], P["PCB_H"], P["PCB_T"]
NOTCH = (PCB_W - P["PCB_NOTCH_D"], P["PCB_NOTCH_Y0"], PCB_W, P["PCB_NOTCH_Y1"])

SWITCHES, DIODES = _load_placement()
_ITEMS = _load_board_items()

# 飞线焊盘（坐标取板文件真值；label_side: L=文字在左 R=在右）
PADS = [(ref, _ITEMS[ref][0], _ITEMS[ref][1], side)
        for ref, side in (("LEV1", "R"), ("LEV2", "R"), ("RST1", "L"), ("GND1", "L"),
                          ("RGB1", "L"), ("PWR1", "R"), ("PWR2", "R"))
        if ref in _ITEMS]

# 排针两列 / 最低孔 y / 每列孔数 —— 全部由 params 推导
JP_XS = (_ITEMS["JP1"][0], _ITEMS["JP2"][0])
JP_N = int(P["NANO_PIN_COUNT"])
JP_PITCH = float(P["NANO_PIN_PITCH"])
JP_Y0 = P["NANO_POS_Y"] + (P["NANO_L"] - P["NANO_PIN_SPAN"]) / 2.0
NANO = (P["NANO_POS_X"], P["NANO_POS_Y"],
        P["NANO_POS_X"] + P["NANO_W"], P["NANO_POS_Y"] + P["NANO_L"])
BATT = (0.0, (PCB_H - P["BATT_L"]) / 2.0, P["BATT_W"], (PCB_H + P["BATT_L"]) / 2.0)

# 板框多边形（含缺口），顺时针
BOARD_POLY = [(0, 0), (NOTCH[0], 0), (NOTCH[0], NOTCH[3]),
              (PCB_W, NOTCH[3]), (PCB_W, PCB_H), (0, PCB_H)]

# ---------------- 颜色工具 ----------------
def _dk(hexcol, f):
    r, g, b = int(hexcol[1:3], 16), int(hexcol[3:5], 16), int(hexcol[5:7], 16)
    return "#%02x%02x%02x" % (round(r * f), round(g * f), round(b * f))

# ---------------- 等轴测投影 ----------------
def iso_pt(x, y, z, ox, oy, sc, mirror=False):
    """等轴测投影：屏幕 y 向下为正，z 越高屏幕位置越靠上"""
    m = -1.0 if mirror else 1.0
    return (ox + m * (x - y) * C * sc, oy + ((x + y) * S - z) * sc)

def _poly_attr(pts):
    return " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)

def iso_box(out, x0, y0, z0, x1, y1, z1, col, ox, oy, sc, mirror=False, stroke="#00000022"):
    """画一个长方体的三个可见面：顶面 / x=x1 面 / y=y1 面"""
    P = lambda x, y, z: iso_pt(x, y, z, ox, oy, sc, mirror)
    top = [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)]
    xf = [P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)]
    yf = [P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)]
    out.append(f'<polygon points="{_poly_attr(yf)}" fill="{_dk(col,0.60)}" stroke="{stroke}"/>')
    out.append(f'<polygon points="{_poly_attr(xf)}" fill="{_dk(col,0.82)}" stroke="{stroke}"/>')
    out.append(f'<polygon points="{_poly_attr(top)}" fill="{col}" stroke="{stroke}"/>')

def iso_circle(out, cx, cy, z, r, col, ox, oy, sc, mirror=False, stroke="#00000033"):
    """z 平面上的圆（等轴测下为椭圆多边形）"""
    pts = []
    for i in range(28):
        t = 2 * math.pi * i / 28
        pts.append(iso_pt(cx + r * math.cos(t), cy + r * math.sin(t), z, ox, oy, sc, mirror))
    out.append(f'<polygon points="{_poly_attr(pts)}" fill="{col}" stroke="{stroke}"/>')

def iso_board(out, ox, oy, sc, mirror=False, z0=0.0, z1=PCB_T, col="#2f7d4a"):
    """PCB 板：z0~z1 一块板，先画侧面（按远近排序），再画顶面"""
    P = lambda x, y, z: iso_pt(x, y, z, ox, oy, sc, mirror)
    n = len(BOARD_POLY)
    faces = []
    for i in range(n):
        a, b = BOARD_POLY[i], BOARD_POLY[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ey) or 1.0
        nx, ny = ey / ln, -ex / ln            # 顺时针多边形外法线
        lit = 0.30 + 0.55 * max(0.0, nx * 0.85 + ny * 0.5)
        faces.append((a[0] + a[1] + b[0] + b[1], a, b, lit))
    for _, a, b, lit in sorted(faces, key=lambda f: f[0]):
        quad = [P(a[0], a[1], z0), P(b[0], b[1], z0), P(b[0], b[1], z1), P(a[0], a[1], z1)]
        out.append(f'<polygon points="{_poly_attr(quad)}" fill="{_dk(col,lit)}" stroke="#00000033"/>')
    top = [P(x, y, z1) for x, y in BOARD_POLY]
    out.append(f'<polygon points="{_poly_attr(top)}" fill="{col}" stroke="#00000055"/>')

def iso_switch(out, x, y, label, ox, oy, sc, mirror=False):
    z0 = PCB_T
    iso_box(out, x - 6.98, y - 6.98, z0, x + 6.98, y + 6.98, z0 + 5.3, "#3c3c46", ox, oy, sc, mirror)
    iso_box(out, x - 4.0, y - 4.0, z0 + 5.3, x + 4.0, y + 4.0, z0 + 7.2, "#55555f", ox, oy, sc, mirror)
    iso_circle(out, x, y, z0 + 7.25, 3.3, "#2e2e36", ox, oy, sc, mirror)
    tx, ty = iso_pt(x, y, z0 + 10.5, ox, oy, sc, mirror)
    out.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="11" '
               f'fill="#e8e8e8" font-family="sans-serif">{label}</text>')

def iso_diode(out, x, y, ref, ox, oy, sc, mirror=False):
    z0 = PCB_T + 0.5
    iso_box(out, x - 3.5, y - 0.95, z0, x + 3.5, y + 0.95, z0 + 1.9, "#c8862a", ox, oy, sc, mirror)
    # 色环（阴极）在 x 小的一端
    iso_box(out, x - 3.55, y - 1.00, z0 - 0.02, x - 2.30, y + 1.00, z0 + 1.94, "#222226", ox, oy, sc, mirror)

def iso_header(out, colx, ox, oy, sc, mirror=False):
    # 只画针脚：黑胶条若贴正面会顶到 STOP/ENTER2/VOICE 轴座（13.95 底座 x 78.0~92.0
    # 与胶条 x 79.7~82.24 重叠），装配时针从背面插或剪去胶条
    z = PCB_T
    for k in range(JP_N):
        py = JP_Y0 + k * JP_PITCH
        iso_box(out, colx - 0.35, py - 0.35, z, colx + 0.35, py + 0.35, z + 3.6, "#d4af37", ox, oy, sc, mirror)

def render_iso(mirror=False, show_back=False):
    sc = 7.6
    ox = 400 if not mirror else 776.5
    oy = 150
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 780" font-family="sans-serif">',
           '<rect width="1240" height="780" fill="#14161a"/>']
    iso_board(out, ox, oy, sc, mirror, z0=-PCB_T if show_back else 0.0, z1=0.0 if show_back else PCB_T)
    if not show_back:
        parts = []
        for label, x, y, _ in SWITCHES:
            parts.append((x + y, lambda l=label, xx=x, yy=y: iso_switch(out, xx, yy, l, ox, oy, sc, mirror)))
        for colx in JP_XS:
            parts.append((colx + 29, lambda cx=colx: iso_header(out, cx, ox, oy, sc, mirror)))
        for _, x, y, _ in DIODES:
            parts.append((x + y, lambda xx=x, yy=y: iso_diode(out, xx, yy, "", ox, oy, sc, mirror)))
        for _, key in sorted(parts, key=lambda p: p[0]):
            key()
        out.append('<text x="40" y="40" font-size="15" fill="#9fd6ae">正面视图（焊接面朝上）</text>')
        out.append('<text x="40" y="62" font-size="12" fill="#8b93a3">绿色板 · 琥珀色=二极管（黑环朝左） · 金针=排针脚 · 深灰方块=轴体</text>')
    else:
        def back_box(x0, y0, x1, y1, h, col):
            iso_box(out, x0, y0, 0.0, x1, y1, h, col, ox, oy, sc, True)
        back_box(*NANO, 3.2, "#1e3a5f")
        # USB-C 在主控**短边（文档 +y，外壳上壁）**，不是右壁
        back_box(NANO[0] + 4.5, NANO[3], NANO[0] + 13.5, NANO[3] + 2.4, 2.6, "#b9bec6")
        back_box(*BATT, 4.0, "#c0c4c8")
        tx, ty = iso_pt((NANO[0] + NANO[2]) / 2, (NANO[1] + NANO[3]) / 2, 6.5, ox, oy, sc, True)
        out.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="12" fill="#cfe3ff">主控 NoLogo NRF52840（元件面朝下）</text>')
        tx, ty = iso_pt((BATT[0] + BATT[2]) / 2, (BATT[1] + BATT[3]) / 2, 7.3, ox, oy, sc, True)
        out.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="12" fill="#f2f3f5">电池（示意）</text>')
        tx, ty = iso_pt(NANO[2] + 4, 30.5, 1.2, ox, oy, sc, True)
        out.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="11" fill="#f2f3f5">USB-C 朝上壁（短边）</text>')
        out.append(f'<text x="80" y="40" font-size="15" fill="#9fc4e8">背面视图（左右已镜像 = 从板底往上看）</text>')
        out.append(f'<text x="80" y="62" font-size="12" fill="#8b93a3">主控套在 {2 * JP_N} 根排针脚上再焊 · 电池红线→电源开关→B+，黑线→B-</text>')
    out.append("</svg>")
    return "\n".join(out)

# ---------------- 俯视标注图 ----------------
def render_top():
    sc, mg = 8.6, 55
    W, H = int(PCB_W * sc + mg * 2), int(PCB_H * sc + mg * 2)
    X = lambda x: mg + x * sc
    Y = lambda y: mg + (PCB_H - y) * sc          # y 向上 → 屏幕 y 向下
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#14161a"/>']
    poly = " ".join(f"{X(x):.0f},{Y(y):.0f}" for x, y in BOARD_POLY)
    out.append(f'<polygon points="{poly}" fill="#2f7d4a" stroke="#6fae86" stroke-width="2"/>')
    # 轴体（孔位按真实旋转角算 —— 原先只做 180° 镜像，STOP/ENTER 转过的角度会画错）
    PIN_OFFSETS = ((-3.80, 4.93), (-5.90, 0.00), (5.15, -5.00))   # Choc V2：2 电气 + 1 定位
    for label, x, y, rot in SWITCHES:
        out.append(f'<rect x="{X(x-7.5):.0f}" y="{Y(y+7.5):.0f}" width="{15*sc:.0f}" height="{15*sc:.0f}" '
                   f'rx="4" fill="#33333d" stroke="#5a5a68"/>')
        out.append(f'<text x="{X(x):.0f}" y="{Y(y)+4:.0f}" text-anchor="middle" font-size="12" fill="#fff">{label}</text>')
        out.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{2.5*sc:.1f}" fill="#1b1b20" '
                   f'stroke="#6b6b78" stroke-width="1"/>')          # 中心孔 Ø5（NPTH）
        th = math.radians(rot)
        ct, st = math.cos(th), math.sin(th)
        for dx, dy in PIN_OFFSETS:
            hx, hy = x + dx * ct - dy * st, y + dx * st + dy * ct
            anchor = (dx, dy) == (5.15, -5.0)
            out.append(f'<circle cx="{X(hx):.1f}" cy="{Y(hy):.1f}" r="{0.8*sc:.1f}" '
                       f'fill="{"none" if anchor else "#d4af37"}" stroke="#d4af37" stroke-width="1.2"/>')
    # 二极管（位号印在管身里，色环=左端深色块）
    for ref, x, y, key in DIODES:
        out.append(f'<rect x="{X(x-4):.1f}" y="{Y(y+1.3):.1f}" width="{8*sc:.1f}" height="{2.6*sc:.1f}" '
                   f'rx="2" fill="#c8862a" stroke="#e8b96a"/>')
        out.append(f'<rect x="{X(x-4):.1f}" y="{Y(y+1.3):.1f}" width="{1.4*sc:.1f}" height="{2.6*sc:.1f}" fill="#1c1c20"/>')
        out.append(f'<text x="{X(x):.0f}" y="{Y(y)+4:.0f}" text-anchor="middle" font-size="10" fill="#1c1c20">{ref}</text>')
    # 排针区（标签放板上缘外，避免压住轴体方块）
    for i, colx in enumerate(JP_XS):
        y_hi = JP_Y0 + (JP_N - 1) * JP_PITCH
        out.append(f'<rect x="{X(colx-1.27):.1f}" y="{Y(y_hi):.1f}" width="{2.54*sc:.1f}" '
                   f'height="{(y_hi-JP_Y0)*sc:.1f}" fill="#17171a" stroke="#3c3c46"/>')
        out.append(f'<text x="{X(colx):.0f}" y="48" text-anchor="middle" font-size="11" fill="#9fd6ae">JP{i+1} ×{JP_N} 针 ↓</text>')
    # 飞线焊盘
    for name, x, y, side in PADS:
        out.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{0.75*sc:.1f}" fill="#d4af37" stroke="#fff" stroke-width="0.8"/>')
        lx = X(x) + 9 if side == "R" else X(x) - 9
        anchor = "start" if side == "R" else "end"
        out.append(f'<text x="{lx:.0f}" y="{Y(y)+4:.0f}" text-anchor="{anchor}" font-size="10" fill="#ffe9b0">{name}</text>')
    # 缺口标注
    out.append(f'<text x="{X(94):.0f}" y="{Y(6)+4:.0f}" text-anchor="middle" font-size="10" fill="#ff9d9d">缺口</text>')
    out.append(f'<text x="{X(94):.0f}" y="{Y(6)+18:.0f}" text-anchor="middle" font-size="9" fill="#d98a8a">拨杆让位</text>')
    # 方向注释
    out.append(f'<text x="{mg}" y="28" font-size="13" fill="#9fd6ae">↑ 上=SPACE 排 · 下=行1（PERM…STOP） · 右=USB/缺口（与 KiCad 屏幕方向一致）</text>')
    out.append(f'<text x="{mg}" y="{H-16}" font-size="13" fill="#ffd98a">← 所有二极管色环端（阴极 K→ROW）一律朝左（x 小的一侧）</text>')
    out.append("</svg>")
    return "\n".join(out)

# ---------------- 输出 HTML ----------------
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    img_dir = os.path.join(root, "docs", "img")
    os.makedirs(img_dir, exist_ok=True)
    svgs = {"front": render_iso(False), "back": render_iso(True, True), "top": render_top()}
    for name, svg in svgs.items():
        with open(os.path.join(img_dir, f"焊接参考-{ {'front':'正面','back':'背面','top':'俯视'}[name] }.svg"),
                  "w", encoding="utf-8") as f:
            f.write(svg)
    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>ClaudePad 焊接参考图</title>
<style>
 body{{background:#0e1013;color:#d7dae0;font-family:"Microsoft YaHei",sans-serif;margin:0;padding:24px}}
 h1{{font-size:22px}} h2{{font-size:17px;margin:34px 0 8px;color:#9fd6ae}}
 figure{{margin:8px 0 0}} svg{{max-width:100%;height:auto;border-radius:10px;background:#14161a}}
 .tip{{background:#1a1f27;border-left:4px solid #d4af37;padding:10px 14px;border-radius:6px;font-size:14px;line-height:1.7}}
 ol{{line-height:1.9}} code{{background:#22262e;padding:1px 6px;border-radius:4px}}
</style></head><body>
<h1>ClaudePad 焊接参考图</h1>
<p class="tip">由 <code>tools/render_assembly.py</code> 生成，坐标与 PCB 同源（placement.csv / netlist.json）。
<strong>焊接顺序：① 二极管 → ② 排针 → ③ 飞线 → ④ 轴体 → ⑤ 拨杆</strong>，配合 <code>docs/焊接指南.md</code> 使用。</p>

<h2>一、焊完正面长这样（等轴测）</h2>
<figure>{svgs["front"]}</figure>

<h2>二、翻过来背面长这样</h2>
<figure>{svgs["back"]}</figure>

<h2>三、俯视标注图（对照焊接用这张）</h2>
<figure>{svgs["top"]}</figure>

<p class="tip">极性铁律：二极管色环端 = 阴极（K）= 朝轴体那侧（MID 网络）；插反不烧板，但按键读不出来。
14 颗轴体都是完整 4 孔（2026-10-11 起，不再有省孔/剪脚）。
焊完先别接电池，按指南 §2 用万用表通断档检查。</p>
</body></html>"""
    out_path = os.path.join(root, "docs", "焊接参考图.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK ->", out_path)

if __name__ == "__main__":
    main()

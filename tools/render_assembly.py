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

数据来源（勿在本文件里"改坐标"，改源头）：
  轴体/二极管  <- pcb/placement.csv      （tools/gen_pcb.py 生成）
  排针/主控    <- tools/gen_kicad.py 头注释（y[12.5,45.5]，孔 y 15.03~42.97）
  板框/缺口    <- cad/lib/params.scad §4
"""
import math
import os

C = math.cos(math.radians(30.0))
S = 0.5

# ---------------- 数据（与 placement.csv / gen_kicad.py 同源） ----------------
PCB_W, PCB_H, PCB_T = 98.0, 50.0, 1.6
NOTCH = (90.0, 0.0, 98.0, 12.0)          # 右缘缺口 x[90,98] y[0,12]（拨杆让位）

# (键名, x, y, 旋转°)  文档坐标系：原点=板左下角，y 向上
SWITCHES = [
    ("PERM", 13, 7, 0), ("UP", 31, 7, 0), ("MODEL", 49, 7, 0), ("CMD", 67, 7, 0), ("STOP", 85, 7, 0),
    ("LEFT", 13, 25, 0), ("DOWN", 31, 25, 0), ("RIGHT", 49, 25, 0), ("ENTER", 67, 25, 0), ("ENTER", 85, 25, 180),
    ("SPACE", 13, 43, 0), ("SPACE", 40, 43, 0), ("SPACE", 67, 43, 0), ("VOICE", 85, 43, 180),
]
# (位号, x, y, 键名)  色环端（阴极→ROW）一律朝 x 小的一侧
DIODES = [
    ("D1", 6.00, 16.00, "PERM"), ("D2", 16.50, 16.00, "UP"), ("D3", 27.00, 16.00, "MODEL"),
    ("D4", 47.26, 16.00, "CMD"), ("D5", 57.58, 16.00, "STOP"), ("D6", 67.90, 16.00, "APPROVE"),
    ("D7", 6.00, 34.00, "LEFT"), ("D8", 16.50, 34.00, "DOWN"), ("D9", 27.00, 34.00, "RIGHT"),
    ("D10", 57.58, 34.00, "ENTER"), ("D11", 47.26, 34.00, "SPACE"), ("D12", 67.90, 34.00, "VOICE"),
]
# 飞线焊盘（与 tools/gen_kicad.py PAD_* 常量一致；label_side: L=文字在左 R=在右）
PADS = [("LEV1", 89, 16.5, "R"), ("LEV2", 85.5, 15.8, "R"), ("RST1", 74, 17, "L"),
        ("GND1", 78, 17, "L"), ("RGB1", 76, 22, "L"), ("PWR1", 3, 23, "R"), ("PWR2", 3, 27, "R")]
JP_XS = (80.97, 96.21)                    # 排针两列 x
JP_Y0, JP_N, JP_PITCH = 15.03, 12, 2.54   # 首孔 y / 每列孔数 / 孔距
NANO = (79.70, 12.50, 97.48, 45.50)       # 主控（背面）x0,y0,x1,y1
BATT = (1.0, 5.0, 31.0, 45.0)             # 电池（背面，示意）

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
        back_box(96.4, 26, 98.3, 35, 2.6, "#b9bec6")                     # USB-C
        back_box(*BATT, 4.0, "#c0c4c8")
        tx, ty = iso_pt((NANO[0] + NANO[2]) / 2, (NANO[1] + NANO[3]) / 2, 6.5, ox, oy, sc, True)
        out.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="12" fill="#cfe3ff">主控 NoLogo NRF52840（元件面朝下）</text>')
        tx, ty = iso_pt((BATT[0] + BATT[2]) / 2, (BATT[1] + BATT[3]) / 2, 7.3, ox, oy, sc, True)
        out.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="12" fill="#f2f3f5">电池（示意）</text>')
        tx, ty = iso_pt(NANO[2] + 4, 30.5, 1.2, ox, oy, sc, True)
        out.append(f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="11" fill="#f2f3f5">USB-C 朝右壁</text>')
        out.append(f'<text x="80" y="40" font-size="15" fill="#9fc4e8">背面视图（左右已镜像 = 从板底往上看）</text>')
        out.append(f'<text x="80" y="62" font-size="12" fill="#8b93a3">主控套在 24 根排针脚上再焊 · 电池红线→电源开关→B+，黑线→B-</text>')
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
    # 轴体
    for label, x, y, rot in SWITCHES:
        fx = -1 if rot == 180 else 1
        out.append(f'<rect x="{X(x-7.5):.0f}" y="{Y(y+7.5):.0f}" width="{15*sc:.0f}" height="{15*sc:.0f}" '
                   f'rx="4" fill="#33333d" stroke="#5a5a68"/>')
        out.append(f'<text x="{X(x):.0f}" y="{Y(y)+4:.0f}" text-anchor="middle" font-size="12" fill="#fff">{label}</text>')
        for dx, dy in ((-3.8, 4.93), (-5.9, 0.0), (5.15, -5.0)):
            hx, hy = X(x + fx * dx), Y(y + fx * dy)
            anchor = (dx, dy) == (5.15, -5.0)
            out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{0.8*sc:.1f}" fill="{"none" if anchor else "#d4af37"}" '
                       f'stroke="#d4af37" stroke-width="1.2"/>')
    # 二极管（位号印在管身里，色环=左端深色块）
    for ref, x, y, key in DIODES:
        out.append(f'<rect x="{X(x-4):.1f}" y="{Y(y+1.3):.1f}" width="{8*sc:.1f}" height="{2.6*sc:.1f}" '
                   f'rx="2" fill="#c8862a" stroke="#e8b96a"/>')
        out.append(f'<rect x="{X(x-4):.1f}" y="{Y(y+1.3):.1f}" width="{1.4*sc:.1f}" height="{2.6*sc:.1f}" fill="#1c1c20"/>')
        out.append(f'<text x="{X(x):.0f}" y="{Y(y)+4:.0f}" text-anchor="middle" font-size="10" fill="#1c1c20">{ref}</text>')
    # 排针区（标签放板上缘外，避免压住轴体方块）
    for i, colx in enumerate(JP_XS):
        out.append(f'<rect x="{X(colx-1.27):.1f}" y="{Y(43.5):.1f}" width="{2.54*sc:.1f}" height="{29.5*sc:.1f}" '
                   f'fill="#17171a" stroke="#3c3c46"/>')
        out.append(f'<text x="{X(colx):.0f}" y="48" text-anchor="middle" font-size="11" fill="#9fd6ae">JP{i+1} ×12 针 ↓</text>')
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

<p class="tip">极性铁律：二极管色环端 = 阴极（K）= 接 ROW；插反不烧板，但按键读不出来。
两个轴（STOP、ENTER 第二轴）没有小定位孔属正常设计。焊完先别接电池，按指南 §2 用万用表通断档检查。</p>
</body></html>"""
    out_path = os.path.join(root, "docs", "焊接参考图.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK ->", out_path)

if __name__ == "__main__":
    main()

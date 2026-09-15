#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极简 2D 绘图画布（SVG + PNG 双后端）
================================================================================
一份布局描述，两个渲染后端，保证矢量图和位图内容完全一致。

用法：
    from canvas import Canvas, render_svg, render_png
    c = Canvas(800, 600)
    c.rect(10, 10, 100, 50, fill="#eee", stroke="#333")
    c.text(60, 40, "你好", 14, anchor="middle")
    open("out.svg","w").write(render_svg(c))
    render_png(c, "out.png")

只支持矩形 / 直线 / 多边形 / 文字 —— 够画工程示意图了。
"""

import os

C_TEXT = "#111827"
C_MUTED = "#6b7280"


class Canvas:
    def __init__(self, w, h, bg="#ffffff"):
        self.w, self.h, self.bg = w, h, bg
        self.ops = []

    def rect(self, x, y, w, h, fill="none", stroke="none", sw=1, rx=0):
        self.ops.append(("rect", x, y, w, h, fill, stroke, sw, rx))

    def line(self, x1, y1, x2, y2, color, sw=1, dash=None):
        self.ops.append(("line", x1, y1, x2, y2, color, sw, dash))

    def poly(self, pts, fill="none", stroke="none", sw=1):
        self.ops.append(("poly", pts, fill, stroke, sw))

    def text(self, x, y, s, size=13, color=C_TEXT, anchor="start", bold=False):
        self.ops.append(("text", x, y, s, size, color, anchor, bold))

    def arrow(self, x1, y1, x2, y2, color, sw=1.5):
        """带箭头的直线（用两段短线做箭头）"""
        self.line(x1, y1, x2, y2, color, sw)
        import math
        a = math.atan2(y2 - y1, x2 - x1)
        L = 7
        for d in (math.radians(155), math.radians(-155)):
            self.line(x2, y2, x2 + L * math.cos(a + d), y2 + L * math.sin(a + d), color, sw)


# ------------------------------ SVG 后端 ------------------------------------
def render_svg(c: Canvas) -> str:
    A = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {c.w} {c.h}" '
         f'width="{c.w}" height="{c.h}" '
         f'font-family="-apple-system, Segoe UI, Microsoft YaHei, sans-serif">',
         f'<rect width="100%" height="100%" fill="{c.bg}"/>']
    for op in c.ops:
        k = op[0]
        if k == "rect":
            _, x, y, w, h, fill, stroke, sw, rx = op
            A.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        elif k == "line":
            _, x1, y1, x2, y2, col, sw, dash = op
            d = f' stroke-dasharray="{dash}"' if dash else ""
            A.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{col}" stroke-width="{sw}"{d}/>')
        elif k == "poly":
            _, pts, fill, stroke, sw = op
            p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            A.append(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        elif k == "text":
            _, x, y, s, size, col, anchor, bold = op
            fw = ' font-weight="600"' if bold else ""
            esc = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            A.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{col}" '
                     f'text-anchor="{anchor}"{fw}>{esc}</text>')
    A.append("</svg>")
    return "\n".join(A)


# ------------------------------ PNG 后端 ------------------------------------
_FONT_CACHE = {}


def _load_font(size, bold=False):
    from PIL import ImageFont
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    cands = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]
    f = None
    for p in cands:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                break
            except Exception:
                continue
    if f is None:
        f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def render_png(c: Canvas, path: str, scale: int = 2) -> str:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (c.w * scale, c.h * scale), c.bg)
    d = ImageDraw.Draw(img)

    def S(v):
        return v * scale

    for op in c.ops:
        k = op[0]
        if k == "rect":
            _, x, y, w, h, fill, stroke, sw, rx = op
            box = [S(x), S(y), S(x + w), S(y + h)]
            if fill != "none":
                d.rounded_rectangle(box, radius=S(rx), fill=fill)
            if stroke != "none":
                d.rounded_rectangle(box, radius=S(rx), outline=stroke,
                                    width=max(1, int(S(sw))))
        elif k == "line":
            _, x1, y1, x2, y2, col, sw, dash = op
            d.line([S(x1), S(y1), S(x2), S(y2)], fill=col, width=max(1, int(S(sw))))
        elif k == "poly":
            _, pts, fill, stroke, sw = op
            p = [(S(x), S(y)) for x, y in pts]
            if fill != "none":
                d.polygon(p, fill=fill)
            if stroke != "none":
                d.line(p + [p[0]], fill=stroke, width=max(1, int(S(sw))))
        elif k == "text":
            _, x, y, s, size, col, anchor, bold = op
            f = _load_font(int(S(size)), bold)
            try:
                bb = d.textbbox((0, 0), s, font=f)
                tw, th = bb[2] - bb[0], bb[3] - bb[1]
            except Exception:
                tw, th = len(s) * size * 0.6, size
            ax = S(x) - (tw / 2 if anchor == "middle" else (tw if anchor == "end" else 0))
            d.text((ax, S(y) - th * 0.85), s, font=f, fill=col)

    img.save(path)
    return path

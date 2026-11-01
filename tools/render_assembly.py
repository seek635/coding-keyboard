#!/usr/bin/env python3
"""Render annotated 3D "after soldering" guide images for ClaudePad.

No CAD kernel is required: the board / case / plate / keycaps come from the
existing STLs in ``pcb/output/3d`` and ``cad/output/stl``, and the switches,
diodes, XIAO module, headers, JST and battery wires are generated
procedurally from the same dimensions used by ``pcb/generate_pcb.py`` and
``cad/params.scad``.

The scene is rasterised with a small numpy z-buffer renderer (flat shading +
super sampling + silhouette/depth edge lines) and then annotated with Pillow
using a CJK font.

Run:
    python tools/render_assembly.py
Outputs (docs/3d/):
    guide-front-iso.png     soldered top, 3/4 view
    guide-top.png           soldered top, orthographic map
    guide-bottom-iso.png    soldered bottom, 3/4 view (diodes)
    guide-assembled.png     plate + keycaps + case, 3/4 view
    guide-exploded.png      exploded layer stack
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "3d"
OUT.mkdir(parents=True, exist_ok=True)

FONT_CJK = r"C:\Windows\Fonts\msyh.ttc"
FONT_CJK_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

# ---------------------------------------------------------------------------
# Board frame: PCB bottom z = 0, top z = 1.6 (same XY as the KiCad board)
# ---------------------------------------------------------------------------
Z_BOT, Z_TOP = 0.0, 1.6
KEY_X = [18.0, 36.0, 54.0, 72.0, 90.0]
KEY_Y = [30.5, 47.5, 64.5]
SWITCHES = [
    (18.0, 30.5), (36.0, 30.5), (54.0, 30.5), (72.0, 30.5), (90.0, 30.5),
    (18.0, 47.5), (54.0, 47.5), (72.0, 47.5), (90.0, 47.5),
    (18.0, 64.5), (36.0, 64.5), (54.0, 64.5), (72.0, 64.5), (90.0, 64.5),
]
KEYCAPS = [
    (18.0, 30.5, 1, "PERM"), (36.0, 30.5, 1, "MODEL"), (54.0, 30.5, 1, "CMD"),
    (72.0, 30.5, 1, "UP"), (90.0, 30.5, 1, "VOICE"),
    (18.0, 47.5, 1, "STOP"), (54.0, 47.5, 1, "LEFT"), (72.0, 47.5, 1, "DOWN"),
    (90.0, 47.5, 1, "RIGHT"),
    (27.0, 64.5, 2, "ENTER"), (72.0, 64.5, 3, "SPACE"),
]
# (ref, x, y, row, rotation) -- same table as pcb/generate_pcb.py
DIODES = [
    ("D1", 18.0, 38.5, 0, 0), ("D2", 36.0, 38.5, 0, 0), ("D3", 54.0, 38.5, 0, 0),
    ("D4", 72.0, 38.5, 0, 0), ("D5", 90.0, 38.5, 0, 0),
    ("D6", 18.0, 55.5, 1, 0), ("D7", 54.0, 55.5, 1, 0), ("D8", 72.0, 55.5, 1, 0),
    ("D9", 90.0, 55.5, 1, 0),
    ("D10", 27.0, 74.5, 2, 180), ("D11", 63.0, 74.5, 2, 180),
]
XIAO = dict(cx=54.0, cy=12.0, w=17.8, d=21.0, h=3.2, header=2.5)
JST = dict(x=74.0, y=12.0, w=6.0, d=5.0, h=4.5)
BAT_PADS = [(70.0, 17.5), (70.0, 19.5)]
CABLE_SLOT = (83.5, 10.0, 87.5, 18.0)
# assembly z offsets (case bottom z = 0, PCB bottom sits at 7.0)
PCB_LIFT = 7.0
PLATE_TOP_Z = 14.8
CAP_BOT_Z = 18.1

# ---------------------------------------------------------------------------
# palette (RGB 0..1)
# ---------------------------------------------------------------------------
C_PCB = np.array([0.11, 0.30, 0.20])
C_PAD = np.array([0.82, 0.66, 0.26])
C_SW = np.array([0.17, 0.18, 0.19])
C_SW_DARK = np.array([0.10, 0.10, 0.11])
C_STEM = np.array([0.36, 0.37, 0.38])
C_METAL = np.array([0.62, 0.65, 0.68])
C_DIODE = np.array([0.14, 0.15, 0.18])
C_BAND = np.array([0.78, 0.80, 0.82])
C_JST = np.array([0.90, 0.87, 0.78])
C_XIAO = np.array([0.16, 0.18, 0.21])
C_PLATE = np.array([0.86, 0.82, 0.74])
C_CASE = np.array([0.17, 0.15, 0.13])
C_CAP_LIGHT = np.array([0.86, 0.82, 0.73])
C_CAP_DARK = np.array([0.22, 0.21, 0.21])
C_CAP_ACCENT = np.array([0.82, 0.44, 0.33])
C_WIRE_P = np.array([0.78, 0.16, 0.14])
C_WIRE_N = np.array([0.12, 0.12, 0.13])
C_GROUND = np.array([0.88, 0.86, 0.81])


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------
def load_stl(path: Path, _cache={}) -> np.ndarray:
    key = str(path)
    if key in _cache:
        return _cache[key].copy()
    data = path.read_bytes()
    if b"facet" in data[:600]:
        # ASCII STL (the KiCad 3D export is ASCII)
        import re
        verts = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)
        tri = np.array(verts, dtype="S24").astype(np.float64).reshape(-1, 3, 3)
    else:
        n = struct.unpack_from("<I", data, 80)[0]
        rec = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])
        tri = np.frombuffer(data, dtype=rec, count=n, offset=84)["v"].astype(np.float64)
    _cache[key] = tri
    return tri.copy()


def orient(tri: np.ndarray, centre) -> np.ndarray:
    """Flip triangles so their normal points away from ``centre``."""
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    c = tri.mean(axis=1)
    flip = ((c - np.asarray(centre, float)) * n).sum(axis=1) < 0
    tri = tri.copy()
    tri[flip] = tri[flip][:, [0, 2, 1]]
    return tri


def box(x0, y0, z0, x1, y1, z1) -> np.ndarray:
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7),
         (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
         (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]
    tri = np.array([[c[i] for i in face] for face in f], float)
    return orient(tri, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def cyl(p0, p1, r, seg=16, caps=True) -> np.ndarray:
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    axis = p1 - p0
    length = float(np.linalg.norm(axis))
    if length < 1e-9:
        return np.zeros((0, 3, 3))
    w = axis / length
    u = np.cross(w, [0.0, 0.0, 1.0])
    if np.linalg.norm(u) < 1e-6:
        u = np.cross(w, [0.0, 1.0, 0.0])
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    ring0 = p0 + np.outer(np.cos(ang), u) * r + np.outer(np.sin(ang), v) * r
    ring1 = p1 + np.outer(np.cos(ang), u) * r + np.outer(np.sin(ang), v) * r
    tris = []
    for i in range(seg):
        j = (i + 1) % seg
        tris.append([ring0[i], ring0[j], ring1[j]])
        tris.append([ring0[i], ring1[j], ring1[i]])
    if caps:
        for ring, centre in ((ring0, p0), (ring1, p1)):
            for i in range(seg):
                j = (i + 1) % seg
                tris.append([centre, ring[i], ring[j]])
    return orient(np.array(tris, float), (p0 + p1) / 2)


def tube(points, r, seg=10) -> np.ndarray:
    pts = [np.asarray(p, float) for p in points]
    parts = []
    for a, b in zip(pts[:-1], pts[1:]):
        parts.append(cyl(a, b, r, seg=seg))
    return np.concatenate(parts) if parts else np.zeros((0, 3, 3))


def disc(cx, cy, z, r, thick=0.10, seg=20) -> np.ndarray:
    return cyl((cx, cy, z - thick / 2), (cx, cy, z + thick / 2), r, seg=seg)


# ---------------------------------------------------------------------------
# scene parts
# ---------------------------------------------------------------------------
def pcb_mesh() -> np.ndarray:
    tri = load_stl(ROOT / "pcb" / "output" / "3d" / "claudepad-pcb.stl")
    # the STL was exported with a mirrored Y axis -> flip it back
    tri = tri[:, :, :].copy()
    tri[:, :, 1] *= -1.0
    tri = tri[:, [0, 2, 1]]                      # keep outward winding
    tri[:, :, 2] += 0.07                          # logical z 0 .. 1.6
    return tri


def ground_plane(z=-45.0, size=400.0) -> np.ndarray:
    x0 = 54 - size / 2
    y0 = 41 - size / 2
    return box(x0, y0, z - 1.0, x0 + size, y0 + size, z)


def pad_ring(cx, cy, r, side, net_color=None) -> np.ndarray:
    z = Z_TOP if side == "top" else Z_BOT
    thick = 0.12
    zc = z + thick / 2 if side == "top" else z - thick / 2
    return disc(cx, cy, zc, r, thick, seg=18)


def switch_mesh(cx, cy):
    parts = [
        box(cx - 7.25, cy - 7.25, Z_TOP + 0.35, cx + 7.25, cy + 7.25, Z_TOP + 4.9),
    ]
    # upper tower + MX-style stem
    parts.append(box(cx - 3.1, cy - 3.1, Z_TOP + 4.9, cx + 3.1, cy + 3.1, Z_TOP + 6.3))
    parts.append(box(cx - 2.3, cy - 0.58, Z_TOP + 6.3, cx + 2.3, cy + 0.58, Z_TOP + 9.4))
    parts.append(box(cx - 0.58, cy - 2.3, Z_TOP + 6.3, cx + 0.58, cy + 2.3, Z_TOP + 9.4))
    return np.concatenate(parts)


def xiao_mesh():
    cx, cy = XIAO["cx"], XIAO["cy"]
    x0, x1 = cx - XIAO["w"] / 2, cx + XIAO["w"] / 2
    y0, y1 = cy - XIAO["d"] / 2, cy + XIAO["d"] / 2
    z0 = Z_TOP + XIAO["header"]
    z1 = z0 + XIAO["h"]
    parts = [box(x0, y0, z0, x1, y1, z1)]
    # USB-C on the -Y edge
    parts.append(box(cx - 4.4, y0 - 1.5, z0 + 0.7, cx + 4.4, y0 + 0.2, z0 + 2.9))
    # reset button on top, near the -Y edge
    parts.append(box(cx + 2.6, y0 + 2.0, z1, cx + 5.2, y0 + 4.2, z1 + 0.55))
    # 2x7 pin headers under the module
    for sx in (cx - 7.62, cx + 7.62):
        parts.append(box(sx - 1.27, cy - 8.89, Z_TOP, sx + 1.27, cy + 8.89, z0))
    return np.concatenate(parts), (x0, x1, y0, y1, z0, z1)


def header_pins_bottom() -> np.ndarray:
    """Pin stubs sticking out under the PCB (trim to <= 4 mm!)."""
    cx, cy = XIAO["cx"], XIAO["cy"]
    parts = []
    for sx in (cx - 7.62, cx + 7.62):
        for i in range(7):
            y = cy - 7.62 + i * 2.54
            parts.append(cyl((sx, y, Z_BOT), (sx, y, Z_BOT - 2.6), 0.32, seg=10, caps=False))
    return np.concatenate(parts)


def jst_mesh():
    x, y = JST["x"], JST["y"]
    x0, x1 = x - JST["w"] / 2, x + JST["w"] / 2
    y0, y1 = y - JST["d"] / 2, y + JST["d"] / 2
    parts = [box(x0, y0, Z_TOP, x1, y1, Z_TOP + JST["h"])]
    # mating opening on +X
    parts.append(box(x1 - 0.8, y0 + 1.0, Z_TOP + 0.9, x1 + 0.12, y1 - 1.0, Z_TOP + 2.4))
    return np.concatenate(parts)


def diode_mesh(x, y, rot):
    zc = -1.15
    s = 1.0 if rot == 0 else -1.0
    parts = [cyl((x - 2.05, y, zc), (x + 2.05, y, zc), 0.95, seg=14)]
    # cathode band
    bx = x + s * 1.72
    parts.append(cyl((bx - 0.16, y, zc), (bx + 0.16, y, zc), 0.99, seg=14))
    # leads + vertical stubs into the pads at +-3.5
    for sx in (-3.5, 3.5):
        parts.append(cyl((x + sx, y, zc), (x + sx * 2.05 / 3.5, y, zc), 0.27, seg=8))
        parts.append(cyl((x + sx, y, zc), (x + sx, y, Z_BOT - 0.05), 0.27, seg=8))
    return np.concatenate(parts)


def caps_for_view(nozzle):
    return nozzle


# ---------------------------------------------------------------------------
# camera + renderer
# ---------------------------------------------------------------------------
class Camera:
    def __init__(self, pos, target, up=(0.0, 0.0, 1.0), fov=32.0,
                 ortho_scale=None, width=2000, height=1500):
        self.pos = np.asarray(pos, float)
        self.target = np.asarray(target, float)
        self.up = np.asarray(up, float)
        self.fov = fov
        self.ortho_scale = ortho_scale
        self.width = width
        self.height = height
        f = self.target - self.pos
        self.f = f / np.linalg.norm(f)
        r = np.cross(self.f, self.up)
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.r, self.f)
        self.fpx = (height / 2.0) / math.tan(math.radians(fov) / 2.0)

    def project(self, pts, ss=1):
        pts = np.atleast_2d(np.asarray(pts, float))
        v = pts - self.pos
        cx, cy, cz = v @ self.r, v @ self.u, v @ self.f
        if self.ortho_scale is not None:
            sx = cx * self.ortho_scale * ss + self.width * ss / 2
            sy = -cy * self.ortho_scale * ss + self.height * ss / 2
        else:
            fpx = self.fpx * ss
            sx = cx / cz * fpx + self.width * ss / 2
            sy = -cy / cz * fpx + self.height * ss / 2
        return sx, sy, cz


def background(w, h):
    top = np.array([0.965, 0.955, 0.935])
    bot = np.array([0.870, 0.885, 0.880])
    ramp = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(top * (1 - ramp) + bot * ramp, (h, w, 3)).astype(np.float64).copy()


def erode(mask, it=1):
    m = mask
    for _ in range(it):
        m = (m & np.roll(m, 1, 0) & np.roll(m, -1, 0)
             & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    return m


def render(cam: Camera, meshes, ss=2, lights=None, edge_color=0.42):
    """meshes: list of (triangles, rgb) tuples."""
    W, H = cam.width, cam.height
    w, h = W * ss, H * ss
    img = background(w, h)
    zbuf = np.full((h, w), 1e9)

    if lights is None:
        lights = [((0.35, -0.45, 0.82), 0.62), ((-0.55, -0.25, 0.35), 0.22)]
    lights = [(np.asarray(d, float) / np.linalg.norm(d), i) for d, i in lights]

    for tris, col in meshes:
        if len(tris) == 0:
            continue
        v = tris - cam.pos
        cx, cy, cz = v @ cam.r, v @ cam.u, v @ cam.f
        if cam.ortho_scale is not None:
            sx = cx * cam.ortho_scale * ss + w / 2
            sy = -cy * cam.ortho_scale * ss + h / 2
        else:
            fpx = cam.fpx * ss
            valid = cz > 0.05
            sx = np.full_like(cx, -1e9)
            sy = np.full_like(cy, -1e9)
            sx[valid] = cx[valid] / cz[valid] * fpx + w / 2
            sy[valid] = -cy[valid] / cz[valid] * fpx + h / 2
            cz = np.where(valid, cz, np.inf)
        # per-face normal & shading
        n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ln[ln == 0] = 1
        n = n / ln[:, None]
        shade = 0.34 + sum(inten * np.clip(n @ d, 0, None) for d, inten in lights)
        face_col = np.clip(col[None, :] * shade[:, None], 0, 1)
        # camera facing cull
        tv = tris.mean(axis=1) - cam.pos
        facing = (n * tv).sum(axis=1) < 0.0
        # projected backface cull (winding)
        area = ((sx[:, 1] - sx[:, 0]) * (sy[:, 2] - sy[:, 0])
                - (sx[:, 2] - sx[:, 0]) * (sy[:, 1] - sy[:, 0]))
        keep = np.nonzero(facing & (np.abs(area) > 1e-9))[0]
        for t in keep:
            xs, ys, zs = sx[t], sy[t], cz[t]
            x0, x1 = int(np.floor(xs.min())), int(np.ceil(xs.max()))
            y0, y1 = int(np.floor(ys.min())), int(np.ceil(ys.max()))
            if x1 < 0 or y1 < 0 or x0 >= w or y0 >= h:
                continue
            x0, x1 = max(x0, 0), min(x1, w - 1)
            y0, y1 = max(y0, 0), min(y1, h - 1)
            if x1 < x0 or y1 < y0:
                continue
            px = np.arange(x0, x1 + 1) + 0.5
            py = np.arange(y0, y1 + 1) + 0.5
            gx, gy = np.meshgrid(px, py)
            d = ((ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2]))
            if abs(d) < 1e-12:
                continue
            w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
            w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
            w2 = 1.0 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any():
                continue
            z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            subimg = img[y0:y1 + 1, x0:x1 + 1]
            hit = m & (z < sub)
            if not hit.any():
                continue
            sub[hit] = z[hit]
            subimg[hit] = face_col[t]

    # outline: silhouette + strong depth steps
    mask = zbuf < 1e8
    edge = mask & ~erode(mask, 1)
    zsafe = np.where(mask, zbuf, np.nan)
    dz = np.zeros_like(zbuf)
    for axis in (0, 1):
        a = np.roll(zsafe, 1, axis)
        b = np.roll(zsafe, -1, axis)
        dz = np.fmax(dz, np.fmax(np.abs(zsafe - a), np.abs(zsafe - b)))
    edges = edge | (mask & (np.nan_to_num(dz, nan=0.0) > 2.5))
    img[edges] *= edge_color

    arr = np.clip(img * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------------------
# annotation helpers
# ---------------------------------------------------------------------------
def font(size, bold=False):
    path = FONT_CJK_BOLD if bold else FONT_CJK
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(FONT_CJK, size)


def draw_callouts(img, cam, callouts, *, title, subtitle, fsize=30,
                  accent=(0.12, 0.12, 0.12)):
    """callouts: list of dict(anchor=xyz, text=str, xy=(px,py), align='left'|'right')"""
    draw = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    f_body = font(fsize)
    f_title = font(46, bold=True)
    f_sub = font(26)
    ink = (28, 28, 28)
    line_h = fsize + 10

    draw.text((46, 34), title, font=f_title, fill=ink)
    draw.text((48, 94), subtitle, font=f_sub, fill=(90, 90, 90))

    for c in callouts:
        ax, ay, _ = cam.project([c["anchor"]])
        ax, ay = float(ax[0]), float(ay[0])
        text = c["text"]
        lines = text.split("\n")
        tw = max(draw.textlength(ln, font=f_body) for ln in lines)
        th = (len(lines) - 1) * line_h
        pad = 14
        bx, by = c["xy"]
        align = c.get("align", "left")
        if align == "right":
            bx = bx - tw - 2 * pad
        box = (bx - pad, by - pad, bx + tw + pad, by + th + pad - 8)
        # leader line
        lx = box[0] if ax > box[2] else (box[2] if ax < box[0] else (box[0] + box[2]) / 2)
        ly = (box[1] + box[3]) / 2
        if box[0] <= ax <= box[2]:
            lx = (box[0] + box[2]) / 2
            ly = box[3] if ay > box[3] else box[1]
        draw.line([(lx, ly), (ax, ay)], fill=(120, 120, 120, 235), width=2)
        r = 6
        draw.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(200, 70, 50, 255),
                     outline=(255, 255, 255, 230))
        draw.rounded_rectangle(box, radius=12, fill=(255, 255, 255, 232),
                               outline=(150, 150, 150, 240), width=2)
        for i, ln in enumerate(lines):
            draw.text((bx, by + i * line_h), ln, font=f_body, fill=ink)
    return img


# ---------------------------------------------------------------------------
# scenes
# ---------------------------------------------------------------------------
def scene_soldered_top(include_case=False, include_plate=False, include_caps=False,
                       exploded=0.0):
    meshes = []
    pcb = pcb_mesh()
    lift = PCB_LIFT if include_case else 0.0
    meshes.append((pcb + np.array([0, 0, lift]), C_PCB))
    meshes.append((np.concatenate([pad_ring(s[0], s[1] - 5.9, 1.10, "top")
                                   for s in SWITCHES]), C_PAD))
    meshes.append((np.concatenate([pad_ring(s[0] + 5.0, s[1] - 3.8, 1.10, "top")
                                   for s in SWITCHES]), C_PAD))
    meshes.append((np.concatenate([pad_ring(s[0] - 5.0, s[1] + 5.15, 1.30, "top")
                                   for s in SWITCHES]), C_PAD))
    # diode pads (visible from top through the holes)
    dpads = []
    for ref, x, y, row, rot in DIODES:
        dpads.append(pad_ring(x - 3.5, y, 0.80, "top"))
        dpads.append(pad_ring(x + 3.5, y, 0.80, "top"))
    meshes.append((np.concatenate(dpads), C_PAD))
    # XIAO pads + JST pads + BAT1 pads
    xp = []
    for sx in (XIAO["cx"] - 7.62, XIAO["cx"] + 7.62):
        for i in range(7):
            xp.append(pad_ring(sx, XIAO["cy"] - 7.62 + 2.54 * i, 0.85, "top"))
    meshes.append((np.concatenate(xp), C_PAD))
    meshes.append((np.concatenate([pad_ring(JST["x"], JST["y"], 0.95, "top"),
                                   pad_ring(JST["x"] + 2.0, JST["y"], 0.95, "top")]), C_PAD))

    sw = np.concatenate([switch_mesh(x, y) for x, y in SWITCHES])
    meshes.append((sw + np.array([0, 0, lift]), C_SW))
    xiao, _ = xiao_mesh()
    meshes.append((xiao + np.array([0, 0, lift]), C_XIAO))
    meshes.append((jst_mesh() + np.array([0, 0, lift]), C_JST))
    wires = np.concatenate([
        tube([(62.5, 15.8, Z_TOP + 2.6), (65.6, 16.4, Z_TOP + 2.0),
              (68.4, 17.4, Z_TOP + 0.6), (70.0, 17.5, Z_TOP)], 0.32, seg=9),
        tube([(62.5, 18.8, Z_TOP + 2.6), (65.8, 19.4, Z_TOP + 2.0),
              (68.4, 19.5, Z_TOP + 0.6), (70.0, 19.5, Z_TOP)], 0.32, seg=9),
    ])
    meshes.append((wires + np.array([0, 0, lift]), C_WIRE_P))
    if include_case:
        case = load_stl(ROOT / "cad" / "output" / "stl" / "case_bottom.stl")
        meshes.append((case, C_CASE))
    if include_plate:
        plate = load_stl(ROOT / "cad" / "output" / "stl" / "plate.stl")
        meshes.append((plate + np.array([0, 0, 0]), C_PLATE))
    if include_caps:
        cap_meshes = {1: load_stl(ROOT / "cad" / "output" / "stl" / "keycap_1u.stl"),
                      2: load_stl(ROOT / "cad" / "output" / "stl" / "keycap_2u.stl"),
                      3: load_stl(ROOT / "cad" / "output" / "stl" / "keycap_3u.stl")}
        for cx, cy, u, name in KEYCAPS:
            col = C_CAP_ACCENT if name == "STOP" else (
                C_CAP_DARK if name in ("UP", "LEFT", "DOWN", "RIGHT", "ENTER") else C_CAP_LIGHT)
            m = cap_meshes[u] + np.array([cx, cy, CAP_BOT_Z])
            meshes.append((m, col))
    return meshes


def scene_soldered_bottom():
    meshes = []
    meshes.append((pcb_mesh(), C_PCB))
    # bottom pads
    bp = []
    for ref, x, y, row, rot in DIODES:
        bp.append(pad_ring(x - 3.5, y, 0.80, "bottom"))
        bp.append(pad_ring(x + 3.5, y, 0.80, "bottom"))
    for x, y in BAT_PADS:
        bp.append(pad_ring(x, y, 0.80, "bottom"))
    for sx in (XIAO["cx"] - 7.62, XIAO["cx"] + 7.62):
        for i in range(7):
            bp.append(pad_ring(sx, XIAO["cy"] - 7.62 + 2.54 * i, 0.85, "bottom"))
    bp.append(pad_ring(JST["x"], JST["y"], 0.95, "bottom"))
    bp.append(pad_ring(JST["x"] + 2.0, JST["y"], 0.95, "bottom"))
    meshes.append((np.concatenate(bp), C_PAD))
    di = np.concatenate([diode_mesh(x, y, rot) for ref, x, y, row, rot in DIODES])
    meshes.append((di, C_DIODE))
    bands = []
    for ref, x, y, row, rot in DIODES:
        s = 1.0 if rot == 0 else -1.0
        bands.append(cyl((x + s * 1.56, y, -1.15), (x + s * 1.88, y, -1.15), 1.0, seg=14))
    meshes.append((np.concatenate(bands), C_BAND))
    meshes.append((header_pins_bottom(), C_METAL))
    return meshes


# ---------------------------------------------------------------------------
# views
# ---------------------------------------------------------------------------
def project_anchor(cam, p):
    sx, sy, _ = cam.project([p])
    return float(sx[0]), float(sy[0])


def view_front_iso():
    cam = Camera(pos=(139, -96, 147), target=(54, 40, 3), fov=30,
                 width=2000, height=1500)
    meshes = scene_soldered_top()
    meshes.append((ground_plane(-45.0), C_GROUND))
    img = render(cam, meshes, ss=2,
                 lights=[((0.35, -0.5, 0.79), 0.62), ((-0.6, -0.2, 0.4), 0.24)])
    callouts = [
        dict(anchor=(54, 12, Z_TOP + 7.3), xy=(250, 1140),
             text="U1  XIAO nRF52840\n2×7 排针，抬高 2.5mm\nUSB-C 朝后边"),
        dict(anchor=(76, 12, Z_TOP + 4.5), xy=(1120, 1280),
             text="J1  JST-PH 2.0\npin1 = BAT+"),
        dict(anchor=(58, 18, Z_TOP + 1.2), xy=(120, 940),
             text="电池线：XIAO 背面 BAT 焊盘\n沿模块右侧走到 BAT1"),
        dict(anchor=(85.5, 14, Z_TOP), xy=(1420, 1300),
             text="走线槽 4×8mm\n电池线穿到背面"),
        dict(anchor=(18, 30.5, Z_TOP + 7.9), xy=(110, 330),
             text="SW1–SW5  R0 上排\nPERM MODEL CMD ↑ VOICE"),
        dict(anchor=(18, 47.5, Z_TOP + 7.9), xy=(110, 500),
             text="SW6–SW9  R1 中排\nSTOP ← ↓ →"),
        dict(anchor=(72, 64.5, Z_TOP + 7.9), xy=(1250, 330),
             text="SW10–SW14  R2 下排\nENTER 2 轴 / SPACE 3 轴\n每个轴位 pin1 在左下角"),
        dict(anchor=(90, 55.5, Z_TOP + 4.9), xy=(1980, 860), align="right",
             text="14 个 Choc V2 轴\n焊前先确认方向"),
    ]
    img = draw_callouts(img, cam, callouts,
                        title="ClaudePad · 焊好的正面（3D）",
                        subtitle="轴体 / 主控 / JST / 电池线 —— 未装定位板与键帽")
    img.save(OUT / "guide-front-iso.png")
    print("wrote", OUT / "guide-front-iso.png")


def view_top():
    cam = Camera(pos=(54, 41, 250), target=(54, 41, 0), up=(0, 1, 0),
                 ortho_scale=17.5, width=2500, height=1900)
    scene = scene_soldered_top()
    scene.append((ground_plane(-45.0), C_GROUND))
    layout = [C_PCB, C_PAD, C_PAD, C_PAD, C_PAD, C_PAD, C_PAD,
              np.array([0.78, 0.78, 0.78]), np.array([0.42, 0.50, 0.58]),
              np.array([0.92, 0.89, 0.80]), np.array([0.80, 0.22, 0.16])]
    meshes = [(tri, layout[i] if i < len(layout) else col)
              for i, (tri, col) in enumerate(scene)]
    img = render(cam, meshes, ss=2,
                 lights=[((0.25, -0.2, 0.95), 0.70), ((-0.4, 0.3, 0.5), 0.20)])
    callouts = [
        dict(anchor=(54, 12, Z_TOP + 7.3), xy=(2045, 1660),
             text="U1  XIAO nRF52840\n2×7 排针，抬高 2.5mm"),
        dict(anchor=(76, 12, Z_TOP + 4.5), xy=(2045, 1470),
             text="J1  JST-PH 2.0\npin1 = BAT+"),
        dict(anchor=(85.5, 14, Z_TOP), xy=(2045, 1310),
             text="走线槽 4×8mm"),
        dict(anchor=(54, 47.5, Z_TOP + 6.3), xy=(2045, 820),
             text="R1/C1 空位\n不装轴、不补孔"),
        dict(anchor=(72, 64.5, Z_TOP + 6.3), xy=(2045, 470),
             text="SPACE 3u\nSW12+SW13+SW14 并联"),
        dict(anchor=(18, 30.5, Z_TOP + 6.3), xy=(40, 1030),
             text="SW1–SW5  R0\nPERM MODEL CMD ↑ VOICE"),
        dict(anchor=(18, 47.5, Z_TOP + 6.3), xy=(40, 720),
             text="SW6–SW9  R1\nSTOP ← ↓ →"),
        dict(anchor=(27, 64.5, Z_TOP + 6.3), xy=(40, 400),
             text="SW10–SW14  R2\nENTER 2u：SW10+SW11 并联\npin1 在轴位左下角"),
    ]
    img = draw_callouts(img, cam, callouts, fsize=27,
                        title="ClaudePad · 焊好的正面（俯视布局图）",
                        subtitle="矩阵 R0–R2 × C0–C4，11 个键位；R1/C1 为空位")
    d = ImageDraw.Draw(img, "RGBA")
    f_small = font(24, True)
    for i, x in enumerate(KEY_X):
        px, py = project_anchor(cam, (x, 80.6, Z_TOP))
        d.text((px - 15, py - 8), f"C{i}", font=f_small, fill=(70, 70, 70))
    px, _ = project_anchor(cam, (54, 41, Z_TOP))
    d.text((px - 130, 150), "↑ 板边为使用者一侧（前）", font=font(26), fill=(80, 80, 80))
    d.text((px - 140, 1720), "↓ 板下边为 USB-C / 控制器仓（后）", font=font(26), fill=(80, 80, 80))
    img.save(OUT / "guide-top.png")
    print("wrote", OUT / "guide-top.png")


def view_bottom_iso():
    cam = Camera(pos=(147, -97, -144), target=(54, 40, 0), fov=30,
                 width=2000, height=1500)
    meshes = scene_soldered_bottom()
    meshes.append((ground_plane(45.0), C_GROUND))
    img = render(cam, meshes, ss=2,
                 lights=[((0.35, -0.5, -0.79), 0.62), ((-0.6, -0.2, -0.4), 0.24)])
    callouts = [
        dict(anchor=(18, 38.5, -1.15), xy=(80, 1120),
             text="D1–D5  R0/R1 之间\n阴极（短丝印线）朝右"),
        dict(anchor=(18, 55.5, -1.15), xy=(80, 1270),
             text="D6–D9  R1/R2 之间\n阴极朝右"),
        dict(anchor=(27, 74.5, -1.15), xy=(560, 1370),
             text="D10  ENTER 共用\n转 180°，阴极朝左"),
        dict(anchor=(63, 74.5, -1.15), xy=(1230, 1330),
             text="D11  SPACE 共用\n转 180°，阴极朝左"),
        dict(anchor=(54, 12, -2.6), xy=(150, 640),
             text="XIAO 排针脚\n焊完剪到 ≤ 4mm"),
        dict(anchor=(70, 18.5, 0), xy=(1980, 470), align="right",
             text="BAT1  BAT+ / BAT−\n电池线焊盘"),
        dict(anchor=(85.5, 14, 0), xy=(1600, 200),
             text="走线槽（贯穿板）"),
    ]
    img = draw_callouts(img, cam, callouts,
                        title="ClaudePad · 焊好的背面（3D）",
                        subtitle="11 个 1N4148：以背面短丝印线为阴极；D1–D9 阴极朝右，D10/D11 朝左")
    img.save(OUT / "guide-bottom-iso.png")
    print("wrote", OUT / "guide-bottom-iso.png")


def view_assembled():
    cam = Camera(pos=(158, -106, 160), target=(54, 41, 8), fov=30,
                 width=2000, height=1500)
    meshes = scene_soldered_top(include_case=True, include_plate=True, include_caps=True)
    meshes.append((ground_plane(-2.0), C_GROUND))
    img = render(cam, meshes, ss=2,
                 lights=[((0.4, -0.5, 0.76), 0.58), ((-0.55, -0.2, 0.45), 0.26)])
    callouts = [
        dict(anchor=(90, 30.5, 14.9), xy=(1450, 980),
             text="定位板 1.2mm\n14 个 14.5mm 方孔 + 侧卡扣槽"),
        dict(anchor=(72, 64.5, 18.6), xy=(1120, 1270),
             text="键帽：1u×9 / 2u×1 / 3u×1\nSPACE 3u 跨 3 颗轴"),
        dict(anchor=(54, 12, 15.9), xy=(180, 1140),
             text="控制器仓敞开\nUSB-C / RESET 可直接操作"),
        dict(anchor=(60, 78, 8), xy=(1350, 1330),
             text="底座 4 个支撑柱托住 PCB\n4 颗 M2×6 自攻螺丝"),
    ]
    img = draw_callouts(img, cam, callouts,
                        title="ClaudePad · 总装（底座 + 定位板 + 键帽）",
                        subtitle="整机约 108 × 82 × 23.1 mm")
    img.save(OUT / "guide-assembled.png")
    print("wrote", OUT / "guide-assembled.png")


def main():
    print("board tris:", len(pcb_mesh()))
    view_front_iso()
    view_top()
    view_bottom_iso()
    view_assembled()


if __name__ == "__main__":
    main()

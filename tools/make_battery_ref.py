"""Crop + annotate the JST (front) and BAT1 (back) areas for battery wiring."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pcb" / "output" / "preview"
OUT = ROOT / "docs" / "3d" / "battery-pads.png"
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"

PCB_X0, PCB_X1 = 9.0, 99.0
PCB_Y0, PCB_Y1 = 3.0, 79.0


def board_box(img: Image.Image, pad: int = 10):
    a = np.asarray(img.convert("RGB")).astype(int)
    mask = (a[:, :, 1] > a[:, :, 0] + 12) & (a[:, :, 1] > a[:, :, 2] + 6)
    ys, xs = np.nonzero(mask)
    return (max(xs.min() - pad, 0), max(ys.min() - pad, 0),
            min(xs.max() + pad, a.shape[1]), min(ys.max() + pad, a.shape[0]))


def to_px(box, x, y, mirrored):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if mirrored:
        return x0 + (PCB_X1 - x) / (PCB_X1 - PCB_X0) * w, y0 + (y - PCB_Y0) / (PCB_Y1 - PCB_Y0) * h
    return x0 + (x - PCB_X0) / (PCB_X1 - PCB_X0) * w, y0 + (y - PCB_Y0) / (PCB_Y1 - PCB_Y0) * h


def panel(img, box, cx, cy, halfx, halfy, scale, mirrored):
    px, py = to_px(box, cx, cy, mirrored)
    x0, y0, x1, y1 = box
    dx = halfx / (PCB_X1 - PCB_X0) * (x1 - x0)
    dy = halfy / (PCB_Y1 - PCB_Y0) * (y1 - y0)
    sx0, sy0 = int(round(px - dx)), int(round(py - dy))
    crop = img.crop((sx0, sy0, int(round(px + dx)), int(round(py + dy))))
    crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)

    def mapper(x, y):
        ppx, ppy = to_px(box, x, y, mirrored)
        return (ppx - sx0) * scale, (ppy - sy0) * scale

    return crop, mapper


def ring(draw, pt, r, color, width=5):
    x, y = pt
    draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=width)


def main():
    top = Image.open(SRC / "claudepad-pcb-top.png").convert("RGB")
    bot = Image.open(SRC / "claudepad-pcb-bottom.png").convert("RGB")
    tb, bb = board_box(top), board_box(bot)

    # ---- front: J1 ----------------------------------------------------------
    jst, map_jst = panel(top, tb, 75.5, 10.5, 9.5, 7.0, 3.6, mirrored=False)
    d1 = ImageDraw.Draw(jst)
    f_small = ImageFont.truetype(FONT_B, 40)
    ring(d1, map_jst(74.0, 12.0), 34, (210, 60, 40), 6)
    ring(d1, map_jst(76.0, 12.0), 34, (30, 90, 190), 6)

    # ---- back: BAT1 (preview is mirrored in X) ------------------------------
    bat, map_bat = panel(bot, bb, 73.0, 17.2, 9.5, 7.0, 3.6, mirrored=True)
    d2 = ImageDraw.Draw(bat)
    ring(d2, map_bat(70.0, 17.5), 34, (210, 60, 40), 6)
    ring(d2, map_bat(70.0, 19.5), 34, (30, 90, 190), 6)

    pad, gap = 54, 48
    head_h, note_h = 64, 116
    panel_y = 42 + 66 + head_h
    W = pad * 2 + jst.width + gap + bat.width
    H = panel_y + max(jst.height, bat.height) + note_h + pad
    canvas = Image.new("RGB", (W, H), (247, 244, 236))
    d = ImageDraw.Draw(canvas)
    f_title = ImageFont.truetype(FONT_B, 50)
    f_head = ImageFont.truetype(FONT, 36)
    f_note = ImageFont.truetype(FONT, 26)
    ink = (30, 30, 30)

    d.text((pad, 30), "电池接线位置（J1 正面 / BAT1 背面）", font=f_title, fill=ink)

    x1 = pad
    canvas.paste(jst, (x1, panel_y))
    d.text((x1, panel_y - head_h + 6), "正面 J1：插电池插头", font=f_head, fill=(150, 50, 40))
    for i, (ln, col) in enumerate([
        ("红圈 = pin1 = BAT+（内侧方形焊盘）", (170, 50, 35)),
        ("蓝圈 = pin2 = BAT−（外侧）", (30, 80, 170)),
        ("插头方向以 JST 座的缺口/丝印为准", (70, 70, 70)),
    ]):
        d.text((x1, panel_y + jst.height + 16 + i * 34), ln, font=f_note, fill=col)

    x2 = pad + jst.width + gap
    canvas.paste(bat, (x2, panel_y))
    d.text((x2, panel_y - head_h + 6), "背面 BAT1：接 XIAO 电池线", font=f_head, fill=(40, 80, 140))
    for i, (ln, col) in enumerate([
        ("红圈 = BAT+（丝印 BAT+ 旁）", (170, 50, 35)),
        ("蓝圈 = BAT−（丝印 BAT− 旁）", (30, 80, 170)),
        ("电池插头线经走线槽（4×8mm 长孔）穿到板下", (70, 70, 70)),
    ]):
        d.text((x2, panel_y + bat.height + 16 + i * 34), ln, font=f_note, fill=col)

    canvas.save(OUT)
    print("wrote", OUT, canvas.size)


if __name__ == "__main__":
    main()

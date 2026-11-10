"""Build a quick side-by-side "which side is which" reference image.

Left  = PCB top preview  (F.SilkS: key names, R0-R2, C0-C4, "1", "+JST/-JST")
Right = PCB bottom preview (B.SilkS: only BAT+ / BAT- plus the diode cathode ticks)

Run: python tools/make_sides_ref.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pcb" / "output" / "preview"
OUT = ROOT / "docs" / "3d" / "board-sides.png"
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"


def crop_board(img: Image.Image, pad: int = 24) -> Image.Image:
    a = np.asarray(img.convert("RGB")).astype(int)
    # the bare board is green; the render background is warm gray
    mask = (a[:, :, 1] > a[:, :, 0] + 15) & (a[:, :, 1] > a[:, :, 2] + 8)
    ys, xs = np.nonzero(mask)
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, a.shape[1])
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, a.shape[0])
    return img.crop((x0, y0, x1, y1))


def fit(img: Image.Image, width: int) -> Image.Image:
    h = round(img.height * width / img.width)
    return img.resize((width, h), Image.LANCZOS)


def main() -> None:
    top = fit(crop_board(Image.open(SRC / "claudepad-pcb-top.png")), 1120)
    bot = fit(crop_board(Image.open(SRC / "claudepad-pcb-bottom.png")), 1120)

    pad, gap = 60, 70
    head_y = 118
    panel_y = 186
    note_y = panel_y + max(top.height, bot.height) + 16
    foot_y = note_y + 92
    W = pad * 2 + top.width + gap + bot.width
    H = foot_y + 74
    canvas = Image.new("RGB", (W, H), (247, 244, 236))
    d = ImageDraw.Draw(canvas)

    f_title = ImageFont.truetype(FONT_B, 56)
    f_head = ImageFont.truetype(FONT, 38)
    f_note = ImageFont.truetype(FONT, 29)
    ink = (30, 30, 30)

    d.text((pad, 30), "怎么区分正反面（看丝印）", font=f_title, fill=ink)

    x1 = pad
    canvas.paste(top, (x1, panel_y))
    d.text((x1, head_y), "正面（F.SilkS / 装轴面）", font=f_head, fill=(150, 50, 40))
    for i, ln in enumerate(["丝印：R0–R2、C0–C4、PERM/MODEL/… 键名、", "XIAO 旁「1」、JST 旁「+JST / −JST」"]):
        d.text((x1, note_y + i * 36), ln, font=f_note, fill=(70, 70, 70))

    x2 = pad + top.width + gap
    canvas.paste(bot, (x2, panel_y))
    d.text((x2, head_y), "背面（B.SilkS / 二极管面）", font=f_head, fill=(40, 80, 140))
    for i, ln in enumerate(["丝印只有 BAT+ / BAT−，以及 11 个二极管", "焊盘旁的短横线（阴极标记）"]):
        d.text((x2, note_y + i * 36), ln, font=f_note, fill=(70, 70, 70))

    d.text((pad, foot_y),
           "一句话：能看到一堆键名文字的那面是正面；只有 BAT+ / BAT− 和短横线的那面是背面。",
           font=ImageFont.truetype(FONT_B, 34), fill=(20, 20, 20))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT)
    print("wrote", OUT, canvas.size)


if __name__ == "__main__":
    main()

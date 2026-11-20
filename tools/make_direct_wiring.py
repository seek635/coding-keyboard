"""Close-up: solder battery wires (no JST plug) directly to BAT1 on the back."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pcb" / "output" / "preview" / "claudepad-pcb-bottom.png"
OUT = ROOT / "docs" / "3d" / "battery-direct-wiring.png"
F = r"C:\Windows\Fonts\msyh.ttc"
FB = r"C:\Windows\Fonts\msyhbd.ttc"

RED = (200, 55, 40)
BLK = (35, 35, 38)
INK = (30, 30, 30)
DIM = (90, 90, 90)
YEL = (190, 150, 40)

# crop window in the original preview image (rows are the back view, x mirrored)
CROP = (690, 205, 1010, 505)
PAD_PLUS = (914, 376)
PAD_MINUS = (914, 421)
JST_1 = (814, 276)
JST_2 = (851, 276)


def main():
    img = Image.open(SRC).convert("RGB")
    panel = img.crop(CROP)
    scale = 4
    panel = panel.resize((panel.width * scale, panel.height * scale), Image.LANCZOS)

    def mp(pt):
        return ((pt[0] - CROP[0]) * scale, (pt[1] - CROP[1]) * scale)

    px_plus, px_minus = mp(PAD_PLUS), mp(PAD_MINUS)
    j1, j2 = mp(JST_1), mp(JST_2)

    W = panel.width + 780
    H = panel.height + 300
    canvas = Image.new("RGB", (W, H), (247, 244, 236))
    ox, oy = 70, 190
    canvas.paste(panel, (ox, oy))
    d = ImageDraw.Draw(canvas)

    f_title = ImageFont.truetype(FB, 48)
    f_lab = ImageFont.truetype(FB, 32)
    f_note = ImageFont.truetype(F, 27)

    d.text((60, 34), "电池没有插头：直接焊到背面 BAT1", font=f_title, fill=INK)
    d.text((62, 96), "红线 → BAT+（上）；黑线 → BAT−（下）；XIAO 的两根线也重新并到同一对焊盘",
           font=f_note, fill=DIM)

    ax, ay = ox + px_plus[0], oy + px_plus[1]
    bx, by = ox + px_minus[0], oy + px_minus[1]

    def arrow(start, end, color, w=7):
        d.line([start, end], fill=color, width=w)
        r = 11
        d.ellipse([end[0] - r, end[1] - r, end[0] + r, end[1] + r], fill=color)

    # labels on the right side
    lx = ox + panel.width + 30
    # battery red +
    d.text((lx, ay - 26), "电池红线（+）", font=f_lab, fill=RED)
    d.line([(lx - 18, ay), (ax, ay)], fill=RED, width=6)
    d.ellipse([ax - 10, ay - 10, ax + 10, ay + 10], fill=RED)
    # battery black -
    d.text((lx, by - 16), "电池黑线（−）", font=f_lab, fill=BLK)
    d.line([(lx - 18, by), (bx, by)], fill=BLK, width=6)
    d.ellipse([bx - 10, by - 10, bx + 10, by + 10], fill=BLK)
    # XIAO note
    d.text((lx, by + 60), "XIAO 的两根线也焊在\n这两个焊盘上（每盘两股线）", font=f_note, fill=DIM)
    # JST note
    jy = oy + j1[1] - 120
    d.text((lx, jy), "这两块方形焊盘是 J1\n没有 JST 座就不用管它", font=f_note, fill=DIM)
    d.line([(lx - 18, jy + 40), (ox + j2[0] + 30, oy + j2[1])], fill=(120, 120, 120), width=4)

    # pad labels inside the panel
    d.text((ox + px_plus[0] - 250, oy + px_plus[1] - 30), "BAT+", font=ImageFont.truetype(FB, 34), fill=(240, 240, 240))
    d.text((ox + px_minus[0] - 250, oy + px_minus[1] - 30), "BAT−", font=ImageFont.truetype(FB, 34), fill=(240, 240, 240))

    d.text((60, H - 96),
           "顺序：先给焊盘上锡 → 焊 XIAO 的两根细线 → 再焊电池线；焊前用胶带把电池另一极贴住防短路，焊完测通断/短路再上电。",
           font=f_note, fill=(70, 70, 70))

    canvas.save(OUT)
    print("wrote", OUT, canvas.size)


if __name__ == "__main__":
    main()

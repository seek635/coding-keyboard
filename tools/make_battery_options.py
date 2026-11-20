"""Battery wiring options diagram (with / without JST plug, optional power switch)."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "3d" / "battery-wiring-options.png"
F = r"C:\Windows\Fonts\msyh.ttc"
FB = r"C:\Windows\Fonts\msyhbd.ttc"

W, H = 2200, 1500
BG = (247, 244, 236)
INK = (32, 32, 32)
DIM = (95, 95, 95)
RED = (196, 54, 40)
BLK = (45, 45, 48)
BLUE = (44, 88, 170)
GOLD = (190, 152, 44)
GREEN = (32, 105, 70)


def box(d, x, y, w, h, title, sub=None, fill=(255, 255, 255), edge=(120, 120, 120),
        tc=INK, subc=DIM, radius=16):
    d.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=edge, width=3)
    ft = ImageFont.truetype(FB, 34)
    fs = ImageFont.truetype(F, 26)
    tw = d.textlength(title, font=ft)
    d.text((x + (w - tw) / 2, y + 22), title, font=ft, fill=tc)
    if sub:
        for i, line in enumerate(sub.split(chr(10))):
            sw = d.textlength(line, font=fs)
            d.text((x + (w - sw) / 2, y + 64 + i * 36), line, font=fs, fill=subc)


def wire(d, pts, color, width=6):
    d.line(pts, fill=color, width=width, joint="curve")


def arrow(d, pts, color, width=6, head=16):
    wire(d, pts, color, width)
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    d.polygon([(x2, y2),
               (x2 - head * 0.9 - (y2 - y1) * 0.25, y2 - head * 0.5 + (x2 - x1) * 0.2),
               (x2 - head * 0.9 + (y2 - y1) * 0.25, y2 - head * 0.5 - (x2 - x1) * 0.2)],
              fill=color)


def tag(d, x, y, text, color, size=26):
    f = ImageFont.truetype(FB, size)
    d.text((x, y), text, font=f, fill=color)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    ft = ImageFont.truetype(FB, 54)
    fs = ImageFont.truetype(F, 28)
    d.text((60, 34), "电池接法（按你手上的材料选一种）", font=ft, fill=INK)
    d.text((62, 104), "XIAO 自带 BQ25101 充电管理；板上 J1 与 BAT1 在板内是通的（BAT+ / BAT− 同一网络）",
           font=fs, fill=DIM)

    # ---------------- Option A ----------------
    y = 200
    tag(d, 60, y - 44, "A. 有 JST-PH 2.0 插头的电池（最省事）", GREEN, 32)
    box(d, 70, y, 300, 120, "电池 3.7V", "302030 带保护板")
    box(d, 470, y, 250, 120, "JST 插头", "插到板上 J1")
    box(d, 820, y, 300, 120, "板内铜箔", "B.Cu：J1 ↔ BAT1", fill=(232, 243, 236))
    box(d, 1220, y, 300, 120, "BAT1 焊盘", "背面 BAT+ / BAT−")
    box(d, 1620, y, 500, 120, "XIAO 背面 BAT 焊盘", "两根细线焊到 BAT1")
    arrow(d, [(370, y + 60), (470, y + 60)], RED)
    arrow(d, [(720, y + 60), (820, y + 60)], RED)
    arrow(d, [(1120, y + 60), (1220, y + 60)], RED)
    arrow(d, [(1520, y + 60), (1620, y + 60)], RED)
    tag(d, 86, y + 128, "红=+ 黑=−", DIM, 24)

    # ---------------- Option B ----------------
    y = 520
    tag(d, 60, y - 44, "B. 电池没有插头（或没焊 JST 座）：线直接焊到 BAT1", BLUE, 32)
    box(d, 70, y, 300, 130, "电池 3.7V", "红线 + / 黑线 −")
    box(d, 470, y, 360, 130, "直接焊到背面 BAT1", "红→BAT+（上）\n黑→BAT−（下）")
    box(d, 940, y, 420, 130, "XIAO 的两根线", "也焊在 BAT1 同样两个焊盘\n（每盘两股线）")
    box(d, 1470, y + 15, 620, 100, "结果：BAT1 就是接线柱，J1 不用焊", "",
        fill=(236, 240, 250))
    arrow(d, [(370, y + 65), (470, y + 65)], RED)
    arrow(d, [(830, y + 65), (940, y + 65)], BLK)
    tag(d, 86, y + 140, "注意：先焊线再上电池；两根线不要短路", DIM, 24)

    # ---------------- Option C ----------------
    y = 850
    tag(d, 60, y - 44, "C. 想加物理电源开关（可选，原设计没有）", (150, 90, 40), 32)
    box(d, 70, y, 280, 120, "电池 +", "红线", fill=(255, 240, 238))
    box(d, 440, y, 300, 132, "拨动开关", "串联在 BAT+ 上\n电流 ≥1A", fill=(255, 248, 230))
    box(d, 830, y, 280, 120, "BAT1 BAT+", "板上焊盘")
    box(d, 1210, y, 300, 120, "电池 −", "黑线", fill=(240, 240, 242))
    box(d, 1600, y, 280, 120, "BAT1 BAT−", "板上焊盘")
    arrow(d, [(350, y + 60), (440, y + 60)], RED)
    arrow(d, [(740, y + 60), (830, y + 60)], RED)
    arrow(d, [(1510, y + 66), (1600, y + 66)], BLK)
    tag(d, 70, y + 150, "开关放控制器仓侧壁；别放在 XIAO 天线（键区那一端）附近", DIM, 24)

    # ---------------- footer ----------------
    d.text((60, 1120), "没有电源开关怎么办：", font=ImageFont.truetype(FB, 36), fill=INK)
    lines = [
        "· USB-C 插上 = 上电（同时给电池充电）；拔掉 = 断电。",
        "· 用电池时靠 ZMK 深度睡眠：闲置自动睡，按任意键唤醒；要彻底断电就拔 JST 插头（最推荐的“开关”）。",
        "· 不要从 USB 的 5V 焊盘和电池同时硬接；板子只需要一路供电。",
        "· 加开关就按方案 C：只串在 BAT+ 上，BAT− 直连。",
    ]
    for i, ln in enumerate(lines):
        d.text((70, 1180 + i * 46), ln, font=ImageFont.truetype(F, 28), fill=(60, 60, 60))

    img.save(OUT)
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()

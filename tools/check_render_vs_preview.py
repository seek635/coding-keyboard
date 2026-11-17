"""Diagnostic: compare the 3D scene (ortho top) with the KiCad PCB top preview."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_assembly as R

OUT = Path(r"D:\coding keyboard\.tmp_check.png")


def main():
    cam = R.Camera(pos=(54, 41, 250), target=(54, 41, 0), up=(0, 1, 0),
                   ortho_scale=17.5, width=1400, height=1180)
    meshes = R.scene_soldered_top()
    meshes.append((R.ground_plane(-45.0), R.C_GROUND))
    img3d = R.render(cam, meshes, ss=2,
                     lights=[((0.25, -0.2, 0.95), 0.70), ((-0.4, 0.3, 0.5), 0.20)])

    # kicad preview, board-cropped, matched size
    top = Image.open(R.ROOT / "pcb" / "output" / "preview" / "claudepad-pcb-top.png").convert("RGB")
    a = np.asarray(top).astype(int)
    mask = (a[:, :, 1] > a[:, :, 0] + 12) & (a[:, :, 1] > a[:, :, 2] + 6)
    ys, xs = np.nonzero(mask)
    pad = 6
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0),
           min(xs.max() + pad, a.shape[1]), min(ys.max() + pad, a.shape[0]))
    kic = top.crop(box).resize(img3d.size, Image.LANCZOS)

    scale = 0.5
    w3 = int(img3d.width * scale)
    h3 = int(img3d.height * scale)
    p3 = img3d.resize((w3, h3), Image.LANCZOS)
    pk = kic.resize((w3, h3), Image.LANCZOS)

    gap, m = 30, 20
    canvas = Image.new("RGB", (m * 2 + w3 * 2 + gap, h3 + 110), (245, 243, 238))
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 34)
    canvas.paste(p3, (m, 80))
    canvas.paste(pk, (m + w3 + gap, 80))
    d.text((m, 24), "我的 3D 渲染（正上方）", font=f, fill=(160, 40, 30))
    d.text((m + w3 + gap, 24), "KiCad 出板预览（正上方，镜像？）", font=f, fill=(30, 60, 140))
    canvas.save(OUT)
    print("wrote", OUT, canvas.size)


if __name__ == "__main__":
    main()

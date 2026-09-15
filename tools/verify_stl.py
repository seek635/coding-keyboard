# -*- coding: utf-8 -*-
"""
STL 校验脚本（纯 Python，无第三方依赖）
---------------------------------------
OpenSCAD 导出 STL 后，用本脚本验证渲染结果是否真的正确：

  1. 三角形数量、包围盒尺寸（与 params.scad 的期望值对比）
  2. 水密性（每条边必须恰好被 2 个三角形共用）
  3. 体积（用散度定理计算，负值说明法向反了）
  4. 是否有退化三角形（面积为 0）

这能补上「模型没经过真实渲染验证」这个缺口。

运行：
    python tools/verify_stl.py                  # 校验 cad/output 下全部 STL
    python tools/verify_stl.py path/to/x.stl    # 校验指定文件
"""

import os
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scad_params import load, find_project_root     # noqa: E402

ROOT = find_project_root() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "cad", "output")

# 各零件期望的包围盒（从 params.scad 推导，容差 ±0.6mm）
def expected_boxes(P):
    plate_w = P["PLATE_W"]
    plate_h = P["PLATE_H"]
    case_w = plate_w + P["CASE_TOP_TOL"] * 2 + P["CASE_WALL"] * 2
    case_d = plate_h + P["CASE_TOP_TOL"] * 2 + P["CASE_WALL"] * 2
    return {
        "00_test_coupon.stl": None,      # 组合件，不校验固定尺寸
        # 底座：X 含壳外拨杆凸台；Z 少了底部防大象脚倒角
        "01_case_bottom.stl": (case_w + P["SW_BOSS_T"],
                               case_d,
                               P["CASE_OUTER_H"] - P["TOL_BOTTOM_CHAMFER"]),
        "02_plate.stl":       (plate_w, plate_h, P["PLATE_T"]),
        "03_keycap_1u.stl":   (P["PITCH"] - 0.40, P["PITCH"] - 0.40, P["CAP_H"]),
        "04_keycap_2u.stl":   (P["PITCH"] * 2 - 0.40, P["PITCH"] - 0.40, P["CAP_H"]),
        "05_keycap_4u.stl":   (P["PITCH"] * 4 - 0.40, P["PITCH"] - 0.40, P["CAP_H"]),
    }


def read_stl(path):
    """读取二进制或 ASCII STL，返回 [(v1,v2,v3), ...]"""
    with open(path, "rb") as f:
        head = f.read(84)
        if len(head) < 84:
            # 可能是 ASCII
            f.seek(0)
            return read_ascii(f)
        n = struct.unpack("<I", head[80:84])[0]
        expect = 84 + n * 50
        actual = os.path.getsize(path)
        if expect != actual:
            f.seek(0)
            return read_ascii(f)
        tris = []
        for _ in range(n):
            data = f.read(50)
            vals = struct.unpack("<12fH", data)
            tris.append((vals[3:6], vals[6:9], vals[9:12]))
        return tris


def read_ascii(f):
    tris = []
    cur = []
    for line in f:
        line = line.decode("ascii", "ignore").strip()
        if line.startswith("vertex"):
            cur.append(tuple(float(x) for x in line.split()[1:4]))
            if len(cur) == 3:
                tris.append(tuple(cur))
                cur = []
    return tris


def bbox(tris):
    xs = [v[0] for t in tris for v in t]
    ys = [v[1] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def volume(tris):
    """散度定理：V = Σ (v1 · (v2 × v3)) / 6"""
    total = 0.0
    for a, b, c in tris:
        total += (a[0] * (b[1] * c[2] - b[2] * c[1])
                  - a[1] * (b[0] * c[2] - b[2] * c[0])
                  + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return total / 6.0


def check_watertight(tris, eps=1e-4):
    """每条边应恰好被 2 个三角形共用"""
    def key(v):
        return (round(v[0] / eps), round(v[1] / eps), round(v[2] / eps))

    edges = defaultdict(int)
    for a, b, c in tris:
        ka, kb, kc = key(a), key(b), key(c)
        for e in [(ka, kb), (kb, kc), (kc, ka)]:
            edges[tuple(sorted(e))] += 1

    bad = {e: n for e, n in edges.items() if n != 2}
    return len(bad), len(edges)


def degenerate_count(tris, eps=1e-9):
    n = 0
    for a, b, c in tris:
        # 叉积模长的两倍 = 平行四边形面积
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        cx = uy * vz - uz * vy
        cy = uz * vx - ux * vz
        cz = ux * vy - uy * vx
        if (cx * cx + cy * cy + cz * cz) < eps:
            n += 1
    return n


def main():
    P = load()
    expect = expected_boxes(P)

    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        if not os.path.isdir(OUT):
            print(f"❌ 输出目录不存在：{OUT}")
            print("   先跑：python tools/export_stl.py")
            return 1
        files = sorted(os.path.join(OUT, f) for f in os.listdir(OUT)
                       if f.lower().endswith(".stl"))

    if not files:
        print(f"❌ {OUT} 下没有 STL 文件。先跑：python tools/export_stl.py")
        return 1

    print("=" * 76)
    print("STL 校验")
    print("=" * 76)

    failed = 0
    for path in files:
        name = os.path.basename(path)
        print(f"\n【{name}】")
        try:
            tris = read_stl(path)
        except Exception as e:
            print(f"  ❌ 读取失败：{e}")
            failed += 1
            continue

        if not tris:
            print("  ❌ 没有三角形（空文件或格式不支持）")
            failed += 1
            continue

        (x0, y0, z0), (x1, y1, z1) = bbox(tris)
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        vol = volume(tris)
        bad, total_e = check_watertight(tris)
        deg = degenerate_count(tris)

        print(f"  三角形     : {len(tris):,}")
        print(f"  包围盒     : {dx:.2f} × {dy:.2f} × {dz:.2f} mm")
        print(f"  原点偏移   : ({x0:.2f}, {y0:.2f}, {z0:.2f})")
        print(f"  体积       : {vol/1000:.2f} cm³")
        print(f"  退化三角形 : {deg}")

        ok = True
        if deg > 0:
            print(f"  ⚠️  有 {deg} 个零面积三角形（通常无害，但可能是建模瑕疵）")
        if bad > 0:
            print(f"  ⚠️  非水密：{bad} / {total_e} 条边不是恰好共用 2 次")
            print("      （多个分离实体组合时属正常；单一实体则说明模型有破面）")
        if vol < 0:
            print("  ⚠️  体积为负 → 法向朝内，切片软件可能报错")
            ok = False

        exp = expect.get(name)
        if exp:
            ew, ed, eh = exp
            d = [abs(dx - ew), abs(dy - ed), abs(dz - eh)]
            print(f"  期望尺寸   : {ew:.2f} × {ed:.2f} × {eh:.2f} mm")
            worst = max(d)
            if worst <= 0.6:
                print(f"  ✅ 尺寸吻合（最大偏差 {worst:.2f} mm）")
            else:
                print(f"  ❌ 尺寸不符（最大偏差 {worst:.2f} mm）")
                ok = False

        if not ok:
            failed += 1

    print("\n" + "=" * 76)
    if failed:
        print(f"❌ {failed} / {len(files)} 个文件有问题")
        return 1
    print(f"✅ 全部 {len(files)} 个文件校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

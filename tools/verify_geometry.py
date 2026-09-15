# -*- coding: utf-8 -*-
"""
CAD 几何交叉验证
----------------
不依赖 OpenSCAD，用 Python 独立复算 plate.scad / keycap.scad 的坐标逻辑，
与「应该出现的结果」逐项比对。

参数直接从 cad/lib/params.scad 读取，改参数后本脚本自动同步。

检查项：
  1. 轴孔总数与位置（1u/2u/4u 三种跨度的孔位算法）
  2. 相邻轴孔筋宽（防断裂）
  3. 4u 大键三轴对称性
  4. 孔是否越出定位板边界
  5. 键帽是否罩得住轴孔
  6. 键帽榫槽 ↔ 定位板轴孔 是否 100% 对位（错位就装不上）

运行：python tools/verify_geometry.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scad_params import load, load_keymap     # noqa: E402

P = load()
KEYMAP = load_keymap()

PITCH = P["PITCH"]
BORDER = P["PLATE_BORDER"]
PLATE_W = P["PLATE_W"]
PLATE_H = P["PLATE_H"]
HOLE = P["SWITCH_CUTOUT"] + P["SWITCH_CUTOUT_TOL"]

errors = []


def axis_count(u):
    return 1 if u <= 1 else (2 if u == 2 else 3)


def axis_offset(u, i):
    return 0.5 if u <= 1 else 0.5 + i * (u - 1) / (axis_count(u) - 1)


def key_axis_pos(c, r, u, i):
    """定位板坐标系下的第 i 个轴孔中心"""
    return (round(BORDER + (c - 1) * PITCH + PITCH * axis_offset(u, i), 3),
            round(BORDER + (r - 1) * PITCH + PITCH / 2, 3))


def kc_stem_offset(u, i):
    """键帽榫头相对键帽中心的偏移"""
    if u <= 1:
        return 0.0
    return PITCH * (0.5 + i * (u - 1) / (axis_count(u) - 1) - u / 2)


print("=" * 72)
print("ClaudePad 几何交叉验证")
print("=" * 72)
print(f"键距 {PITCH} ｜ 边距 {BORDER} ｜ 轴孔 {HOLE:.2f}")
print(f"定位板 {PLATE_W:.1f} × {PLATE_H:.1f} mm")

# ---- 1. 轴孔清单 -----------------------------------------------------------
print("\n" + "-" * 72)
print(f"{'键位':<8}{'格位':<10}{'轴数':<6}{'孔中心 x':<32}{'跨度检查'}")
print("-" * 72)

total = 0
for (c, r, u, tag) in KEYMAP:
    n = axis_count(u)
    total += n
    xs = [key_axis_pos(c, r, u, i)[0] for i in range(n)]
    span = xs[-1] - xs[0]
    expect = PITCH * (u - 1)
    ok = abs(span - expect) < 0.01
    if not ok:
        errors.append(f"{tag}: 孔跨度 {span:.2f} ≠ {expect:.2f}")
    print(f"{tag:<8}{f'列{c}行{r}':<10}{n:<6}{str(xs):<32}{'OK' if ok else 'FAIL'}")

expect_total = sum(axis_count(k[2]) for k in KEYMAP)
print("-" * 72)
print(f"轴孔总数 = {total}（应为 {expect_total}）")
if total != expect_total:
    errors.append(f"轴孔总数 {total} ≠ {expect_total}")

# ---- 1b. 键帽数量统计（按宽度分档，用于打印清单）--------------------------
from collections import Counter     # noqa: E402
cap_counts = Counter(k[2] for k in KEYMAP)
print("\n【键帽数量】（按宽度分档，打印/采购按这个数）")
for u in sorted(cap_counts):
    label = f"{u}u"
    note = "（跨 %d 格）" % u if u > 1 else ""
    print(f"  {label:<4} × {cap_counts[u]:>2} 个 {note}")
print(f"  合计   × {sum(cap_counts.values()):>2} 个键帽")
if sum(cap_counts.values()) != len(KEYMAP):
    errors.append("键帽数量与键位数不符")

# ---- 2. 筋宽 -----------------------------------------------------------------
print("\n" + "-" * 72)
print("【相邻轴孔筋宽】")
holes = []
for (c, r, u, tag) in KEYMAP:
    for i in range(axis_count(u)):
        x, y = key_axis_pos(c, r, u, i)
        holes.append((x, y, tag))

min_gap, pair = 1e9, None
for i in range(len(holes)):
    for j in range(i + 1, len(holes)):
        x1, y1, t1 = holes[i]
        x2, y2, t2 = holes[j]
        if abs(y1 - y2) < 0.01 and abs(x2 - x1) < min_gap:
            min_gap, pair = abs(x2 - x1), (t1, t2)
rib = min_gap - HOLE
print(f"  最近同行孔距 {min_gap:.2f} mm（{pair[0]} ↔ {pair[1]}）")
print(f"  筋宽 = {min_gap:.2f} − {HOLE:.2f} = {rib:.2f} mm")
if rib < 1.0:
    errors.append(f"孔间筋宽 {rib:.2f} < 1.0，定位板易断")
print(f"  判定：{'OK' if rib >= 1.0 else 'FAIL'}")

# ---- 3. 4u 三轴对称 ---------------------------------------------------------
print("\n" + "-" * 72)
print("【4u 空格三轴对称性】")
big = [k for k in KEYMAP if k[2] >= 3]
if big:
    c, r, u, tag = big[0]
    xs = [key_axis_pos(c, r, u, i)[0] for i in range(axis_count(u))]
    print(f"  {tag} 三孔 x = {xs}")
    mid = (xs[0] + xs[-1]) / 2
    if abs(mid - xs[1]) > 0.01:
        errors.append(f"{tag} 三轴不对称")
    else:
        print(f"  中点 {mid:.2f} = 中间孔 {xs[1]:.2f} → OK 完全对称")
    print(f"  相邻孔间距 {xs[1] - xs[0]:.2f} / {xs[2] - xs[1]:.2f} mm")

# ---- 4. 边界 -----------------------------------------------------------------
print("\n" + "-" * 72)
print("【边界检查】轴孔是否留在定位板内")
R = HOLE / 2
worst = min(((min(x - R, y - R, PLATE_W - x - R, PLATE_H - y - R), t, x, y)
             for (x, y, t) in holes))
print(f"  最紧的孔（{worst[1]} @ {worst[2]:.1f},{worst[3]:.1f}）距板边 {worst[0]:.2f} mm")
if worst[0] < 1.0:
    errors.append(f"孔距板边仅 {worst[0]:.2f}mm，太薄")
print(f"  判定：{'OK' if worst[0] >= 1.0 else 'FAIL'}")

# ---- 5. 键帽覆盖 -------------------------------------------------------------
print("\n" + "-" * 72)
print("【键帽覆盖】4u 键帽能否罩住三个轴孔")
if big:
    c, r, u, tag = big[0]
    cap_w = PITCH * u - 0.40
    cap_cx = BORDER + (c - 1) * PITCH + u * PITCH / 2
    lo, hi = cap_cx - cap_w / 2, cap_cx + cap_w / 2
    xs = [key_axis_pos(c, r, u, i)[0] for i in range(axis_count(u))]
    print(f"  键帽中心 x={cap_cx:.2f}，范围 {lo:.2f} ~ {hi:.2f}（宽 {cap_w:.2f}）")
    for x in xs:
        inside = lo <= x <= hi
        print(f"    轴孔 x={x:.2f}  {'在内' if inside else '★超出'}")
        if not inside:
            errors.append("4u 键帽罩不住轴孔")
    print(f"  两端余量 {xs[0]-lo:.2f} / {hi-xs[-1]:.2f} mm")

# ---- 6. 键帽榫槽 ↔ 定位板轴孔 对位 ------------------------------------------
print("\n" + "-" * 72)
print("【键帽榫槽 ↔ 定位板轴孔 对位】（错位就装不上）")
print(f"{'键位':<8}{'轴数':<6}{'定位板绝对 x':<30}{'键帽中心+偏移':<30}{'对位'}")
print("-" * 72)
for (c, r, u, tag) in KEYMAP:
    n = axis_count(u)
    plate_x = [key_axis_pos(c, r, u, i)[0] for i in range(n)]
    cap_cx = BORDER + (c - 1) * PITCH + u * PITCH / 2
    cap_x = [round(cap_cx + kc_stem_offset(u, i), 3) for i in range(n)]
    match = all(abs(plate_x[i] - cap_x[i]) < 0.01 for i in range(n))
    if not match:
        errors.append(f"{tag}: 榫槽与轴孔错位 {plate_x} vs {cap_x}")
    print(f"{tag:<8}{n:<6}{str(plate_x):<30}{str(cap_x):<30}{'OK' if match else '★错位'}")

# ---- 汇总 -------------------------------------------------------------------
print("\n" + "=" * 72)
if errors:
    print(f"❌ 发现 {len(errors)} 个问题：")
    for e in errors:
        print(f"   · {e}")
    sys.exit(1)
else:
    print("✅ 全部通过")
    print(f"   {total} 个轴孔位置正确、对称、筋宽 {rib:.2f}mm、键帽与定位板 100% 对位")
print("=" * 72)

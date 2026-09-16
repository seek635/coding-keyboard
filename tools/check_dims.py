# -*- coding: utf-8 -*-
"""
ClaudePad 设计规则校验
----------------------
从 cad/lib/params.scad 读取真实参数（不硬编码副本），逐条验证结构约束。

这些规则来自实际设计过程中踩过的坑：
  · 内腔高度写死导致轴体够不到 PCB（致命）
  · 定位板宽度算错 12mm
  · 螺丝柱撞穿轴孔
  · 拨杆挡墙比内腔还高，顶到定位板
  · 轴芯太长，捅穿键帽顶面
  · 螺母没有咬合长度

运行：python tools/check_dims.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scad_params import load, load_keymap     # noqa: E402

P = load()
KM = load_keymap()

results = []


def chk(name, ok, detail, fix=""):
    results.append((name, ok, detail, fix))


def f(v):
    return f"{v:.2f}"


# =============================================================================
print("=" * 72)
print("ClaudePad 设计规则校验")
print("=" * 72)

# ---- 1. 垂直尺寸链 ----------------------------------------------------------
plate_bottom_z = P["CASE_BOTTOM_T"] + P["CASE_INNER_H"]
plate_top_z = plate_bottom_z + P["PLATE_T"]
pcb_bottom_z = P["CASE_BOTTOM_T"] + P["PCB_STANDOFF_H"]
pcb_top_z = pcb_bottom_z + P["PCB_T"]
switch_tip_z = pcb_top_z + P["SWITCH_TOP_ABOVE_PCB"]
cap_bottom_z = plate_top_z + P["CAP_GAP"]
cap_top_z = cap_bottom_z + P["CAP_H"]

print("\n【垂直尺寸链】（z=0 为底板上表面）")
rows = [
    ("底板上表面", 0.0),
    ("PCB 下表面", P["PCB_STANDOFF_H"]),
    ("PCB 上表面", P["PCB_STANDOFF_H"] + P["PCB_T"]),
    ("定位板下表面", P["CASE_INNER_H"]),
    ("定位板上表面", P["CASE_INNER_H"] + P["PLATE_T"]),
    ("轴芯顶面", P["PCB_STANDOFF_H"] + P["PCB_T"] + P["SWITCH_TOP_ABOVE_PCB"]),
    ("键帽底面", cap_bottom_z - P["CASE_BOTTOM_T"]),
    ("键帽顶面", cap_top_z - P["CASE_BOTTOM_T"]),
]
for label, z in rows:
    print(f"  {label:<14} z = {f(z):>7} mm")

# 关键：内腔高度必须等于堆叠之和
expected_inner = P["PCB_STANDOFF_H"] + P["PCB_T"] + P["SWITCH_PLATE_GAP"]
chk("内腔高度 = 支撑台+PCB+卡扣间隙",
    abs(P["CASE_INNER_H"] - expected_inner) < 0.001,
    f"{f(P['CASE_INNER_H'])} vs {f(expected_inner)}",
    "改 CASE_INNER_H 的推导式，不要写死")

# 轴体必须能从定位板够到 PCB
chk("轴体跨越定位板到PCB的间隙合理",
    0.5 <= P["SWITCH_PLATE_GAP"] <= 6.0,
    f"SWITCH_PLATE_GAP = {f(P['SWITCH_PLATE_GAP'])} mm",
    "超出 0.5~6.0 说明参数异常，用 test_coupon.scad 实测")

# ---- 2. 键帽与轴芯配合（含按键行程！）--------------------------------------
print("\n【键帽配合与按键行程】")
tip_above_plate = P["SWITCH_TOP_ABOVE_PCB"] - P["SWITCH_PLATE_GAP"] - P["PLATE_T"]
reach = P["CAP_GAP"] + P["CAP_STEM_DEPTH"]
travel = P["SWITCH_TRAVEL"]

print(f"  键帽底面离定位板顶面 : {f(P['CAP_GAP'])} mm")
print(f"  轴体键程（按下深度） : {f(travel)} mm")
print(f"  → 可用行程 = min(键帽间隙, 键程) = {f(min(P['CAP_GAP'], travel))} mm")

# ★ 最关键的一条：键帽裙边比定位板轴孔宽，塞不进孔里，
#   所以键帽必须能整体下移一个完整键程而不撞到定位板。
chk("键帽能按下完整键程（不撞定位板）",
    P["CAP_GAP"] >= travel,
    f"间隙 {f(P['CAP_GAP'])} ≥ 键程 {f(travel)}",
    "键帽会按不动！CAP_GAP 必须 ≥ SWITCH_TRAVEL（改 CAP_GAP_MARGIN 或 SWITCH_TRAVEL）")

skirt = P["PITCH"] - 0.40
print(f"  键帽裙边宽度         : {f(skirt)} mm")
print(f"  定位板轴孔宽度       : {f(P['SWITCH_CUTOUT'])} mm")
print(f"  → 裙边比孔宽 {f(skirt - P['SWITCH_CUTOUT'])} mm，只能悬在板上方（这是上面那条约束的由来）")

print(f"  轴芯高出定位板顶面   : {f(tip_above_plate)} mm")
print(f"  键帽可容纳深度       : 间隙 {f(P['CAP_GAP'])} + 榫槽 {f(P['CAP_STEM_DEPTH'])} = {f(reach)} mm")
chk("轴芯能插进榫槽（不捅穿键帽顶面）",
    tip_above_plate <= reach,
    f"{f(tip_above_plate)} ≤ {f(reach)}",
    "增大 CAP_STEM_DEPTH 或 CAP_GAP，或减小 SWITCH_PLATE_GAP")

chk("榫槽有足够咬合深度",
    P["CAP_STEM_DEPTH"] >= 2.0,
    f"CAP_STEM_DEPTH = {f(P['CAP_STEM_DEPTH'])} mm",
    "小于 2mm 键帽容易掉")

chk("键帽底面高于定位板顶面",
    P["CAP_GAP"] > 0,
    f"CAP_GAP = {f(P['CAP_GAP'])} mm",
    "等于 0 或负数会导致键帽压住定位板")

# ---- 3. 定位板 / 外壳 / PCB 尺寸 -------------------------------------------
print("\n【平面尺寸】")
plate_w, plate_h = P["PLATE_W"], P["PLATE_H"]
case_w = plate_w + P["CASE_TOP_TOL"] * 2 + P["CASE_WALL"] * 2
case_d = plate_h + P["CASE_TOP_TOL"] * 2 + P["CASE_WALL"] * 2
print(f"  网格        : {f(P['GRID_W'])} × {f(P['GRID_H'])} mm")
print(f"  定位板      : {f(plate_w)} × {f(plate_h)} × {f(P['PLATE_T'])} mm")
print(f"  底座外形    : {f(case_w)} × {f(case_d)} × {f(P['CASE_OUTER_H'])} mm")
print(f"  PCB         : {f(P['PCB_W'])} × {f(P['PCB_H'])} mm")
print(f"  整机总高    : {f(P['TOTAL_H'])} mm")

chk("定位板宽度 = 网格 + 两侧边距",
    abs(plate_w - (P["GRID_W"] + P["PLATE_BORDER"] * 2)) < 0.001,
    f"{f(plate_w)} mm")

chk("PCB 能覆盖全部轴位",
    P["PCB_W"] >= P["GRID_W"] - 6 and P["PCB_H"] >= P["GRID_H"] - 6,
    f"PCB {f(P['PCB_W'])}×{f(P['PCB_H'])} vs 网格 {f(P['GRID_W'])}×{f(P['GRID_H'])}",
    "PCB 太小会导致边缘轴体没有焊盘")

# ---- 4. 螺丝柱 vs 轴孔 干涉 ------------------------------------------------
print("\n【螺丝柱与轴孔干涉】")
hole_half = (P["SWITCH_CUTOUT"] + P["SWITCH_CUTOUT_TOL"]) / 2
hole_near = P["PLATE_BORDER"] + P["PITCH"] / 2 - hole_half
post_far = P["SCREW_INSET"] + P["POST_D"] / 2
clearance = hole_near - post_far
print(f"  最靠边的轴孔近边距定位板边 : {f(hole_near)} mm")
print(f"  螺丝柱外缘距定位板边       : {f(post_far)} mm")
print(f"  余量                       : {f(clearance)} mm")
chk("螺丝柱不撞轴孔", clearance >= 0.8,
    f"余量 {f(clearance)} mm",
    "增大 PLATE_BORDER 或减小 POST_D / SCREW_INSET")

# ---- 5. 拨杆安装 ------------------------------------------------------------
print("\n【拨杆安装】")
print("  安装方式：拨杆+轴套+螺母在壳外，开关本体在壳内")
boss_outer = P["CASE_WALL"] + P["SW_BOSS_T"] + P["SW_NUT_T"]
print(f"  壁厚 + 凸台 + 螺母 : {f(P['CASE_WALL'])} + {f(P['SW_BOSS_T'])} + {f(P['SW_NUT_T'])} = {f(boss_outer)} mm")
print(f"  轴套长度           : {f(P['SW_BUSH_H'])} mm")
chk("轴套足够长，能穿过 壁+凸台+螺母",
    boss_outer <= P["SW_BUSH_H"] - 0.4,
    f"{f(boss_outer)} ≤ {f(P['SW_BUSH_H'] - 0.4)}",
    "换更长的轴套，或减小 SW_BOSS_T")

# 凸台不能超出外壳高度（否则会从顶/底穿出）
sw_z = P["CASE_BOTTOM_T"] + P["CASE_INNER_H"] * 0.55
boss_lo = sw_z - P["SW_BOSS_D"] / 2
boss_hi = sw_z + P["SW_BOSS_D"] / 2
print(f"  凸台 z 范围        : {f(boss_lo)} ~ {f(boss_hi)}（外壳 0 ~ {f(P['CASE_OUTER_H'])}）")
chk("拨杆凸台不穿出外壳",
    boss_lo > 0 and boss_hi < P["CASE_OUTER_H"],
    f"{f(boss_lo)} > 0 且 {f(boss_hi)} < {f(P['CASE_OUTER_H'])}",
    "减小 SW_BOSS_D 或调整 SW_Z 的系数")

# 拨杆本体不能撞 PCB
sw_body_in = P["CASE_WALL"] + P["SW_BODY_D"]     # 从内壁向内的侵入深度
pcb_edge = P["CASE_WALL"] + P["PCB_X"] + P["PCB_W"]
print(f"  本体侵入深度       : {f(sw_body_in)} mm（从内壁算起）")
print(f"  PCB 右缘距内壁     : {f(pcb_edge)} mm")
print(f"  → PCB 右侧需开缺口 : PCB_NOTCH_D = {f(P['PCB_NOTCH_D'])} mm")
chk("已为拨杆本体预留 PCB 缺口",
    P["PCB_NOTCH_D"] >= 4.0,
    f"缺口深 {f(P['PCB_NOTCH_D'])} mm",
    "缺口太小会导致拨杆本体压到 PCB")

# ---- 6. 电池 ----------------------------------------------------------------
print("\n【电池空间】")
avail = P["PCB_STANDOFF_H"]                      # PCB 下方净高
need = P["BATT_TAPE_T"] + P["BATT_H"]            # 胶 + 电池
print(f"  PCB 下方净高        : {f(avail)} mm")
print(f"  胶 + 电池占用        : {f(P['BATT_TAPE_T'])} + {f(P['BATT_H'])} = {f(need)} mm")
chk("电池能放进 PCB 下方",
    need <= P["PCB_STANDOFF_H"],
    f"{f(need)} ≤ {f(P['PCB_STANDOFF_H'])}",
    "增大 PCB_STANDOFF_H 或换更薄的电池")

batt_area = P["BATT_W"] * P["BATT_L"]
pcb_area = P["PCB_W"] * P["PCB_H"]
cavity = (P["PLATE_W"]) * (P["PLATE_H"])
print(f"  电池投影面积 : {f(batt_area)} mm² ｜ PCB : {f(pcb_area)} mm² ｜ 内腔 : {f(cavity)} mm²")
chk("电池与 PCB 在平面内不重叠（电池走 PCB 正下方）",
    batt_area < cavity * 0.6,
    f"电池占内腔 {batt_area / cavity * 100:.0f}%",
    "占比过高会导致元器件没地方放")

# ---- 7. 主控在腔内的净空 ----------------------------------------------------
# ★ 重要耦合：PCB 上表面到定位板下表面的空间 = SWITCH_PLATE_GAP
#   也就是说「轴体卡扣间隙」和「主控可用高度」是同一个尺寸，必须同时满足
print("\n【主控净空】（注意：这个空间 = SWITCH_PLATE_GAP，与轴体共用）")
space_above_pcb = P["SWITCH_PLATE_GAP"]
print(f"  PCB 上表面到定位板下表面 : {f(space_above_pcb)} mm")
print(f"  主控板+元件高度          : {f(P['NANO_H'])} mm（直焊方案，不用普通排母）")
print(f"  余量                     : {f(space_above_pcb - P['NANO_H'])} mm")
chk("轴体间隙同时满足主控净空",
    space_above_pcb >= P["NANO_H"] + 0.30,
    f"{f(space_above_pcb)} ≥ {f(P['NANO_H'] + 0.30)}",
    "间隙太小 → 主控放不下。必须把主控改成 PCB 底面安装，或加大间隙并重验轴体")

# ---- 8. 空格大键挠度 --------------------------------------------------------
# 按「无加强筋」的最坏情况估算（只有顶面承力），保守
print("\n【4u 空格挠度】（按无加强筋的最坏情况估算）")
E_PLA = 2400.0
L = 4 * P["PITCH"] - 0.4                 # 键帽跨度
b = P["PITCH"] - 0.4                     # 有效宽度
t = P["CAP_TOP_T"]                       # 有效厚度（只算顶面，不算筋）
I = b * t ** 3 / 12
F = 3.0                                  # 单点按压力 3N
d_single = F * L ** 3 / (48 * E_PLA * I)
d_triple = F * (L / 2) ** 3 / (48 * E_PLA * I)
print(f"  跨度 {f(L)} mm ｜ 有效截面 {f(b)} × {f(t)} mm")
print(f"  单轴支撑中点挠度 : {f(d_single)} mm")
print(f"  三轴并联中点挠度 : {f(d_triple)} mm（跨度等效减半 → 挠度约 1/8）")
chk("空格三轴支撑挠度可接受", d_triple < 0.5,
    f"{f(d_triple)} mm",
    "超过 0.5mm 需加厚顶面 / 增加加强筋 / 增加轴数")
chk("空格不能只靠单轴支撑", d_single > 0.5,
    f"单轴 {f(d_single)} mm > 0.5，必须三轴并联",
    "这是三轴方案的依据")

# ---- 9. 轴孔间距 ------------------------------------------------------------
print("\n【轴孔间距】")
gap = P["PITCH"] - (P["SWITCH_CUTOUT"] + P["SWITCH_CUTOUT_TOL"])
print(f"  相邻轴孔净距 : {f(gap)} mm（= 间距 {f(P['PITCH'])} − 轴孔 {f(P['SWITCH_CUTOUT'] + P['SWITCH_CUTOUT_TOL'])}）")
chk("轴孔之间有足够筋宽", gap >= 3.0,
    f"{f(gap)} mm",
    "小于 3mm 定位板容易断裂")

# ---- 10. PCB 支撑台不能顶住轴体塑料脚 ---------------------------------------
# 轴体宽 13.5，间距 18 → 轴体之间只有 4.5mm 空隙。
# 支撑台必须落在空隙中央，且直径 < 空隙宽度，否则会顶住轴体的塑料脚。
print("\n【PCB 支撑台与轴体脚的干涉】")
SW_BODY_W = 13.50                     # Choc 轴体宽（比定位板孔 13.9 小）
sw_gap = P["PITCH"] - SW_BODY_W       # 轴体之间的净空隙
sup_d = P["PCB_SUPPORT_D"]
print(f"  轴体宽            : {f(SW_BODY_W)} mm")
print(f"  轴体间净空隙      : {f(sw_gap)} mm（= 间距 {f(P['PITCH'])} − 轴体宽 {f(SW_BODY_W)}）")
print(f"  支撑台直径        : {f(sup_d)} mm")

# 第一个轴体中心（PCB 坐标系）= (PLATE_BORDER + PITCH/2) − PCB_X
first = P["PLATE_BORDER"] + P["PITCH"] / 2 - (P["PLATE_W"] - P["PCB_W"]) / 2
valid_x = {round(first + P["PITCH"] / 2 + i * P["PITCH"], 2) for i in range(4)}
valid_y = {round(first + P["PITCH"] / 2 + i * P["PITCH"], 2) for i in range(2)}
print(f"  合法的空隙中心 x  : {sorted(valid_x)}")
print(f"  合法的空隙中心 y  : {sorted(valid_y)}")
for name, v in [("X1", P["PCB_SUPPORT_X1"]), ("X2", P["PCB_SUPPORT_X2"])]:
    chk(f"支撑台 {name} 落在列间隙中心", round(v, 2) in valid_x,
        f"{f(v)}", f"应取 {sorted(valid_x)} 之一")
for name, v in [("Y1", P["PCB_SUPPORT_Y1"]), ("Y2", P["PCB_SUPPORT_Y2"])]:
    chk(f"支撑台 {name} 落在行间隙中心", round(v, 2) in valid_y,
        f"{f(v)}", f"应取 {sorted(valid_y)} 之一")
chk("支撑台直径小于轴体间隙", sup_d < sw_gap,
    f"{f(sup_d)} < {f(sw_gap)}",
    "支撑台太粗会顶住轴体塑料脚，装不进去")

# ---- 11. 主控必须放得下（板面被轴体占满就会放不下）--------------------------
# 这是「设计能做出来」与「做不出来」的分界线：
# 14 个轴体本体几乎占满 86×50 的板面，主控（17.8×33）可能根本无处可放。
print("\n【主控放置可行性】")
NANO_W, NANO_L = P["NANO_W"], P["NANO_L"]
PCB_W, PCB_H = P["PCB_W"], P["PCB_H"]
PCB_OFF = (P["PLATE_W"] - PCB_W) / 2      # 定位板坐标 → PCB 坐标 的偏移

n_sw = lambda u: 1 if u <= 1 else (2 if u == 2 else 3)

sw_pos = []
for (c, r, u, tag) in KM:
    for i in range(n_sw(u)):
        if u <= 1:
            px = P["PLATE_BORDER"] + (c - 1) * P["PITCH"] + P["PITCH"] * 0.5
        else:
            px = (P["PLATE_BORDER"] + (c - 1) * P["PITCH"]
                  + P["PITCH"] * (0.5 + i * (u - 1) / (n_sw(u) - 1)))
        py = P["PLATE_BORDER"] + (r - 1) * P["PITCH"] + P["PITCH"] / 2
        sw_pos.append((tag, round(px - PCB_OFF, 2), round(py - PCB_OFF, 2)))

_h = SW_BODY_W / 2


def _overlap(nx, ny):
    """主控矩形与所有轴体本体的重叠面积（mm²）"""
    tot = 0.0
    for (_, sx, sy) in sw_pos:
        ox = max(0.0, min(sx + _h, nx + NANO_W) - max(sx - _h, nx))
        oy = max(0.0, min(sy + _h, ny + NANO_L) - max(sy - _h, ny))
        tot += ox * oy
    return tot


# 主控安装面：方案 A（2026-09-16）后装在 PCB 背面（下表面）
on_back = P.get("NANO_ON_BACK", False)
NANO_X = P.get("NANO_POS_X", PCB_W - 3.0 - NANO_W)
NANO_Y = P.get("NANO_POS_Y", PCB_H - 3.0 - NANO_L)
CIW = P["PLATE_W"] + P["CASE_TOP_TOL"] * 2
CID = P["PLATE_H"] + P["CASE_TOP_TOL"] * 2

print(f"  板面       : {f(PCB_W)} × {f(PCB_H)} mm")
print(f"  主控       : {f(NANO_W)} × {f(NANO_L)} mm（{f(P['NANO_H'])} 厚）")
print(f"  轴体本体   : {f(SW_BODY_W)} mm 见方 × {len(sw_pos)} 个")
print(f"  安装面     : {'PCB 背面（下表面）' if on_back else 'PCB 正面（上表面）'}")
print(f"  设计位置   : ({f(NANO_X)}, {f(NANO_Y)})  [PCB 坐标]")

if not on_back:
    # ---- 正面：与轴体争板面 ----
    cur = _overlap(NANO_X, NANO_Y)
    print(f"  与轴体重叠 : {f(cur)} mm²")
    chk("主控在板面上不与轴体重叠", cur == 0,
        f"重叠 {f(cur)} mm²",
        "主控必须移到 PCB 背面，或改用更小的主控模块（见 docs/PCB设计规格书.md §14）")

    # 穷举板面，看还有没有别的位置
    valid = 0
    _x = 0.0
    while _x <= PCB_W - NANO_W + 0.01:
        _y = 0.0
        while _y <= PCB_H - NANO_L + 0.01:
            if _overlap(round(_x, 1), round(_y, 1)) == 0:
                valid += 1
            _y += 0.5
        _x += 0.5
    chk("板面上存在可放置主控的位置", valid > 0,
        f"共 {valid} 个候选位（步长 0.5mm）",
        "板面被轴体占满 —— 主控只能放 PCB 背面（需同步挪支撑台、下移 USB 开孔）")
else:
    # ---- 背面：与电池、支撑台共用同一层，必须互不干涉 ----
    b_x0 = -P["PCB_X"]                              # 电池贴内腔左壁
    b_y0 = (CID - P["BATT_L"]) / 2 - P["PCB_Y"]     # 纵向居中
    b_x1, b_y1 = b_x0 + P["BATT_W"], b_y0 + P["BATT_L"]
    _ox = max(0.0, min(b_x1, NANO_X + NANO_W) - max(b_x0, NANO_X))
    _oy = max(0.0, min(b_y1, NANO_Y + NANO_L) - max(b_y0, NANO_Y))
    batt_ov = _ox * _oy
    print(f"  电池       : x {f(b_x0)}~{f(b_x1)}  y {f(b_y0)}~{f(b_y1)}  [PCB 坐标]")
    chk("主控在背面不与电池重叠", batt_ov == 0,
        f"重叠 {f(batt_ov)} mm²",
        "电池需让位到另一侧，或改用更小的电池")

    _r = P["PCB_SUPPORT_D"] / 2
    sup_hit = []
    for sx in (P["PCB_SUPPORT_X1"], P["PCB_SUPPORT_X2"]):
        for sy in (P["PCB_SUPPORT_Y1"], P["PCB_SUPPORT_Y2"]):
            if (sx + _r > NANO_X and sx - _r < NANO_X + NANO_W
                    and sy + _r > NANO_Y and sy - _r < NANO_Y + NANO_L):
                sup_hit.append(f"({f(sx)},{f(sy)})")
    chk("主控在背面不与支撑台重叠", not sup_hit,
        "无冲突" if not sup_hit else f"冲突 {len(sup_hit)} 个：{' '.join(sup_hit)}",
        "支撑台必须挪到不被主控覆盖的轴体间隙中心")

# 背面可行性：层高够不够
back_ok = P["NANO_H"] <= P["PCB_STANDOFF_H"]
chk("主控厚度能放进 PCB 下方层", back_ok,
    f"{f(P['NANO_H'])} ≤ {f(P['PCB_STANDOFF_H'])} mm"
    f"（余 {f(P['PCB_STANDOFF_H'] - P['NANO_H'])}）",
    "改用更薄的主控或加高 PCB 支撑台")

# ---- 汇总 -------------------------------------------------------------------
print("\n" + "=" * 72)
failed = [r for r in results if not r[1]]
for name, ok, detail, fix in results:
    mark = "✅" if ok else "❌"
    print(f"{mark} {name:<34} {detail}")
    if not ok and fix:
        print(f"   └ 建议：{fix}")

print("=" * 72)
if failed:
    print(f"❌ {len(failed)} / {len(results)} 项未通过")
    sys.exit(1)
else:
    print(f"✅ 全部 {len(results)} 项设计规则通过")
    print(f"   整机 {f(case_w)} × {f(case_d)} × {f(P['TOTAL_H'])} mm")
    print(f"   ⚠️ 唯一需实物确认的参数：SWITCH_PLATE_GAP = {f(P['SWITCH_PLATE_GAP'])} mm")
    print("      → 先打 cad/test_coupon.scad 校准")

// =============================================================================
// ClaudePad · 定位板（轴板 / Switch Plate）
// -----------------------------------------------------------------------------
// 功能：为 11 个键（含回车 2u、空格 4u）提供轴体卡扣定位。
//
// 尺寸基准：定位板左下角为 (0,0)，网格从 (PLATE_BORDER, PLATE_BORDER) 起。
// 公差核心：轴孔 13.8mm 是 Choc 官方值，3D 打印需 +0.10 补偿。
//
// 用途：单独打印验证布局与轴孔松紧 → 确认无误后再打整体底座。
// =============================================================================

include <lib/params.scad>

// ---------- 派生尺寸 ------------------------------------------------------
PLATE_W = GRID_W + PLATE_BORDER * 2;    // = 90 + 12 = 102.0
PLATE_H = GRID_H + PLATE_BORDER * 2;    // = 54 + 12 = 66.0

// ---------- 轴孔位置（统一算法）------------------------------------------
// 一个键宽 u 格，内部放 n 个轴，用同一套公式：
//   1u → 1 个；2u → 2 个；≥3u → 3 个（左中右）
// 第 i 个轴相对键左缘的偏移 = PITCH * axis_offset(u, i)
function axis_count(u) = (u <= 1) ? 1 : ((u == 2) ? 2 : 3);
function axis_offset(u, i) =
    (u <= 1) ? 0.5 : 0.5 + i * (u - 1) / (axis_count(u) - 1);

// 第 i 个轴孔中心（定位板坐标系）
function key_axis_pos(c, r, u, i) = [
    PLATE_BORDER + (c - 1) * PITCH + PITCH * axis_offset(u, i),
    PLATE_BORDER + (r - 1) * PITCH + PITCH / 2
];

// ---------- 单个轴孔 ------------------------------------------------------
// Choc 轴孔：主方孔 + 左右两个侧卡扣槽
module choc_cutout() {
    s = SWITCH_CUTOUT + SWITCH_CUTOUT_TOL;
    linear_extrude(height = PLATE_T + 2, center = true) {
        square([s, s], center = true);
        for (sx = [-1, 1]) {
            translate([sx * (s / 2 + SWITCH_CLIP_H / 2), 0])
                square([SWITCH_CLIP_H * 2, SWITCH_CLIP_W], center = true);
        }
    }
}

// ---------- 定位板本体 ----------------------------------------------------
module switch_plate() {
    difference() {
        // 外形：圆角矩形
        linear_extrude(height = PLATE_T)
            offset(r = CAP_TOP_R) offset(delta = -CAP_TOP_R)
                square([PLATE_W, PLATE_H]);

        // 所有轴孔
        for (k = KEYMAP) {
            c = k[0]; r = k[1]; u = k[2];
            for (i = [0 : axis_count(u) - 1]) {
                p = key_axis_pos(c, r, u, i);
                translate([p[0], p[1], -1]) choc_cutout();
            }
        }

        // 四角螺丝通孔（与底座螺丝柱对位）
        for (px = [0, 1], py = [0, 1]) {
            translate([
                px == 0 ? SCREW_INSET : PLATE_W - SCREW_INSET,
                py == 0 ? SCREW_INSET : PLATE_H - SCREW_INSET,
                -1
            ]) cylinder(d = SCREW_M2_CLEAR, h = PLATE_T + 2);
        }
    }
}

// ---------- 渲染 ----------------------------------------------------------
switch_plate();

// ---------- 尺寸自检 -------------------------------------------------------
echo(str("定位板外形 = ", PLATE_W, " × ", PLATE_H, " × ", PLATE_T, " mm"));
echo(str("网格 = ", GRID_W, " × ", GRID_H, " mm，边距 ", PLATE_BORDER, " mm"));

// ---------- 打印建议 -------------------------------------------------------
// 方向：平放打印（孔轴线垂直于热床），无需支撑
// 层高：0.16mm（1.2mm 厚 = 8 层，别用 0.2 否则只有 6 层）
// 壁数：3 圈
// 填充：40%（受力件）
// 注意：打印后务必用实物轴体试装，过紧用刀修，过松需重打

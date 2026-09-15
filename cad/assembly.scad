// =============================================================================
// ClaudePad · 总装与导出 (assembly.scad)
// -----------------------------------------------------------------------------
// 用途：
//   1. 爆炸视图预览（检查装配关系与干涉）
//   2. 一键导出所有零件（配合 OpenSCAD CLI 或 tools/export_stl.py）
//
// 命令行导出示例（在 cad/ 目录执行）：
//   openscad -o output/01_case_bottom.stl case_bottom.scad
//   openscad -o output/02_plate.stl plate.scad
//   openscad -D 'keycap_mode="1u"' -o output/03_keycap_1u.stl keycap.scad
//   openscad -D 'keycap_mode="2u"' -o output/04_keycap_2u.stl keycap.scad
//   openscad -D 'keycap_mode="4u"' -o output/05_keycap_4u.stl keycap.scad
//   openscad -o output/06_test_coupon.stl test_coupon.scad
// =============================================================================

include <lib/params.scad>
use <plate.scad>
use <case_bottom.scad>
use <keycap.scad>

// ---------- 派生高度（与各零件保持一致）----------------------------------
CASE_INNER_W = PLATE_W + CASE_TOP_TOL * 2;
CASE_INNER_D = PLATE_H + CASE_TOP_TOL * 2;
CASE_W = CASE_INNER_W + CASE_WALL * 2;
CASE_D = CASE_INNER_D + CASE_WALL * 2;

PLATE_BOTTOM_Z = CASE_BOTTOM_T + CASE_INNER_H;          // = 12.1
CAP_BOTTOM_Z = PLATE_BOTTOM_Z + PLATE_T + CAP_GAP;      // = 13.6
PCB_TOP_Z = CASE_BOTTOM_T + PCB_STANDOFF_H + PCB_T;     // = 8.6

// ---------- 装配预览 ------------------------------------------------------
module all_keycaps() {
    for (k = KEYMAP) {
        c = k[0]; r = k[1]; u = k[2];
        // 键帽中心 = 该键跨格范围中点（换算到外壳绝对坐标）
        translate([
            CASE_WALL + PLATE_BORDER + (c - 1) * PITCH + u * PITCH / 2,
            CASE_WALL + PLATE_BORDER + (r - 1) * PITCH + PITCH / 2,
            0
        ]) keycap(u);
    }
}

module assembly_exploded(explode = 0) {
    color("LightSteelBlue", 0.9) case_bottom();

    color("Khaki", 0.95)
        translate([CASE_WALL, CASE_WALL, PLATE_BOTTOM_Z + explode * 14])
            switch_plate();

    color("Salmon", 0.95)
        translate([0, 0, CAP_BOTTOM_Z + explode * 34])
            all_keycaps();
}

// ---------- 渲染控制 ------------------------------------------------------
VIEW = "explode";     // "explode" / "assembly" / "case" / "plate" / "caps"

if (VIEW == "explode") {
    assembly_exploded(1.0);
} else if (VIEW == "assembly") {
    assembly_exploded(0.0);
} else if (VIEW == "case") {
    case_bottom();
} else if (VIEW == "caps") {
    all_keycaps();
} else {
    switch_plate();
}

// ---------- 尺寸链自检（改参数后看这里）----------------------------------
echo("════════ ClaudePad 尺寸链 ════════");
echo(str("整机外形      : ", CASE_W, " × ", CASE_D, " × ", TOTAL_H, " mm"));
echo(str("底座          : ", CASE_W, " × ", CASE_D, " × ", CASE_OUTER_H, " mm"));
echo(str("定位板        : ", PLATE_W, " × ", PLATE_H, " × ", PLATE_T, " mm"));
echo(str("内腔净高      : ", CASE_INNER_H, " mm"));
echo(str("  ├ 电池/走线层 : ", PCB_STANDOFF_H, " mm"));
echo(str("  ├ PCB         : ", PCB_T, " mm"));
echo(str("  └ 轴体卡扣间隙: ", SWITCH_PLATE_GAP, " mm  ← 关键待验证"));
echo(str("定位板底面 z  : ", PLATE_BOTTOM_Z, " mm"));
echo(str("PCB 顶面   z  : ", PCB_TOP_Z, " mm"));
echo(str("键帽底面   z  : ", CAP_BOTTOM_Z, " mm"));
echo(str("键帽顶面   z  : ", CAP_BOTTOM_Z + CAP_H, " mm  ← 整机总高"));
echo(str("电池可用厚度  : ", PCB_STANDOFF_H - BATT_TAPE_T, " mm"));
echo(str("轴芯高出定位板: ", SWITCH_TIP_ABOVE_PLATE, " mm（榫槽深 ", CAP_STEM_DEPTH, " mm）"));

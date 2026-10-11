// =============================================================================
// ClaudePad · 焊接完成后的 PCB 组件 3D 模型 (pcb_assembly.scad)
// -----------------------------------------------------------------------------
// 与外壳（case_bottom.scad / plate.scad）同一套参数体系：include <lib/params.scad>
//
// 坐标：PCB 本地坐标系 —— 原点 = 板左下角，x 右 / y 上 / z 上（板顶面 z=0，板厚向下）
//   与 pcb/placement.csv 的 x_mm/y_mm 一致；数据勿手改，源头是 placement.csv
//   与 tools/gen_kicad.py 头注释。
//
// 用法（OpenSCAD 打开本文件）：
//   预览焊接进度：改 STEP = 0..5
//     0 裸板 → 1 +二极管 → 2 +排针/主控 → 3 +飞线/电池/开关 → 4 +轴体 → 5 +拨杆
//   与外壳一起看：改 VIEW = "in_case"（半透明外壳 + 装好板的组件）
//
// 预览步骤图（KiCad 引擎真实渲染）：docs/img/step0-bare.png … step5-final.png
// =============================================================================

include <lib/params.scad>
use <case_bottom.scad>

// ---------- 控制 ----------
STEP = 5;        // 0..5 焊接步骤
VIEW = "step";   // "step"（焊接步骤） / "in_case"（装进外壳）

// ---------- 颜色 ----------
C_PCB    = [0.18, 0.49, 0.29];
C_SWBASE = [0.24, 0.24, 0.28];
C_SWTOP  = [0.34, 0.34, 0.40];
C_STEM   = [0.30, 0.30, 0.35];
C_GLASS  = [0.78, 0.52, 0.16];
C_BAND   = [0.10, 0.10, 0.10];
C_GOLD   = [0.83, 0.69, 0.22];
C_BLACK  = [0.09, 0.09, 0.10];
C_NAVY   = [0.12, 0.23, 0.37];
C_SILVER = [0.75, 0.75, 0.78];
C_BATT   = [0.76, 0.78, 0.80];
C_RED    = [0.80, 0.20, 0.20];

// ---------- 数据（与 pcb/placement.csv / gen_kicad.py 同源）----------
// ⚠️ 本表是**副本**：改板后必须同步（或直接看 docs/焊接参考图.html ——
//    那个由 tools/render_assembly.py 从 placement.csv / 板文件生成，不会漂移）。
// [键名, x, y, 旋转°]（文档坐标，y 向上）
SWITCHES = [
    ["PERM", 13, 7, 0], ["UP", 31, 7, 0], ["MODEL", 49, 7, 0], ["CMD", 67, 7, 0], ["STOP", 85, 7, 270],
    ["LEFT", 13, 25, 0], ["DOWN", 31, 25, 0], ["RIGHT", 49, 25, 0], ["ENTER", 67, 25, 0], ["ENTER", 85, 25, 90],
    // ★ 2026-10-11（用户要求 · 第二次修正）：这一行 4 颗键贴左 —— 空格跨列 1-3（13/31/49），
    //   语音键第 5 列 → 第 4 列（67）；第 5 列（85）空出，主控区不再被轴体压住。
    ["SPACE", 13, 43, 0], ["SPACE", 31, 43, 0], ["SPACE", 49, 43, 0], ["VOICE", 67, 43, 180],
];
// 二极管中心 [x, y]（色环端/阴极一律朝 x 小的一侧）
DIODES = [
    [6, 16], [16.5, 16], [27, 16], [47.26, 16], [57.58, 16], [67.9, 16],
    [6, 34], [16.5, 34], [27, 34], [57.58, 34], [47.26, 34], [67.9, 34],
];
JP_XS  = [78.03, 93.27];      // 排针两列（主控左缘 76.76 + 1.27 / 右缘 94.54 − 1.27）
JP_Y0  = 14.82;               // 最低孔 y（= 主控 y0 13.56 + (33.00 − 30.48)/2）
JP_N   = 13;                  // 每列 13 孔（跨距 30.48 = 12 × 2.54）

// ---------- PCB 板（含右缘缺口）----------
module pcb_board() {
    color(C_PCB) difference() {
        translate([0, 0, -PCB_T]) cube([PCB_W, PCB_H, PCB_T]);
        translate([PCB_W - PCB_NOTCH_D, -0.1, -PCB_T - 0.1])
            cube([PCB_NOTCH_D + 0.1, PCB_NOTCH_Y1 + 0.1, PCB_T + 0.2]);
    }
}

// ---------- 轴体 Choc V2（原点=轴芯中心，PCB 顶面 z=0）----------
module choc_switch(rot) {
    rotate([0, 0, rot]) {
        color(C_SWBASE) translate([0, 0, 0.8]) cube([13.95, 13.95, 1.6], center = true);
        color(C_SWTOP)  translate([0, 0, 3.45]) cube([15, 15, 3.7], center = true);
        color(C_STEM) {
            translate([0, 0, 6.0]) cube([4.2, 1.3, 1.4], center = true);
            translate([0, 0, 6.0]) cube([1.3, 4.2, 1.4], center = true);
        }
        // 引脚穿板（2 电气 + 1 定位，官方坐标）
        color(C_SILVER) {
            translate([-3.8, 4.93, -1.1]) cylinder(h = 2.2, r = 0.6, center = true, $fn = 16);
            translate([-5.9, 0, -1.1]) cylinder(h = 2.2, r = 0.6, center = true, $fn = 16);
            translate([5.15, -5, -1.1]) cylinder(h = 2.2, r = 0.75, center = true, $fn = 16);
        }
    }
}

// ---------- 二极管 1N4148（原点=中心，卧式，色环在 x 小端）----------
module diode_1n4148(x, y) {
    translate([x, y, 0]) {
        color(C_GLASS) translate([0, 0, 1.0]) rotate([0, 90, 0]) cylinder(h = 4, r = 1.0, center = true, $fn = 24);
        color(C_BAND)  translate([-1.6, 0, 1.0]) rotate([0, 90, 0]) cylinder(h = 1.1, r = 1.04, center = true, $fn = 24);
        color(C_SILVER) {
            translate([2.9, 0, 0.8]) cube([2.0, 0.5, 0.5], center = true);
            translate([-2.9, 0, 0.8]) cube([2.0, 0.5, 0.5], center = true);
        }
    }
}

// ---------- 排针（13 针一列，胶条已剪掉，只留金针）----------
module header_pins(x) {
    for (k = [0 : JP_N - 1])
        translate([x, JP_Y0 + k * 2.54, 1.8]) cube([0.64, 0.64, 3.6], center = true);
}

// ---------- 主控 NoLogo NRF52840（背面，元件面朝下，USB-C 朝 +y 上壁）----------
// 本体 x[76.76,94.54] y[13.56,46.56] → 中心 (85.65, 30.06)
module promicro() {
    translate([85.65, 30.06, -2.5]) {
        color(C_NAVY)   translate([0, 0, -0.8]) cube([17.78, 33, 1.6], center = true);
        color(C_SILVER) translate([0, 17.5, -0.6]) cube([9, 1.5, 1.8], center = true);   // USB-C（短边 +y）
        color(C_BLACK)  translate([-2, 4, -2.1]) cube([10, 10, 1], center = true);       // NRF 屏蔽罩
        color(C_SILVER) translate([4.5, -8, -1.95]) cube([3.2, 2, 0.7], center = true);  // 晶振
        color(C_GOLD) {
            translate([-7, -12, -1.68]) cube([2.5, 2, 0.16], center = true);             // B+
            translate([-7, -8.5, -1.68]) cube([2.5, 2, 0.16], center = true);            // B-
        }
    }
}

// ---------- 电池 403040（背面，顶面贴板底；贴内腔左壁 x −2~28）----------
module battery() {
    translate([13, 25, -1.6]) {
        color(C_BATT) translate([0, 0, -2]) cube([30, 40, 4], center = true);
        color(C_RED)   translate([14.6, 2.5, -1.2]) cube([3, 1, 0.8], center = true);    // 红线（B+）
        color(C_BLACK) translate([14.6, -2.5, -1.2]) cube([3, 1, 0.8], center = true);   // 黑线（B-）
    }
}

// ---------- 飞线小件 ----------
module pwr_switch() {           // 电源开关 doc(3,25)
    color(C_BLACK) translate([3, 25, 1.6]) cube([6, 3.2, 3.2], center = true);
    color(C_RED)   translate([3, 25, 3.8]) cube([1.2, 1.2, 1.4], center = true);
}
module reset_btn() {            // 复位按钮飞线焊盘 doc：RST1(74,17) / GND1(74,13)
    color(C_BLACK) translate([74, 17, 1.2]) cube([4.4, 4.4, 2.4], center = true);
    color(C_RED)   translate([74, 17, 3.0]) cube([2.2, 2.2, 1.2], center = true);
    color(C_GOLD)  translate([74, 13, 0.6]) cube([2.5, 2.5, 0.16], center = true);
}
module lever() {                // 审批拨杆（实际装外壳右壁，此处浮在缺口示意）doc(96,5.6)
    color(C_BLACK)  translate([96, 5.6, 0]) cube([8.5, 13, 4], center = true);
    color(C_SILVER) translate([100.5, 5.6, 2.6]) cube([1.6, 1.6, 5.2], center = true);
    color(C_SILVER) translate([102.2, 5.6, 6.2]) cube([3.2, 1.2, 1.2], center = true);
}

// ---------- 焊接步骤总装 ----------
module soldered_pcb() {
    pcb_board();
    if (STEP >= 1) for (d = DIODES) diode_1n4148(d[0], d[1]);
    if (STEP >= 2) {
        for (x = JP_XS) header_pins(x);
        promicro();
    }
    if (STEP >= 3) { battery(); pwr_switch(); reset_btn(); }
    if (STEP >= 4) for (s = SWITCHES) translate([s[1], s[2], 0]) choc_switch(s[3]);
    if (STEP >= 5) lever();
}

// ---------- 装进外壳（与 assembly.scad 同一坐标约定）----------
module soldered_pcb_in_case() {
    translate([CASE_WALL + PCB_X, CASE_WALL + PCB_Y, CASE_BOTTOM_T + PCB_STANDOFF_H + PCB_T])
        soldered_pcb();
}

// ---------- 视图 ----------
if (VIEW == "in_case") {
    color("LightSteelBlue", 0.25) case_bottom();
    soldered_pcb_in_case();
} else {
    soldered_pcb();
}

// ---------- 步骤说明 ----------
echo("══════ ClaudePad 焊接步骤 ══════");
echo(str("STEP=", STEP, "  ", STEP == 0 ? "裸板" :
         STEP == 1 ? "① 二极管×12（色环朝左）" :
         STEP == 2 ? "② 排针×26（剪胶条）+ 主控（背面）" :
         STEP == 3 ? "③ 飞线：电池/电源开关/复位按钮" :
         STEP == 4 ? "④ 轴体×14（含 STOP 270° / ENTER② 90° / VOICE 180°）" :
                     "⑤ 拨杆（装外壳右壁）→ 完成"));

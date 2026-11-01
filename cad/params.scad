// =============================================================================
// ClaudePad · 全局参数（PCB / 定位板 / 外壳 / 键帽共用）
// 单位：mm；坐标与 pcb/generate_pcb.py 完全一致（绝对坐标）
// =============================================================================

// ---- PCB / 按键网格 ---------------------------------------------------------
PCB_X0 = 9.0;
PCB_Y0 = 3.0;
PCB_W = 90.0;
PCB_D = 76.0;
PCB_T = 1.6;
PCB_TOP_Z = 8.6;          // 底板 2.0 + 支撑 5.0 + PCB 1.6
PCB_BOT_Z = 7.0;

PITCH_X = 18.0;
PITCH_Y = 17.0;
KEY_X = [18.0, 36.0, 54.0, 72.0, 90.0];
KEY_Y = [30.5, 47.5, 64.5];

// 14 个实体轴位（ENTER/Space 多轴并联）
SWITCHES = [
    [18.0, 30.5], [36.0, 30.5], [54.0, 30.5], [72.0, 30.5], [90.0, 30.5],
    [18.0, 47.5], [54.0, 47.5], [72.0, 47.5], [90.0, 47.5],
    [18.0, 64.5], [36.0, 64.5], [54.0, 64.5], [72.0, 64.5], [90.0, 64.5]
];

// 11 个键帽：[cx, cy, 宽度u, 名称]
KEYCAPS = [
    [18.0, 30.5, 1, "PERM"], [36.0, 30.5, 1, "MODEL"], [54.0, 30.5, 1, "CMD"],
    [72.0, 30.5, 1, "UP"], [90.0, 30.5, 1, "VOICE"],
    [18.0, 47.5, 1, "STOP"], [54.0, 47.5, 1, "LEFT"], [72.0, 47.5, 1, "DOWN"],
    [90.0, 47.5, 1, "RIGHT"],
    [27.0, 64.5, 2, "ENTER"], [72.0, 64.5, 3, "SPACE"]
];

// ---- 轴体 / 定位板 ---------------------------------------------------------
SWITCH_CUTOUT = 14.5;     // Choc V2 方孔（kiswitch footprint Eco1.User = 14.5）
SWITCH_CUTOUT_TOL = 0.1;
SWITCH_CLIP_W = 2.6;      // 侧卡扣槽
SWITCH_CLIP_H = 1.9;
SWITCH_TRAVEL = 3.0;
SWITCH_TOP_ABOVE_PCB = 8.0; // 轴芯顶面相对 PCB 顶部

PLATE_T = 1.2;
PLATE_X0 = 3.0;
PLATE_Y0 = 22.0;
PLATE_W = 102.0;
PLATE_D = 57.0;
PLATE_RADIUS = 3.0;

// PCB 顶面 → 定位板底面。唯一需要实物校准的参数。
// 先打印 test_coupon.scad，实测 3.50 / 4.25 / 5.00 哪个最贴合。
SWITCH_PLATE_GAP = 5.0;
PLATE_BOT_Z = PCB_TOP_Z + SWITCH_PLATE_GAP;   // 13.6
PLATE_TOP_Z = PLATE_BOT_Z + PLATE_T;          // 14.8

// ---- 外壳 -------------------------------------------------------------------
CASE_W = 108.0;
CASE_D = 82.0;
CASE_WALL = 2.4;
CASE_BOTTOM_T = 2.0;
CASE_RADIUS = 3.0;
CASE_H = PLATE_TOP_Z;                          // 14.8（定位板顶面与外沿齐平）

SCREW_POS = [[6.0, 25.0], [102.0, 25.0], [6.0, 76.0], [102.0, 76.0]];
SCREW_CLEAR = 2.3;
POST_D = 5.0;
PILOT_D = 1.7;

SUPPORT_POS = [[27.0, 39.0], [81.0, 39.0], [27.0, 56.0], [81.0, 56.0]];
SUPPORT_D = 4.0;
SUPPORT_H = PCB_BOT_Z - CASE_BOTTOM_T;         // 5.0

FOOT_POS = [[10.0, 8.0], [98.0, 8.0], [10.0, 74.0], [98.0, 74.0]];

// ---- 电池仓（PCB 下方）------------------------------------------------------
// 电池放在控制器仓下方（PCB 下面），避开键区背面的 DO-35 二极管
BATT_W = 30.0;
BATT_L = 20.0;
BATT_H = 3.0;             // 302030 锂电，带保护板
BATT_X0 = 10.0;
BATT_Y0 = 3.0;
BATT_WALL = 1.6;
BATT_WALL_H = 4.0;        // 1.5..6.0，PCB 底面 7.0，留 1.0

// ---- XIAO / 电池连接器 ------------------------------------------------------
XIAO_X = 54.0;
XIAO_Y = 12.0;
XIAO_W = 21.0;
XIAO_D = 17.8;
XIAO_H = 3.2;
// XIAO 用 2x7 2.54mm 排针穿孔安装，模块被抬高 HEADER_H。
// PCB 顶面 8.6 + 2.5 = 模块底面 11.1；USB-C 中心约 12.7。
HEADER_H = 2.5;
XIAO_RECESS_X0 = 42.0;
XIAO_RECESS_X1 = 66.0;
XIAO_RECESS_Y0 = 1.4;
XIAO_RECESS_Y1 = 2.6;
XIAO_RECESS_Z0 = 10.5;
XIAO_RECESS_Z1 = 14.3;
USB_SLOT_X0 = 48.5;
USB_SLOT_X1 = 59.5;
USB_SLOT_Z0 = 10.5;
USB_SLOT_Z1 = 14.3;

JST_X = 74.0;
JST_Y = 12.0;
CABLE_SLOT = [83.5, 10.0, 87.5, 18.0];

// ---- 键帽 -------------------------------------------------------------------
CAP_GAP = 3.3;            // 定位板顶面 → 键帽裙边底面（≥ SWITCH_TRAVEL）
CAP_H = 5.0;
CAP_WALL = 1.8;
CAP_TOP_T = 1.6;
CAP_TAPER = 0.55;
CAP_STEM_W = 1.2;
CAP_STEM_GAP = 0.95;
CAP_STEM_DEPTH = 3.6;
CAP_TOP_R = 3.0;
CAP_RIB_T = 1.2;
CAP_RIB_COUNT_MED = 1;
CAP_RIB_COUNT_LONG = 3;

TOTAL_H = PLATE_TOP_Z + CAP_GAP + CAP_H;       // 23.1

$fn = 64;

// ---- 通用函数 ---------------------------------------------------------------
module rrect(w, d, r) {
    offset(r = r) offset(delta = -r) square([w, d], center = true);
}

function axis_count(u) = (u <= 1) ? 1 : ((u == 2) ? 2 : 3);

function stem_offset(u, i) =
    (axis_count(u) <= 1) ? 0 : (i - (axis_count(u) - 1) / 2) * PITCH_X;

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

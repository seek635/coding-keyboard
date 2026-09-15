// =============================================================================
// ClaudePad · 底座 / 外壳下壳 (case_bottom.scad)
// -----------------------------------------------------------------------------
// 结构：一个上开口的盒子。
//   · 内腔是直壁矩形，定位板从上方落入，与外壳上沿齐平
//   · 四角螺丝柱托住定位板（M2 螺丝从上往下拧）
//   · PCB 由 4 个矮支撑台托起，靠轴体+定位板压住固定
//   · 电池贴在底板中央（PCB 下方），四周有限位挡墙
//   · 右壁装 SPDT 审批拨杆
//
// 打印方向：底面朝下平放，无需支撑
// =============================================================================

include <lib/params.scad>

// ---------- 派生尺寸 ------------------------------------------------------
CASE_INNER_W = PLATE_W + CASE_TOP_TOL * 2;      // = 102.30
CASE_INNER_D = PLATE_H + CASE_TOP_TOL * 2;      // = 66.30
CASE_W = CASE_INNER_W + CASE_WALL * 2;          // = 107.10
CASE_D = CASE_INNER_D + CASE_WALL * 2;          // = 71.10

// 定位板底面高度（= 螺丝柱顶面 = 底板上表面 + 内腔高度）
PLATE_BOTTOM_Z = CASE_BOTTOM_T + CASE_INNER_H;  // = 13.60
PCB_TOP_Z = CASE_BOTTOM_T + PCB_STANDOFF_H + PCB_T;   // = 8.60

// 拨杆位置（右壁）
SW_Y = 16.0;                                    // 拨杆中心纵向位置
SW_Z = CASE_BOTTOM_T + CASE_INNER_H * 0.55;     // 拨杆中心高度

// 主控位置（PCB 右上方）
NANO_X = PCB_X + CASE_WALL + PCB_W - 3.0 - NANO_W;    // 绝对坐标
NANO_Y = PCB_Y + CASE_WALL + PCB_H - 3.0 - NANO_L;

// ---------- 通用工具 ------------------------------------------------------
module rounded_box(w, h, d, r) {
    linear_extrude(height = d)
        offset(r = r) offset(delta = -r)
            square([w, h]);
}

// ---------- 底座主体 ------------------------------------------------------
module case_shell() {
    difference() {
        // 外壳实体（底面做 0.2 倒角防大象脚）
        translate([0, 0, TOL_BOTTOM_CHAMFER])
            rounded_box(CASE_W, CASE_D, CASE_OUTER_H - TOL_BOTTOM_CHAMFER, CASE_RADIUS);
        translate([TOL_BOTTOM_CHAMFER, TOL_BOTTOM_CHAMFER, 0])
            rounded_box(
                CASE_W - TOL_BOTTOM_CHAMFER * 2,
                CASE_D - TOL_BOTTOM_CHAMFER * 2,
                TOL_BOTTOM_CHAMFER + 0.01,
                CASE_RADIUS - TOL_BOTTOM_CHAMFER
            );

        // 内腔（直壁，上开口）
        translate([CASE_WALL, CASE_WALL, CASE_BOTTOM_T])
            rounded_box(
                CASE_INNER_W,
                CASE_INNER_D,
                CASE_INNER_H + PLATE_T + 1,
                CASE_RADIUS - 1
            );
    }
}

// ---------- 四角螺丝柱（托住定位板）--------------------------------------
// 柱高 = 内腔高度（从底板上表面到定位板底面）
// ★ 向下多伸 FUSE_OVERLAP 与底板融合，避免共面产生非流形边
// 顶部开 M2 自攻底孔，深 6mm（留 4.5mm 不穿透底板）
module case_posts() {
    for (px = [0, 1], py = [0, 1]) {
        translate([
            px == 0 ? CASE_WALL + SCREW_INSET : CASE_W - CASE_WALL - SCREW_INSET,
            py == 0 ? CASE_WALL + SCREW_INSET : CASE_D - CASE_WALL - SCREW_INSET,
            CASE_BOTTOM_T - FUSE_OVERLAP
        ]) difference() {
            cylinder(d = POST_D, h = CASE_INNER_H + FUSE_OVERLAP);
            // M2 自攻底孔（从柱顶向下 6mm）
            translate([0, 0, CASE_INNER_H - 6.0 + FUSE_OVERLAP])
                cylinder(d = SCREW_M2_TAP, h = 6.5);
        }
    }
}

// ---------- PCB 支撑台 ----------------------------------------------------
// 4 个矮柱托起 PCB，高度 = PCB_STANDOFF_H
// ★ 位置取「轴体之间的空隙中央」，不能放四角（会顶住轴体塑料脚）
module pcb_supports() {
    ox = PCB_X + CASE_WALL;
    oy = PCB_Y + CASE_WALL;
    for (sx = [PCB_SUPPORT_X1, PCB_SUPPORT_X2],
         sy = [PCB_SUPPORT_Y1, PCB_SUPPORT_Y2]) {
        translate([ox + sx, oy + sy, CASE_BOTTOM_T - FUSE_OVERLAP])
            cylinder(d = PCB_SUPPORT_D, h = PCB_STANDOFF_H + FUSE_OVERLAP);
    }
}

// ---------- 电池仓 --------------------------------------------------------
// 电池贴在底板中央（PCB 正下方），四周限位挡墙防止滑动
// 挡墙高度受 PCB_STANDOFF_H 限制，不能顶到 PCB
BATT_X = CASE_WALL + (CASE_INNER_W - BATT_W) / 2;
BATT_Y = CASE_WALL + (CASE_INNER_D - BATT_L) / 2;
BATT_WALL_H = PCB_STANDOFF_H - BATT_TAPE_T;      // = 4.4，正好不顶 PCB

module battery_bay() {
    // 限位挡墙：右 + 上 两侧（左、下靠外壳内壁）
    // ★ 向下多伸 FUSE_OVERLAP 与底板融合
    translate([BATT_X + BATT_W + BATT_TOL, BATT_Y - BATT_TOL,
               CASE_BOTTOM_T - FUSE_OVERLAP])
        cube([1.60, BATT_L + BATT_TOL * 2, BATT_WALL_H + FUSE_OVERLAP]);
    translate([BATT_X - BATT_TOL, BATT_Y + BATT_L + BATT_TOL,
               CASE_BOTTOM_T - FUSE_OVERLAP])
        cube([BATT_W + BATT_TOL * 2 + 1.60, 1.60, BATT_WALL_H + FUSE_OVERLAP]);
}

// ---------- 走线通道 ------------------------------------------------------
// A：沿下缘横向（键位矩阵行线）
// B：沿右缘纵向（拨杆信号线 → 主控）
module wire_channels() {
    // A
    translate([CASE_WALL + 2, CASE_WALL + 1, CASE_BOTTOM_T - WIRE_CH_D])
        cube([CASE_INNER_W - 4, WIRE_CH_W, WIRE_CH_D + 0.01]);
    // B
    translate([CASE_W - CASE_WALL - 1 - WIRE_CH_W, CASE_WALL + 2, CASE_BOTTOM_T - WIRE_CH_D])
        cube([WIRE_CH_W, CASE_INNER_D - 4, WIRE_CH_D + 0.01]);
}

// ---------- 右壁：USB-C 开孔 ---------------------------------------------
// 主控焊在 PCB 上，USB 口朝右壁，开口是「横长」的槽（宽 > 高）
//
// ⚠️ 注意 rotate([0,90,0]) 之后：局部 X 轴 → 世界 Z 轴（垂直）
//    所以要沿「局部 Y 轴」偏移，才能得到水平方向的槽。
module usb_cutout() {
    d = NANO_USB_H + NANO_USB_TOL;                       // 槽高
    off = NANO_USB_W + NANO_USB_TOL - d;                 // 槽宽 - 槽高
    translate([CASE_W - CASE_WALL - 2, NANO_Y + NANO_L / 2, PCB_TOP_Z + 1.80])
        rotate([0, 90, 0])
            hull() {
                cylinder(d = d, h = CASE_WALL + 6);
                translate([0, off, 0]) cylinder(d = d, h = CASE_WALL + 6);
            }
}

// ---------- 右壁：拨杆凸台与开孔 -----------------------------------------
// 凸台是「壳外」的圆形加厚垫，用来给轴套提供额外咬合长度。
// 拨杆在壳外摆动，不需要在壳壁上开行程槽 —— 只需要一个轴套过孔。
module switch_boss() {
    // ★ 向壳内多伸 FUSE_OVERLAP 与侧壁融合
    translate([CASE_W - FUSE_OVERLAP, SW_Y, SW_Z])
        rotate([0, 90, 0])
            cylinder(d = SW_BOSS_D, h = SW_BOSS_T + FUSE_OVERLAP);
}

module switch_cutouts() {
    // 轴套过孔（贯穿 壁 + 凸台），两端各留 1mm 保证切透
    translate([CASE_W - CASE_WALL - 1, SW_Y, SW_Z])
        rotate([0, 90, 0])
            cylinder(d = SW_BUSH_D + TOL_HOLE, h = CASE_WALL + SW_BOSS_T + 2);
}

// ---------- 底面：脚垫沉孔 / 通气孔 / 复位孔 ------------------------------
module bottom_features() {
    // 脚垫沉孔（四角）
    for (px = [0, 1], py = [0, 1]) {
        translate([
            px == 0 ? FOOT_INSET : CASE_W - FOOT_INSET,
            py == 0 ? FOOT_INSET : CASE_D - FOOT_INSET,
            -0.1
        ]) cylinder(d = FOOT_D + TOL_HOLE, h = FOOT_DEPTH + 0.1);
    }

    // 通气孔（主控正下方，VENT_COLS × VENT_ROWS 阵列）
    for (ix = [0 : VENT_COLS - 1], iy = [0 : VENT_ROWS - 1]) {
        translate([
            NANO_X + NANO_W * (0.2 + 0.6 * ix / max(1, VENT_COLS - 1)),
            NANO_Y + NANO_L * (0.3 + 0.4 * iy / max(1, VENT_ROWS - 1)),
            -0.1
        ]) cylinder(d = BOTTOM_VENT_D, h = CASE_BOTTOM_T + 0.2);
    }

    // 复位按钮开孔（主控 reset 位置）
    translate([NANO_X + NANO_W / 2, NANO_Y + 3.0, -0.1])
        cylinder(d = 8.0, h = CASE_BOTTOM_T + 0.2);
}

// ---------- 装配体 --------------------------------------------------------
module case_bottom() {
    difference() {
        union() {
            case_shell();
            case_posts();
            pcb_supports();
            battery_bay();
            switch_boss();
        }
        usb_cutout();
        switch_cutouts();
        bottom_features();
        wire_channels();
    }
}

case_bottom();

// ---------- 尺寸自检 -------------------------------------------------------
echo("──────── 底座尺寸 ────────");
echo(str("外形   = ", CASE_W, " × ", CASE_D, " × ", CASE_OUTER_H, " mm"));
echo(str("内腔   = ", CASE_INNER_W, " × ", CASE_INNER_D, " × ", CASE_INNER_H, " mm"));
echo(str("定位板底面 z = ", PLATE_BOTTOM_Z, " ｜ PCB 顶面 z = ", PCB_TOP_Z));
echo(str("电池仓 高度限制 = ", BATT_WALL_H, " mm（电池 ", BATT_H, " + 胶 ", BATT_TAPE_T, "）"));
echo(str("螺丝柱外缘到轴孔余量 = ",
    (PLATE_BORDER + PITCH / 2 - (SWITCH_CUTOUT + SWITCH_CUTOUT_TOL) / 2)
    - (SCREW_INSET + POST_D / 2), " mm"));
echo(str("拨杆凸台：直径 ", SW_BOSS_D, " 厚 ", SW_BOSS_T,
         " ｜ z 范围 ", SW_Z - SW_BOSS_D / 2, " ~ ", SW_Z + SW_BOSS_D / 2,
         "（外壳高 ", CASE_OUTER_H, "）"));

// ---------- 打印建议 -------------------------------------------------------
// 方向：底面朝下平放，无需支撑
// 层高：0.20mm｜壁数：3｜填充：25%
// 材料：PETG 优先（韧性好），PLA 次选

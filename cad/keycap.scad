// =============================================================================
// ClaudePad · 键帽 (keycap.scad)
// -----------------------------------------------------------------------------
// 三类键帽：1u 标准 / 2u 回车 / 4u 空格
// Choc 矮轴专用（十字榫槽适配 Choc 轴芯 1.1 十字）
//
// 结构：薄壳（四壁 + 顶面）+ 中心榫头柱，底部开口
// 打印方向：顶面朝下（倒扣），榫头朝上 —— 榫槽精度最高，无需支撑
// =============================================================================

include <lib/params.scad>

// ---------- 榫头定位（必须与 plate.scad 的轴孔位置严格一致）---------------
// 键帽中心 = 该键跨格范围的中点，故第 i 个榫头相对中心的偏移为：
//   PITCH * (axis_offset(u,i) - u/2)
function kc_axis_count(u) = (u <= 1) ? 1 : ((u == 2) ? 2 : 3);
function kc_stem_offset(u, i) =
    PITCH * ((u <= 1) ? 0
                      : (0.5 + i * (u - 1) / (kc_axis_count(u) - 1) - u / 2));

// ---------- 圆角矩形截面（复用）------------------------------------------
module rrect(w, h, r) {
    offset(r = r) offset(delta = -r) square([w, h], center = true);
}

// ---------- 十字榫槽（从 z=0 向上开，深 CAP_STEM_DEPTH）-------------------
module cross_stem_socket() {
    union() {
        translate([-CAP_CROSS_L / 2, -CAP_CROSS_W / 2, 0])
            cube([CAP_CROSS_L, CAP_CROSS_W, CAP_STEM_DEPTH]);
        translate([-CAP_CROSS_W / 2, -CAP_CROSS_L / 2, 0])
            cube([CAP_CROSS_W, CAP_CROSS_L, CAP_STEM_DEPTH]);
    }
}

// ---------- 键帽外壳（薄壳：四壁 + 顶面，底部开口）----------------------
module cap_shell(u) {
    outer_w = PITCH * u - 0.40;
    outer_d = PITCH - 0.40;
    top_w = outer_w - CAP_TAPER * 2;
    top_d = outer_d - CAP_TAPER * 2;
    r_out = min(CAP_TOP_R, min(outer_w, outer_d) / 2 - 0.1);
    r_in = max(r_out - CAP_WALL, 0.2);

    difference() {
        // 外壳实体（下大上小的梯形）
        hull() {
            linear_extrude(height = 0.01) rrect(outer_w, outer_d, r_out);
            translate([0, 0, CAP_H - CAP_TOP_T])
                linear_extrude(height = CAP_TOP_T) rrect(top_w, top_d, r_out);
        }
        // 内腔（从底部开口一直挖到顶面下方，留 CAP_TOP_T 做顶）
        hull() {
            translate([0, 0, -1])
                linear_extrude(height = 0.01)
                    rrect(outer_w - CAP_WALL * 2, outer_d - CAP_WALL * 2, r_in);
            translate([0, 0, CAP_H - CAP_TOP_T])
                linear_extrude(height = 0.01)
                    rrect(top_w - CAP_WALL * 2, top_d - CAP_WALL * 2, r_in);
        }
    }
}

// ---------- 榫头柱 --------------------------------------------------------
module stem_boss() {
    h = CAP_H - CAP_TOP_T;
    difference() {
        cylinder(d = CAP_STEM_BOSS_D, h = h);
        translate([0, 0, -0.5]) cross_stem_socket();
    }
}

// ---------- 内部加强筋（大键防变形）--------------------------------------
module cap_ribs(u) {
    if (u >= 2) {
        outer_w = PITCH * u - 0.40;
        outer_d = PITCH - 0.40;
        n = (u == 2) ? CAP_RIB_COUNT_MED : CAP_RIB_COUNT_LONG;
        for (i = [1 : n]) {
            translate([
                -outer_w / 2 + outer_w * i / (n + 1) - CAP_RIB_T / 2,
                -outer_d / 2 + CAP_WALL,
                0
            ]) cube([CAP_RIB_T, outer_d - CAP_WALL * 2, CAP_H - CAP_TOP_T]);
        }
    }
}

// ---------- 完整键帽 ------------------------------------------------------
module keycap(u = 1) {
    union() {
        cap_shell(u);
        for (i = [0 : kc_axis_count(u) - 1]) {
            translate([kc_stem_offset(u, i), 0, 0]) stem_boss();
        }
        cap_ribs(u);
    }
}

// ---------- 渲染控制（改这里切换键帽规格）--------------------------------
keycap_mode = "1u";     // "1u" / "2u" / "4u"

if (keycap_mode == "1u") {
    keycap(1);
} else if (keycap_mode == "2u") {
    keycap(2);
} else {
    keycap(4);
}

// ---------- 尺寸自检 -------------------------------------------------------
echo(str("键帽：高 ", CAP_H, " ｜ 1u 外宽 ", PITCH - 0.40, " ｜ MX 十字榫槽 ", CAP_CROSS_L, "×", CAP_CROSS_W, " 深 ", CAP_STEM_DEPTH));
echo(str("装配校验：轴芯高出定位板 ", SWITCH_TIP_ABOVE_PLATE,
         " ≤ 间隙 ", CAP_GAP, " + 榫槽深 ", CAP_STEM_DEPTH, " = ", CAP_GAP + CAP_STEM_DEPTH));

// ---------- 打印建议 -------------------------------------------------------
// 方向：顶面朝下倒扣打印（榫头朝上），无需支撑
// 层高：0.12mm｜壁数：3｜填充：15%
// 材料：PLA（手感清脆）或 PETG（耐用）

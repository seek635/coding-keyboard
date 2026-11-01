// =============================================================================
// ClaudePad · 零件模块（由 params.scad 提供尺寸）
// =============================================================================

// ---- 底座 -------------------------------------------------------------------
module case_shell() {
    difference() {
        translate([CASE_W / 2, CASE_D / 2, 0])
            linear_extrude(height = CASE_H)
                rrect(CASE_W, CASE_D, CASE_RADIUS);

        translate([CASE_W / 2, CASE_D / 2, CASE_BOTTOM_T])
            linear_extrude(height = CASE_H + 1)
                rrect(CASE_W - 2 * CASE_WALL, CASE_D - 2 * CASE_WALL,
                      CASE_RADIUS - CASE_WALL);

        translate([XIAO_RECESS_X0, XIAO_RECESS_Y0, XIAO_RECESS_Z0])
            cube([XIAO_RECESS_X1 - XIAO_RECESS_X0,
                  XIAO_RECESS_Y1 - XIAO_RECESS_Y0,
                  XIAO_RECESS_Z1 - XIAO_RECESS_Z0]);

        translate([USB_SLOT_X0, -0.1, USB_SLOT_Z0])
            cube([USB_SLOT_X1 - USB_SLOT_X0, 1.6,
                  USB_SLOT_Z1 - USB_SLOT_Z0]);

        for (f = FOOT_POS)
            translate([f[0], f[1], -0.1]) cylinder(d = 8.0, h = 1.2);
    }
}

module plate_ledges() {
    z0 = PLATE_BOT_Z - PLATE_T;
    translate([CASE_WALL - 0.5, PLATE_Y0, z0])
        cube([2.5, PLATE_D, PLATE_T]);
    translate([CASE_W - CASE_WALL - 2.0, PLATE_Y0, z0])
        cube([2.5, PLATE_D, PLATE_T]);
    translate([CASE_WALL, CASE_D - CASE_WALL - 2.0, z0])
        cube([CASE_W - 2 * CASE_WALL, 2.5, PLATE_T]);
}

module screw_posts() {
    for (p = SCREW_POS)
        translate([p[0], p[1], CASE_BOTTOM_T - 0.5])
            cylinder(d = POST_D, h = PLATE_BOT_Z - CASE_BOTTOM_T + 0.5);
}

module pcb_supports() {
    for (p = SUPPORT_POS)
        translate([p[0], p[1], CASE_BOTTOM_T - 0.5])
            cylinder(d = SUPPORT_D, h = SUPPORT_H + 0.5);
}

module battery_walls() {
    z0 = CASE_BOTTOM_T - 0.5;
    h = BATT_WALL_H + 0.5;
    // 左
    translate([BATT_X0 - 2.0, BATT_Y0 - 1.5, z0])
        cube([BATT_WALL, BATT_L + 3.0, h]);
    // 右（中间留走线缺口）
    translate([BATT_X0 + BATT_W + 0.4, BATT_Y0 - 1.5, z0])
        cube([BATT_WALL, 12.5, h]);
    translate([BATT_X0 + BATT_W + 0.4, BATT_Y0 + 14.5, z0])
        cube([BATT_WALL, BATT_L - 10.0, h]);
    // 后
    translate([BATT_X0 - 2.0, BATT_Y0 - 1.5, z0])
        cube([BATT_W + 4.0, BATT_WALL, h]);
    // 前
    translate([BATT_X0 - 2.0, BATT_Y0 + BATT_L, z0])
        cube([BATT_W + 4.0, BATT_WALL, h]);
}

module case_bottom() {
    difference() {
        union() {
            case_shell();
            plate_ledges();
            screw_posts();
            pcb_supports();
            battery_walls();
        }
        for (p = SCREW_POS)
            translate([p[0], p[1], 7.0])
                cylinder(d = PILOT_D, h = PLATE_BOT_Z - 7.0 + 0.2);
    }
}

// ---- 定位板 -----------------------------------------------------------------
module plate() {
    difference() {
        translate([PLATE_X0 + PLATE_W / 2, PLATE_Y0 + PLATE_D / 2, PLATE_BOT_Z])
            linear_extrude(height = PLATE_T)
                rrect(PLATE_W, PLATE_D, PLATE_RADIUS);

        for (s = SWITCHES)
            translate([s[0], s[1], PLATE_BOT_Z + PLATE_T / 2])
                choc_cutout();

        for (p = SCREW_POS)
            translate([p[0], p[1], PLATE_BOT_Z - 1])
                cylinder(d = SCREW_CLEAR, h = PLATE_T + 2);
    }
}

// ---- 键帽 -------------------------------------------------------------------
module cross_stem_socket() {
    union() {
        translate([-CAP_STEM_W / 2, -CAP_STEM_GAP / 2, 0])
            cube([CAP_STEM_W, CAP_STEM_GAP, CAP_STEM_DEPTH]);
        translate([-CAP_STEM_GAP / 2, -CAP_STEM_W / 2, 0])
            cube([CAP_STEM_GAP, CAP_STEM_W, CAP_STEM_DEPTH]);
    }
}

module cap_shell(u) {
    outer_w = PITCH_X * u - 0.4;
    outer_d = PITCH_Y - 0.4;
    top_w = outer_w - CAP_TAPER * 2;
    top_d = outer_d - CAP_TAPER * 2;
    r_out = min(CAP_TOP_R, min(outer_w, outer_d) / 2 - 0.1);
    r_in = max(r_out - CAP_WALL, 0.2);

    difference() {
        hull() {
            linear_extrude(height = 0.01) rrect(outer_w, outer_d, r_out);
            translate([0, 0, CAP_H - CAP_TOP_T])
                linear_extrude(height = CAP_TOP_T) rrect(top_w, top_d, r_out);
        }
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

module stem_boss() {
    h = CAP_H - CAP_TOP_T;
    difference() {
        cylinder(d = CAP_STEM_W * 2 + 2.0, h = h);
        translate([0, 0, -0.5]) cross_stem_socket();
    }
}

module cap_ribs(u) {
    if (u >= 2) {
        outer_w = PITCH_X * u - 0.4;
        outer_d = PITCH_Y - 0.4;
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

module keycap(u = 1) {
    union() {
        cap_shell(u);
        for (i = [0 : axis_count(u) - 1])
            translate([stem_offset(u, i), 0, 0]) stem_boss();
        cap_ribs(u);
    }
}

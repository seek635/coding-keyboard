// =============================================================================
// ClaudePad · 总装预览（OpenSCAD）
// 导出 PNG：
//   openscad -o assembly.png --autocenter --viewall --imgsize=1600,1200 assembly.scad
// 视图：-D VIEW_MODE='"assembly"' / "exploded" / "case" / "plate" / "caps"
// =============================================================================

include <params.scad>
include <parts.scad>

VIEW = is_undef(VIEW_MODE) ? "assembly" : VIEW_MODE;
EXPLODE = is_undef(EXPLODE_MM) ? 0 : EXPLODE_MM;

module pcb_preview() {
    color("#1d4a32")
        translate([PCB_X0, PCB_Y0, PCB_BOT_Z])
            cube([PCB_W, PCB_D, PCB_T]);

    // XIAO 模块（示意）
    color("#181818")
        translate([XIAO_X - XIAO_W / 2, XIAO_Y - XIAO_D / 2, PCB_TOP_Z])
            cube([XIAO_W, XIAO_D, XIAO_H]);

    // USB-C 口示意
    color("#a7adb3")
        translate([XIAO_X - 5.0, XIAO_Y - XIAO_D / 2 - 0.8, PCB_TOP_Z + 0.7])
            cube([10.0, 1.4, 2.8]);

    // RESET 按键示意
    color("#8a8f94")
        translate([XIAO_X, XIAO_Y - XIAO_D / 2 + 3.5, PCB_TOP_Z + XIAO_H])
            cylinder(d = 2.4, h = 0.6);

    // JST 电池座示意
    color("#efe6d6")
        translate([JST_X - 2.5, JST_Y - 3.5, PCB_TOP_Z])
            cube([5.0, 7.0, 4.6]);
}

module cap_color(name) {
    if (name == "STOP") color("#d97757") children();
    else if (name == "UP" || name == "LEFT" || name == "DOWN" ||
             name == "RIGHT" || name == "ENTER") color("#3a3937") children();
    else color("#e3dac9") children();
}

module keycaps(zoff = 0) {
    for (k = KEYCAPS) {
        cap_color(k[3])
            translate([k[0], k[1], PLATE_TOP_Z + CAP_GAP + zoff])
                keycap(k[2]);
    }
}

if (VIEW == "case") {
    color("#2b2825") case_bottom();
} else if (VIEW == "plate") {
    color("#e9e1d2") plate();
} else if (VIEW == "caps") {
    keycaps(0);
} else {
    color("#2b2825") case_bottom();
    pcb_preview();
    color("#e9e1d2") translate([0, 0, EXPLODE]) plate();
    keycaps(EXPLODE * 2);
}

echo(str("整机外形 = ", CASE_W, " × ", CASE_D, " × ", TOTAL_H, " mm"));
echo(str("定位板顶面 z = ", PLATE_TOP_Z, "；键帽顶面 z = ", TOTAL_H));

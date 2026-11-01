// =============================================================================
// ClaudePad · 校准试件（先打这个！）
// 用途：确认 SWITCH_PLATE_GAP（PCB 顶面 → 定位板底面）
// 三个测试位：3.50 / 4.25 / 5.00 mm
// 判读：轴体卡扣清脆扣入、轴体底面刚好贴住基座顶面 → 就是该值
// =============================================================================

include <params.scad>
include <parts.scad>

COUPON_SIZE = 40.0;
COUPON_GAP = 5.0;
GAPS = [3.50, 4.25, 5.00];
BASE_H = PCB_TOP_Z;          // 8.6，模拟底板 + PCB
PIN_HOLE = 12.0;

module station(gap, idx) {
    ox = idx * (COUPON_SIZE + COUPON_GAP);

    difference() {
        translate([ox, 0, 0]) cube([COUPON_SIZE, COUPON_SIZE, BASE_H]);
        translate([ox + COUPON_SIZE / 2, COUPON_SIZE / 2, -0.1])
            cube([PIN_HOLE, PIN_HOLE, BASE_H + 0.2], center = true);
    }

    for (px = [0, 1], py = [0, 1]) {
        translate([
            ox + (px == 0 ? 6 : COUPON_SIZE - 6),
            (py == 0 ? 6 : COUPON_SIZE - 6),
            BASE_H
        ]) cylinder(d = 5.0, h = gap);
    }

    translate([ox + COUPON_SIZE / 2, COUPON_SIZE / 2, BASE_H + gap])
        difference() {
            linear_extrude(height = PLATE_T)
                offset(r = 2) offset(delta = -2)
                    square([COUPON_SIZE, COUPON_SIZE], center = true);
            translate([0, 0, PLATE_T / 2]) choc_cutout();
        }

    translate([ox + 4, -0.4, BASE_H - 4])
        linear_extrude(height = 0.8)
            text(str(gap), size = 3.5, font = "Liberation Sans:style=Bold");
}

for (i = [0 : len(GAPS) - 1]) station(GAPS[i], i);

translate([-2, -2, 0])
    cube([len(GAPS) * COUPON_SIZE + (len(GAPS) - 1) * COUPON_GAP + 4,
          COUPON_SIZE + 4, 1.0]);

echo(str("测试间隙 = ", GAPS));
echo(str("当前设计 SWITCH_PLATE_GAP = ", SWITCH_PLATE_GAP));

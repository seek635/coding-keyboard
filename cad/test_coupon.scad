// =============================================================================
// ClaudePad · 校准试件 (test_coupon.scad)
// -----------------------------------------------------------------------------
// 目的：用 15 分钟的一个小件，验证整套垂直尺寸链里最不确定的参数
//       —— SWITCH_PLATE_GAP（PCB 上表面 → 定位板底面）。
//
// 做法：并排做 3 个「单键测试位」，只有卡扣间隙不同：
//       ① 3.50mm   ② 4.25mm   ③ 5.00mm（当前设计值）
//       每个测试位都完整还原了「底板 → PCB → 轴体 → 定位板」的高度关系。
//
// 怎么用：
//   1. 打印本件（无需支撑）
//   2. 拿一个真实 Choc 轴体，逐个测试位插进去
//   3. 找到那个「轴体卡扣清脆扣入定位板，且轴体塑料底面刚好贴住基座顶面」的位置
//   4. 那个位置对应的间隙值，就是你的轴体真实值
//   5. 把 params.scad 里的 SWITCH_PLATE_GAP 改成该值，重新导出全部零件
//
// 判读标准：
//   · 轴体底面与基座顶面之间有明显缝隙 → 该位间隙偏大
//   · 轴体扣不进去 / 扣进去后底部顶住基座、卡扣未啮合 → 该位间隙偏小
//   · 完全贴合且卡扣清脆 → ✅ 就是它
// =============================================================================

include <lib/params.scad>
use <plate.scad>          // 复用 choc_cutout()

// ---------- 试件参数 ------------------------------------------------------
COUPON_SIZE = 40.00;      // 每个测试位的边长
COUPON_GAP = 5.00;        // 测试位之间的间距
GAPS = [3.50, 4.25, 5.00];      // 三个待测间隙值（覆盖实测可能范围）
BASE_H = CASE_BOTTOM_T + PCB_STANDOFF_H + PCB_T;   // 基座高 = 模拟「底板+PCB」= 8.6
PIN_HOLE = 12.00;         // 中央让位孔（供轴体引脚通过）
POST_D_C = 5.00;          // 小支柱直径

// ---------- 单个测试位 ----------------------------------------------------
module station(gap, idx) {
    ox = idx * (COUPON_SIZE + COUPON_GAP);

    // 1. 基座（模拟底板 + PCB，顶面 = PCB 上表面）
    difference() {
        translate([ox, 0, 0]) cube([COUPON_SIZE, COUPON_SIZE, BASE_H]);
        // 中央让位孔（轴体引脚通过，让轴体塑料底面能贴住基座顶面）
        translate([ox + COUPON_SIZE / 2, COUPON_SIZE / 2, -0.1])
            cube([PIN_HOLE, PIN_HOLE, BASE_H + 0.2], center = true);
    }

    // 2. 四角小支柱（高度 = 待测间隙）
    for (px = [0, 1], py = [0, 1]) {
        translate([
            ox + (px == 0 ? 6 : COUPON_SIZE - 6),
            (py == 0 ? 6 : COUPON_SIZE - 6),
            BASE_H
        ]) cylinder(d = POST_D_C, h = gap);
    }

    // 3. 迷你定位板（厚度 = PLATE_T，中间开标准轴孔）
    translate([ox + COUPON_SIZE / 2, COUPON_SIZE / 2, BASE_H + gap])
        difference() {
            linear_extrude(height = PLATE_T)
                offset(r = 2) offset(delta = -2)
                    square([COUPON_SIZE, COUPON_SIZE], center = true);
            translate([0, 0, -1]) choc_cutout();
        }

    // 4. 间隙值浮雕标记（打在基座前侧面，用高度差表示）
    translate([ox + 4, -0.4, BASE_H - 4])
        linear_extrude(height = 0.8)
            text(str(gap), size = 3.5, font = "Liberation Sans:style=Bold");
}

// ---------- 装配 ----------------------------------------------------------
for (i = [0 : len(GAPS) - 1]) {
    station(GAPS[i], i);
}

// 底部连接梁（让三件一次打印成型，不散落）
translate([-2, -2, 0])
    cube([len(GAPS) * COUPON_SIZE + (len(GAPS) - 1) * COUPON_GAP + 4,
          COUPON_SIZE + 4, 1.0]);

// ---------- 尺寸自检 -------------------------------------------------------
echo("════ 校准试件 ════");
echo(str("三个测试位的卡扣间隙 = ", GAPS, " mm"));
echo(str("基座高（模拟 底板+PCB）= ", BASE_H, " mm"));
echo(str("当前设计值 SWITCH_PLATE_GAP = ", SWITCH_PLATE_GAP, " mm"));
echo("用法：插真实轴体，找那个「底面贴合 + 卡扣清脆」的位置");

// ---------- 打印建议 -------------------------------------------------------
// 方向：平放，无需支撑
// 层高：0.16mm（间隙精度靠层高，别用 0.2）
// 填充：20%｜壁数：3
// 注意：本件只是量具，不用装电池/主控，打坏了重打成本极低

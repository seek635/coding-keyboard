// ClaudePad 键帽：1u / 2u / 3u
// 单规格导出请用包装文件：
//   openscad -o keycap_2u.stl keycap_2u.scad
// （本文件默认 1u；OpenSCAD 2021 的 -D 变量在部分环境不生效，故用包装文件）
include <params.scad>
include <parts.scad>

KC_U = is_undef(KEYCAP_U) ? 1 : KEYCAP_U;
keycap(KC_U);

echo(str("键帽 = ", KC_U, "u｜高 ", CAP_H, " mm｜裙边间隙 ", CAP_GAP, " mm"));
echo("打印方向：顶面朝下倒扣，榫槽朝上；层高 0.12，无需支撑。");

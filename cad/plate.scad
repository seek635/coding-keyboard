// ClaudePad 定位板（1.2mm 厚，平放打印）
include <params.scad>
include <parts.scad>

plate();

echo(str("定位板 = ", PLATE_W, " × ", PLATE_D, " × ", PLATE_T, " mm"));
echo(str("轴孔 = ", SWITCH_CUTOUT + SWITCH_CUTOUT_TOL, " mm，共 ", len(SWITCHES), " 个"));
echo("注意：打印后先用真实轴体试装；过紧用刀修，过松需重打。");

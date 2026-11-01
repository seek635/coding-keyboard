// ClaudePad 底座
include <params.scad>
include <parts.scad>

case_bottom();

echo(str("底座外形 = ", CASE_W, " × ", CASE_D, " × ", CASE_H, " mm"));
echo(str("PCB 顶面 z = ", PCB_TOP_Z, "；定位板底面 z = ", PLATE_BOT_Z));
echo(str("电池仓可用高度 = ", BATT_WALL_H, " mm（电池 ", BATT_H, " + 胶）"));

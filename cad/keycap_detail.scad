// 1u / 2u / 3u keycap underside (stem sockets, ribs)
include <params.scad>
include <parts.scad>

translate([-42, 0, 0]) rotate([180, 0, 0]) keycap(1);
translate([0, 0, 0])   rotate([180, 0, 0]) keycap(2);
translate([48, 0, 0])  rotate([180, 0, 0]) keycap(3);

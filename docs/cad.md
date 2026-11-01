# ClaudePad 外壳、定位板与键帽

> 参数化 OpenSCAD 源文件：[cad/](../cad/)
> PCB：[pcb.md](pcb.md)
> STL：[cad/output/stl/](../cad/output/stl/)
> 预览：[claudepad-hero.png](preview/claudepad-hero.png)、[claudepad-top.png](preview/claudepad-top.png)、[claudepad-exploded.png](preview/claudepad-exploded.png)

## 1. 零件与尺寸

| 零件 | 文件 | 尺寸 (mm) | 材料 |
|---|---|---|---|
| 底座 | `case_bottom.stl` | 108 × 82 × 14.8 | PETG / PLA |
| 定位板 | `plate.stl` | 102 × 57 × 1.2 | PLA / PETG |
| 键帽 1u | `keycap_1u.stl` | 17.6 × 16.6 × 5.0 | PLA |
| 键帽 2u（ENTER） | `keycap_2u.stl` | 35.6 × 16.6 × 5.0 | PLA |
| 键帽 3u（SPACE） | `keycap_3u.stl` | 53.6 × 16.6 × 5.0 | PLA |
| 校准试件 | `test_coupon.stl` | 134 × 44 × 14.8 | PLA |

整机（键帽顶面）约 **108 × 82 × 23.1 mm**。底座是单件，控制器仓在后方敞开，USB-C 和 RESET 直接可操作。

## 2. 打印设置

### 底座
- 方向：底面朝下，平放；后壁 USB-C 开口有一小段悬垂，可加树状支撑。
- 层高 0.2mm｜壁数 3｜填充 30–40%｜材料 PETG 优先（PLA 也可）。
- 螺丝柱为 M2 自攻底孔（1.7mm），用 M2×6 自攻螺丝；不需要热熔螺母。

### 定位板（建议单独打印）
- 方向：平放，孔轴线垂直热床；不需要支撑。
- 层高 **0.16mm**（1.2mm 厚 = 8 层）｜壁数 3｜填充 40%。
- 打印后立刻用真实 Choc V2 轴体试装；过紧用刀修，过松需重打。

### 键帽
- 方向：**顶面朝下倒扣**，榫槽朝上；不需要支撑。
- 层高 0.12mm｜壁数 3｜填充 15%｜PLA 手感更清脆。
- 建议先打 1 个 1u 试装；2u/3u 的大键内部有加强筋。
- 商业 Choc V2 键帽优先；打印键帽作为 2u/3u 买不到时的备选。

## 3. 先打校准试件（重要）

`SWITCH_PLATE_GAP`（PCB 顶面 → 定位板底面）是整套尺寸里唯一需要实物确认的值。默认 **5.00mm**，试件包含 **3.50 / 4.25 / 5.00mm** 三个测试位：

1. 打印 `test_coupon.stl`（约 15 分钟）。
2. 拿真实 Choc V2 轴体逐个插入。
3. 找到「卡扣清脆扣入 + 轴体塑料底面刚好贴住基座顶面」的位置。
4. 把 `cad/params.scad` 里的 `SWITCH_PLATE_GAP` 改成该值。
5. 重新导出底座/定位板/键帽（见 §6）。

判读：

| 现象 | 结论 |
|---|---|
| 轴体底面与基座之间有缝 | 该位间隙偏大 |
| 扣不上 / 扣上后底面顶住基座 | 该位间隙偏小 |
| 完全贴合 + 卡扣清脆 | 就是它 |

## 4. 装配

1. **底座**：底部四个脚垫沉孔可贴 6–8mm 橡胶脚垫。
2. **PCB**：放在底座 4 个支撑柱上（x=27/81, y=39/56），不需要螺丝；控制器仓朝后。
3. **电池**：放入**控制器仓下方**的电池仓（30×20mm，302030 约 3mm 厚），JST 线经 PCB 的走线槽穿到控制器仓，插到 JST。
4. **定位板**：放在底座ledge上（z=13.6），4 个 M2 孔对准螺丝柱；轴体已经焊在 PCB 上，定位板从上方套过轴体。
5. **螺丝**：M2×6 自攻螺丝 ×4，从定位板四角拧入底座柱。
6. **键帽**：按 [键位图](keymap.md) 装；ENTER 2u、SPACE 3u 使用多轴支撑。
7. **控制器仓**：XIAO 在后方敞开区域；USB-C 从后壁开口露出；RESET 键可直接按；JST 也在该区域。

> 拆装顺序反过来：先拆键帽/定位板，再取 PCB。电池更换需要先取出 PCB。

## 5. 结构注意

- XIAO 用 2×7 2.54mm 排针安装，模块被抬高约 2.5mm；底座后壁的 XIAO 凹槽和 USB-C 开口已上移到 z≈10.5–14.3，不要锉掉。
- XIAO 的 USB-C 端比 PCB 后边多伸出约 1.5mm；底座后壁有对应开口，不要锉掉。
- 控制器仓是敞开的，不盖板，方便刷机和按 RESET；XIAO 天线在仓内靠键区一侧，电池在仓下方偏左，避开天线。
- 定位板后边没有边框（留出控制器仓）；靠 4 个螺丝和左右/前侧 ledge 固定。
- 底座内腔高度按 PCB 支撑 5.0 + PCB 1.6 + 轴板间隙 5.0 + 定位板 1.2 推导；改 `SWITCH_PLATE_GAP` 后整机高度会自动变化，重新导出即可。XIAO 模块顶面约在 14.3mm，低于 14.8mm 的底座外沿。DO-35 二极管在 PCB 背面、键区下方，电池已移到控制器仓下方避开它们。
- 键帽底部到定位板顶面间隙 3.3mm ≥ 轴体行程 3.0mm。

## 6. 重新导出

用本机的 OpenSCAD：

```bash
OSC="$HOME/openscad-portable/openscad-2021.01/openscad.exe"
"$OSC" -o cad/output/stl/case_bottom.stl --export-format binstl cad/case_bottom.scad
"$OSC" -o cad/output/stl/plate.stl --export-format binstl cad/plate.scad
"$OSC" -o cad/output/stl/keycap_1u.stl --export-format binstl cad/keycap_1u.scad
"$OSC" -o cad/output/stl/keycap_2u.stl --export-format binstl cad/keycap_2u.scad
"$OSC" -o cad/output/stl/keycap_3u.stl --export-format binstl cad/keycap_3u.scad
"$OSC" -o cad/output/stl/test_coupon.stl --export-format binstl cad/test_coupon.scad
```

预览：

```bash
"$OSC" -o cad/output/preview/assembly_hero.png --imgsize=1600,1200 --camera=54,41,12,68,0,155,250 cad/assembly.scad
```

## 7. 已验证

- 所有 STL 均为闭合网格（`tools/check_cad.py`：0 条非流形边）
- 包围盒与设计值一致：底座 108×82×14.8；定位板 102×57×1.2；键帽 17.6/35.6/53.6 ×16.6×5
- 键位坐标与 PCB `SWITCHES`/`KEYCAPS` 完全一致（x=18/36/54/72/90；y=30.5/47.5/64.5）

> 3D 预览中的键帽是无刻字的示意模型；实际可使用商业 Choc V2 键帽。

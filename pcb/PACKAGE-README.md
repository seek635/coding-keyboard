# ClaudePad PCB 设计包

版本 v1.0 · 2026-10-26

11 键 Claude Code 宏键盘的 PCB 设计：**90 × 76 × 1.6 mm，2 层**。XIAO 采用 **2×7 2.54mm 排针穿孔焊接**（14 个 1.0mm 孔），板上没有 SMD 元件。
R1/C1 是设计上的空位，不装轴；其余 14 个轴位全部使用（9 个单键 + 2u ENTER 双轴 + 3u SPACE 三轴），共 11 个键帽、11 个二极管。

## 打样参数

| 项目 | 值 |
|---|---|
| 尺寸 | 90 × 76 mm |
| 层数 / 板厚 | 2 层 / 1.6 mm |
| 铜厚 | 1 oz |
| 表面处理 | 无铅喷锡（或沉金） |
| 阻焊 / 丝印 | 绿色 / 白色（颜色随意） |
| 最小线宽 / 间距 | 0.25 / 0.20 mm |
| 过孔 / 最小孔径 | 0.3 mm / 0.3 mm |
| 贴片 | 不需要 SMT，全部手焊 |

打样时直接上传 `output/claudepad-jlcpcb-gerbers.zip`（只含 2 层铜、阻焊、丝印、板框和钻孔，嘉立创可直接识别）。`output/claudepad-gerbers.zip` 是完整版，额外带 Fab/Paste/坐标，也兼容。

## 文件

| 路径 | 说明 |
|---|---|
| `claudepad.kicad_pro` | KiCad 10 工程 |
| `claudepad.kicad_pcb` | PCB 源文件（28 个封装） |
| `claudepad.kicad_dru` | 自定义板边间距规则 |
| `generate_pcb.py` | 参数化生成 PCB 的脚本 |
| `make_bom.py` | 从 PCB 生成 BOM |
| `clean_footprints.py` | 清理封装丝印的辅助脚本 |
| `footprints/ClaudePad.pretty/` | 全部封装 |
| `output/gerbers/` | Gerber + Excellon 钻孔 + job 文件 |
| `output/claudepad-jlcpcb-gerbers.zip` | 嘉立创直传包（仅必需层） |
| `output/claudepad-gerbers.zip` | 完整 Gerber 包（含 Fab/Paste/坐标） |
| `output/claudepad-pos.csv` | 坐标文件（手焊可忽略） |
| `output/claudepad-bom.csv` | PCB 元件 BOM |
| `output/drc.rpt` | DRC 报告 |
| `output/claudepad-stats.txt` | 板卡统计 |
| `output/preview/` | 顶层/底层预览（SVG + PNG） |
| `output/3d/` | PCB 的 STEP 与 3D PDF |
| `PCB-GUIDE.md` | 制造、网络表与焊接顺序 |

## 焊接要点

详见 `PCB-GUIDE.md`，核心顺序：

1. **先焊 XIAO 背面的 BAT+/BAT− 电池线**，线从模块右侧引出，留够长度。
2. 把 **2×7 2.54mm 排针**插进 XIAO 的 14 个穿孔，先焊模块一侧；再插进 PCB 的 U1 孔位，焊 14 个 1.0mm 孔。USB-C 朝后，`1` 丝印对齐模块 pin1。**焊完从背面把过长针脚剪到 ≤4mm**（PCB 下方净空 5mm）。
3. 焊 14 个 Kailh Choc V2 轴体（正面）。每个轴位左下角短丝印线是 pin1 侧。
4. 翻到背面焊 11 个 1N4148（DO-35）。二极管在轴位之间的空行里水平放置；以背面短丝印线为准装阴极，不要装到任何轴位正下方。
5. 焊 JST-PH 2.0：`pin1 = BAT+`，`pin2 = BAT-`。
6. 把 XIAO 的两根电池线焊到 BAT1（JST 旁，丝印 `BAT+` / `BAT-`）。
7. 测 BAT+ / BAT- 不短路后再插电池。
8. **R1/C1 不装轴**，不要补孔；XIAO 焊盘 4–6、12–14 保持不接。

> XIAO 用排针抬高约 2.5mm；外壳后壁 USB-C 开口已上移到 z≈10.5–14.3，控制器仓敞开。主板下方只有 14 个排针孔，没有电池窗口。

## 验证

- KiCad DRC：**0 violations / 0 unconnected pads / 0 footprint errors**（`output/drc.rpt`）。
- XIAO：14 个 1.0mm 穿孔焊盘（2×7 2.54mm 排针），无 SMD。
- BOM：11 × 1N4148、14 × Choc V2、1 × XIAO nRF52840、1 × JST-PH。
- 二极管焊接空间：本体到最近孔/支撑柱 +1.60 mm，焊盘到最近其它焊盘 +1.12 mm。
- 板框、键位坐标与外壳/定位板一致。

## 重新生成

需要 KiCad 10 自带的 Python（Windows 默认 `D:/kicad/bin/python.exe`）。在本目录运行：

```bash
D:/kicad/bin/python.exe generate_pcb.py
D:/kicad/bin/python.exe make_bom.py
```

Gerber / 钻孔 / 坐标 / 3D 用 `kicad-cli` 重新导出，命令见 `PCB-GUIDE.md` 与项目 `README.md`。

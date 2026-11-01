# ClaudePad PCB 制造与焊接

> PCB 源文件：[pcb/claudepad.kicad_pcb](../pcb/claudepad.kicad_pcb)
> 外壳/定位板/键帽：[cad.md](cad.md)
> 购物清单：[BOM.md](BOM.md)

## 1. 板卡规格

| 项目 | 数值 |
|---|---|
| 尺寸 | **90 × 76 mm** |
| 层数 | **2 层**（F.Cu / B.Cu） |
| 板厚 | 1.6 mm |
| 铜厚 | 1 oz |
| 表面处理 | 沉金/无铅喷锡均可（推荐无铅喷锡） |
| 最小线宽/间距 | 0.25 / 0.20 mm |
| 过孔 | 0.3 mm 钻孔 / 0.6 mm 焊盘 |
| 安装 | 无 PCB 螺丝孔；由外壳 4 个支撑柱托住，定位板压住轴体 |

2 层分配：

- **F.Cu**：5 条列线 + XIAO 引脚扇出 + 与列线不冲突的开关→二极管短接线
- **B.Cu**：ROW0 / ROW1 / ROW2 行线、ENTER/SPACE 并联、电池走线、其余二极管短接线

> ROW2 总线沿板底边（Y=76.5）走，避开 ENTER 的阳极垂直段。

## 2. 制造文件

```
pcb/output/claudepad-pcb-design.zip  完整设计包（KiCad 工程 + 制造文件 + BOM + 预览 + 3D）
pcb/output/claudepad-jlcpcb-gerbers.zip  嘉立创直传包（2 层铜/阻焊/丝印/板框/钻孔）
pcb/output/claudepad-gerbers.zip     完整 Gerber 包（含 Fab/Paste/坐标）
pcb/output/gerbers/                  Gerber + Excellon 钻孔 + job 文件
pcb/output/claudepad-pos.csv         坐标文件（手焊可忽略）
pcb/output/claudepad-bom.csv         PCB 元件 BOM（11 二极管 / 14 轴 / XIAO / JST）
pcb/output/claudepad-stats.txt       板卡统计
pcb/output/drc.rpt                   DRC 报告（0 错误 / 0 未连接）
pcb/output/preview/                  顶层/底层 SVG 与 PNG 预览
pcb/claudepad.kicad_pro               KiCad 10 工程
pcb/claudepad.kicad_pcb               PCB 源文件
pcb/generate_pcb.py                   参数化生成脚本
pcb/make_bom.py / make_package.py     生成 BOM / 设计包
pcb/claudepad.kicad_dru               自定义板边间距规则（0.3mm）
```

打样参数：**2 层、1.6mm、1oz、无铅喷锡、绿色阻焊/白色丝印**（颜色随意）。不需要 SMT 贴片，全部手焊。直接上传 `claudepad-jlcpcb-gerbers.zip` 即可；想连源码一起留档就发 `claudepad-pcb-design.zip`。

> **R1/C1 是设计空位**（STOP 右侧、MODEL 正下方），PCB 上不布开关，外壳定位板也没有开孔。不要按 3×5 把这一格补满；其余 14 个轴位是 9 个单键 + ENTER 2 轴 + SPACE 3 轴。

## 3. 网络表（手焊核对）

### XIAO nRF52840（U1，14 个穿孔焊盘）

U1 使用 **2×7 2.54mm 排针**穿孔焊接：PCB 上 14 个 **1.0mm 孔 / 1.7mm 焊盘**，间距 2.54mm；引脚顺序与 Seeed 官方 XIAO DIP 封装一致（旋转到 USB-C 朝后）。

| 焊盘 | XIAO 信号 | 网络 |
|---|---|---|
| 1 | D0 | ROW0 |
| 2 | D1 | ROW1 |
| 3 | D2 | ROW2 |
| 4–6 | D3–D5 | 未用 |
| 7 | D6 | COL0 |
| 8 | D7 | COL1 |
| 9 | D8 | COL2 |
| 10 | D9 | COL3 |
| 11 | D10 | COL4 |
| 12–14 | 3V3 / GND / 5V | 未用 |

> 电池负极**不要**接到 XIAO 的 GND 焊盘；电池正负极走模块背面的 BAT 焊盘，引线到 JST 旁的 BAT1（见 §5）。

### 开关与二极管

| 开关 | 位置 (mm) | 列 | 二极管 | 行 |
|---|---|---|---|---|
| SW1 PERM | 18, 30.5 | COL0 | D1 | ROW0 |
| SW2 MODEL | 36, 30.5 | COL1 | D2 | ROW0 |
| SW3 CMD | 54, 30.5 | COL2 | D3 | ROW0 |
| SW4 UP | 72, 30.5 | COL3 | D4 | ROW0 |
| SW5 VOICE | 90, 30.5 | COL4 | D5 | ROW0 |
| SW6 STOP | 18, 47.5 | COL0 | D6 | ROW1 |
| SW7 LEFT | 54, 47.5 | COL2 | D7 | ROW1 |
| SW8 DOWN | 72, 47.5 | COL3 | D8 | ROW1 |
| SW9 RIGHT | 90, 47.5 | COL4 | D9 | ROW1 |
| SW10 ENTER_A | 18, 64.5 | COL0 | D10 | ROW2 |
| SW11 ENTER_B | 36, 64.5 | COL0 | —（与 SW10 并联） | — |
| SW12 SPACE_A | 54, 64.5 | COL2 | —（与 SW13 并联） | — |
| SW13 SPACE_B | 72, 64.5 | COL2 | D11 | ROW2 |
| SW14 SPACE_C | 90, 64.5 | COL2 | —（与 SW13 并联） | — |

- 每个开关的 **pin1** 是靠近短丝印线的那一侧（每个轴位左下角）；pin1 接二极管阳极/并联网络，pin2 接列线。
- 二极管在 **PCB 背面、轴位之间的空行**，水平放置，不在任何轴位正下方：
  - D1–D5：y = 38.5，x = 18 / 36 / 54 / 72 / 90（R0 与 R1 之间）
  - D6–D9：y = 55.5，x = 18 / 54 / 72 / 90（R1 与 R2 之间）
  - D10/D11：y = 74.5，x = 27 / 63（R2 下方，旋转 180°）
- 所有二极管以背面**短丝印线为阴极标记**；D1–D9 阴极朝右，D10/D11 因旋转 180° 阴极朝左。
- 二极管焊盘到最近其它焊盘 ≥ **1.12 mm**，本体到最近孔/支撑柱 ≥ **1.6 mm**；不在轴位下方，镊子和烙铁可以从背面直接操作。
- ENTER 的 SW10/SW11、SPACE 的 SW12/SW13/SW14 分别并联；只需要 D10、D11 两个二极管。

## 4. 焊接顺序

1. **先焊 XIAO 电池线**（见 §5）：BAT+/BAT- 在模块背面；先焊两根 26–28AWG 线，线从模块右侧引出。
2. 把 2×7 2.54mm 排针插进 XIAO 的 14 个穿孔，先焊模块一侧；再把排针插进 PCB 的 U1 孔位，焊 14 个孔。USB-C 朝后边（y 小的一侧）；`1` 丝印对齐模块 pin1。**焊完后从 PCB 背面把过长的排针脚剪到 ≤4mm**（PCB 下方到外壳底只有 5mm）。
3. 焊 14 个 Choc V2 轴体（正面）。每个轴位的左下角短丝印线是 **pin1** 侧；轴体侧卡扣决定方向，不要硬压。
4. 翻到背面，焊 11 个 1N4148（DO-35）。二极管在轴位之间的空行里水平放置（D1–D5 在 R0/R1 之间，D6–D9 在 R1/R2 之间，D10/D11 在 R2 下方）；以背面短丝印线为准装阴极，不要装到任何轴位正下方。
5. 正面焊 JST-PH 2.0（J1）。丝印 `+ JST` 对应 pin1（BAT+），`- JST` 对应 pin2（BAT-）。
6. 把 XIAO 的两根电池线焊到 BAT1（JST 旁，丝印 `BAT+` / `BAT-`）。
7. 用万用表测 BAT+ / BAT- 不短路，再插电池。
8. 上电测试矩阵、蓝牙、按键行为。

## 5. XIAO 电池焊盘与电池线

XIAO 用 2×7 排针抬高后，模块背面的 BAT+/BAT- 焊盘可以从侧面操作；**PCB 不再在模块下方开电池窗口**。模块下方只有 14 个排针孔。

BAT1 在 JST 旁边（模块右侧，主板投影外）：

- BAT+：x=70.0, y=17.5
- BAT-：x=70.0, y=19.5
- 两根线从 XIAO 背面 BAT 焊盘引出，沿模块右侧走到 BAT1，再经 JST 接电池。

推荐做法：

1. 先剪两段 26–28AWG 短线，焊到 XIAO 背面的 BAT+ / BAT-（装排针之前更容易）。
2. 把线从模块右侧引出，留够长度。
3. 装排针、焊 PCB 的 14 个孔。
4. 把两根线分别焊到 BAT1 的 1/2 焊盘（丝印 `BAT+` / `BAT-`）。
5. 检查极性后再插电池。

## 6. 天线与结构注意

- XIAO 的板载天线在模块 **+Y 端**（靠近键区一侧）。PCB 在该区域没有走线；电池在键区下方，远离天线。装壳时不要在该区域放金属或大面积电池。
- Choc V2 的中心定位柱会伸出 1.6mm PCB 底面约 1.7mm；二极管已移到轴位之间的空行，避开所有轴脚/定位柱，不要改回轴位下方。
- XIAO 用 2×7 2.54mm 排针抬高约 2.5mm；外壳后壁的 USB-C 开口和 XIAO 凹槽已上移到 z≈10.5–14.3，控制器仓敞开，RESET 仍可直接按。**排针脚要剪短**：PCB 下方净空 5mm，针脚留 ≤4mm。
- 模块的 USB-C 端比 PCB 后边多伸出约 1.5mm；外壳后壁有对应开口，不要锉平。
- PCB 没有螺丝孔，靠外壳 4 个支撑柱和定位板/轴体压住；不要把支撑柱剪掉。

## 7. 检查项

1. 所有 GND/3V3/5V 焊盘（U1 的 12–14）保持未连接（本板不需要）。
2. 每个二极管方向：背面短丝印线一侧 = 色环；位置在轴位之间的空行，不在任何轴位正下方。
3. ENTER 两个开关、SPACE 三个开关的 pin1 都在同一个阳极网络；不要漏掉并联线（板上已走好，检查焊点即可）。
4. 电池极性：JST pin1 = BAT+，pin2 = BAT-；用万用表确认。
5. 刷固件后用键盘测试网站逐键检查；再按 [host/README.md](../host/README.md) 测上位机。

## 8. 已验证

- KiCad DRC：**0 violations, 0 unconnected pads, 0 footprint errors**（2026-10-27，2 层改版后复检，`pcb/output/drc.rpt`）
- XIAO 为 **14 个 1.0mm 穿孔焊盘**（2.54mm 排针），板上没有 SMD 元件
- 2 层 Gerber / Excellon / 坐标 / BOM / 设计包已重新导出（2026-10-27）
- 二极管焊接空间检查：本体到最近孔/支撑柱 **+1.60 mm**，焊盘到最近其它焊盘 **+1.12 mm**
- 板框 90 × 76 mm、1.6 mm；最小线宽 0.25 mm、最小孔径 0.3 mm（`claudepad-stats.txt`）
- 与外壳/定位板的坐标一致（见 [cad.md](cad.md)）

> 3D 预览中的 PCB 渲染没有加载开关/主控的 3D 模型，只显示裸板、焊盘和丝印；成品外观以 [claudepad-hero.png](preview/claudepad-hero.png) 为准。

## 9. 封装来源

- Choc V2 1u：`kiswitch/kiswitch` 的 `SW_Kailh_Choc_V2_1.00u.kicad_mod`
- XIAO nRF52840 THT：基于 Seeed 官方 `XIAO-nRF52840-DIP.kicad_mod` 的 14 个 2.54mm 穿孔焊盘，旋转到 USB-C 朝后；PCB 孔径改为 1.0mm 方便手焊。SMD 版本留在封装库里仅作参考。
- 1N4148 DO-35、JST-PH 2.0、BAT 焊盘：本项目自建

## 10. 重新生成与打包

需要 KiCad 10 自带的 Python（Windows 默认 `D:/kicad/bin/python.exe`）：

```bash
D:/kicad/bin/python.exe pcb/generate_pcb.py
D:/kicad/bin/python.exe pcb/make_bom.py
python pcb/make_package.py
```

> ⚠️ `pcb/generate_pcb.py` 目前仍是**旧的 4 层版**（行线走 In1.Cu/In2.Cu）。现在仓库里的 `pcb/claudepad.kicad_pcb` 和 2026-10-27 的 Gerber 是 **2 层版**（行线走 B.Cu），两者不一致；直接重跑脚本会用 4 层版**覆盖**这块 2 层板。要重新生成 2 层板，得先把脚本里的行线改到 B.Cu（并去掉 In1/In2 层），改好之前不要运行它。

Gerber / 钻孔 / 坐标 / 3D 用 `kicad-cli pcb export ...` 重新导出，输出目录仍为 `pcb/output/`。打包前先重跑 DRC：

```bash
D:/kicad/bin/kicad-cli.exe pcb drc --output pcb/output/drc.rpt --severity-all --exit-code-violations pcb/claudepad.kicad_pcb
```

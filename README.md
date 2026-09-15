# ClaudePad

> 蓝牙（BLE）编程专用实体小键盘 —— 为 Claude Code / 终端场景定制

一个 11 键 + 侧边审批拨杆的紧凑键盘，把 Claude Code 里最高频的操作从键盘组合键变成**单手一按**。

```
┌──────────┬────┬──────┬────────┬────────┐
│ 访问等级  │ ↑  │ 模型  │ 命令行  │  停止   │
├────┬────┬────┴────┴────────┤        │
│ ←  │ ↓  │ →    │   回车 2u   │        │
├────┴────┴──────┴────┬───────┴────────┤
│      空格 4u        │      语音       │
└─────────────────────┴────────────────┘
                                    ╱ 审批拨杆（OFF / ON）
```

**核心设计目标**：键盘本身不改变 Claude Code 的任何行为。拨杆 OFF 时它就是一个普通键盘；拨杆 ON 时才介入。

---

## 项目状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 产品需求（PRD） | ✅ 完成 | `docs/PRD.md` |
| 结构设计（3D 打印） | ✅ 已渲染验证 | 6 个 STL 全部水密、尺寸零偏差 |
| 固件（ZMK） | ⚠️ 未编译 | 语法依据官方文档逐条核对，本地无 Zephyr 工具链 |
| 审批拨杆（宿主程序） | ✅ 协议层验证 | 31 个用例通过，未在真机 Claude Code 上跑通 |
| PCB | ⚠️ 未打样 | 封装坐标经两个独立开源库交叉验证 |
| 采购 | ✅ 清单完成 | `docs/采购清单.md` |

**未完成**：实机联调（画板 → 打样 → 焊接 → BLE 配对 → hooks 真机验证）。

---

## 硬件

| 部件 | 选型 | 备注 |
|---|---|---|
| 主控 | nice!nano v2（nRF52840） | ZMK 生态最成熟 |
| 轴体 | Kailh Choc 矮轴 35–40g | 编程敲击密度高，轻力度降疲劳 |
| 定位板 | 3D 打印，**厚 1.2mm** | Choc 标准值，不是 MX 的 1.5–1.6 |
| 审批拨杆 | SPDT 拨动开关 | 三脚，拨过去停住；轴套长度需 ≥ 9mm |
| 电池 | 3.7V 锂电 300–500mAh | **JST 1.25** 接口 |
| 反馈 | WS2812 | 可选 |

**整机尺寸**：107.10 × 71.10 × **23.10** mm（X 向 111.20 含右侧拨杆凸台）

### 垂直尺寸链

```
z = 23.10  ┌─────────────┐  键帽顶面
           │   键帽 5.0   │
z = 18.10  ├─────────────┤  键帽底面
           │  ★ 间隙 3.3  │  ← 必须 ≥ 键程 3.0，否则按不下去
z = 14.80  ├═════════════┤  定位板上表面
           │  定位板 1.2  │
z = 13.60  ├─────────────┤  定位板底面
           │  轴体卡扣 5.0 │  ← 同时是主控净空（唯一强耦合点）
z =  8.60  ├─────────────┤  PCB 上表面
           │    PCB 1.6   │
z =  7.00  ├─────────────┤  PCB 下表面
           │  电池/走线 5.0│
z =  2.00  ├─────────────┤  底板上表面
           │    底板 2.0   │
z =  0.00  └─────────────┘  桌面
```

> ⚠️ **键帽间隙必须 ≥ 键程**。键帽裙边 17.6mm 比定位板轴孔 13.8mm 宽，塞不进孔里，
> 所以键帽只能悬在板上方，下压空间必须靠这个间隙提供。写成 0.3mm 会让键盘**完全按不下去**。

---

## 目录结构

```
cad/          参数化 3D 模型（OpenSCAD）+ 渲染产物
  lib/params.scad   ★ 所有尺寸的唯一来源
  plate.scad        定位板
  case_bottom.scad  底座（腔体/走线/散热/固定）
  keycap.scad       键帽（1u / 2u / 4u）
  test_coupon.scad  校准试件（打印前必打）
  output/*.stl      已渲染验证的 6 个 STL
  output/viewer.html 可交互三维查看器（three.js）

firmware/     ZMK shield 固件配置
  boards/shields/claudepad/*.keymap   ★ 键位与手势

host/         宿主程序（审批拨杆实现）
  claudepad_daemon.py   ★ 常驻：HTTP hook 应答 + 键盘监听
  claudepad_core.py     决策核心
  install_hook.py       一键安装到 Claude Code

pcb/          PCB 网表与接线图（json / md / svg / png）
tools/        校验与生成脚本（14 个）
docs/         设计文档
```

---

## 快速开始

### 看三维模型（零依赖）

```bash
python tools/view_model.py          # 起本地服务 + 开浏览器
```

或直接看 `cad/output/preview/*.png`。

### 校验设计（只需 Python）

```bash
python tools/check_env.py           # 先跑这个，看缺什么
python tools/check_dims.py          # 23 项结构设计规则
python tools/verify_geometry.py     # 孔位 / 对称 / 键帽对位
python tools/check_keymap.py        # 固件 ↔ 结构 交叉校验
```

**只有导出 STL 才需要 OpenSCAD**（`python tools/export_stl.py`）。
校验逻辑全部纯 Python 实现，这是刻意设计——OpenSCAD 是整条链里最难装的东西。

### 打印顺序

**别一次打全套。**

| 顺序 | 文件 | 验证什么 | 耗时 |
|---|---|---|---|
| ① | `00_test_coupon.stl` | **轴体卡扣间隙**（唯一需实测的参数） | 15 min |
| ② | `02_plate.stl` | 轴孔松紧 | 40 min |
| ③ | `05_keycap_4u.stl` | 三轴支撑手感 | 35 min |
| ④ | `01_case_bottom.stl` | 孔位与装配 | 3–4 h |

### 审批拨杆（宿主程序）

```bash
python host/install_hook.py         # 安装到 Claude Code（自动备份 + 幂等）
python host/claudepad_daemon.py     # 启动常驻进程
python host/switchctl.py on|off     # 手动切换状态（没有硬件也能测）
python host/test_hook.py            # 31 个用例
```

---

## 三个关键设计决策

### 1. 键盘是无状态的

键盘收不到权限档位、模型名、审批状态。所以「长按复位到 default」「长按循环切换模型」
**键盘做不了**——它不知道当前在哪一档。

方案：键盘只**发信号**（`Ctrl+Alt+Shift+F13`/`F14` 这种极难误触的组合），
由读取终端状态栏的上位机执行真正的操作。

### 2. 审批拨杆走 hooks，不走文本嗅探

| | 终端文本嗅探 | Hooks |
|---|---|---|
| 稳定性 | 匹配文案，**改文案就失效** | 官方接口，不依赖文案 |
| 能否分级 | 难结构化 | 直接拿到 `tool_name` + `tool_input` |
| 误判 | 天然会误判 | 结构化字段，无误判 |

官方机制里有一条是整个方案成立的关键：

> `PreToolUse` 返回 `{"hookSpecificOutput":{"permissionDecision":"allow"}}` → 跳过权限提示
> **返回空（exit 0 无输出）→ 不算批准** → 走原生权限流程

这使「拨杆 OFF = 产品不存在」成立——不改变用户任何既有行为。

**实测性能**：command 模式 510ms/次（每次起进程，不可接受）→ **HTTP 模式 15ms/次**（采用）。

**两条铁律**：
1. **失效安全** —— 任何故障（进程没跑 / 令牌错 / 脚本异常）都退化为「正常询问」，绝不误批
2. **只升不降** —— hook 只返回 `allow`，从不返回 `ask`/`deny`

### 3. 大键必须多轴支撑

4u 空格单轴支撑时 PLA 挠度 **1.487mm**（明显翘），三轴并联降到 **0.186mm**（降 87.5%）。
回车 2u 用 2 轴，空格 4u 用 3 轴。这不是可选项。

---

## 单一数据源

**所有尺寸只有一个来源：`cad/lib/params.scad`。** 任何地方要数字都必须解析它，不能手抄。

已落实：校验脚本、PCB 网表、行程图、**三维查看器**全部从它读取。

> **教训**：渲染出的 PNG 是快照（改参数就过期），手写 HTML 是副本（改参数就骗人）。
> 展示层也必须生成——否则它比没有更糟，因为它会**自信地展示错误信息**。

改完 `params.scad` 后：

```bash
python tools/check_dims.py && python tools/lint_scad.py && \
python tools/verify_geometry.py && python tools/export_stl.py && \
python tools/gen_viewer.py && python tools/draw_travel.py
```

---

## 已知限制

- **固件未编译**：本地无 Zephyr 工具链。语法依据 ZMK 官方文档（shield 结构 / hold-tap /
  tap-dance / macros）逐条核对，并做了静态一致性校验，但首次构建可能需微调。
- **审批拨杆未在真机验证**：本机无 Claude Code CLI，验证在协议层完成（按官方文档构造
  输入输出 + 验证失效路径）。接入步骤见 `docs/审批拨杆技术验证.md`。
- **PCB 未打样**：封装坐标经交叉验证，但未生成实际 PCB 文件跑 DRC。
- **`SWITCH_PLATE_GAP` 待实测**：Choc 官方未公开定位板高度，社区实测 3.5–6.0mm 浮动。
  用 `00_test_coupon.stl` 实测后回填 `params.scad`。

---

## 文档

| 文档 | 内容 |
|---|---|
| `docs/PRD.md` | 产品需求、键位定义、手势表、HID 映射 |
| `docs/结构设计规格书.md` | 尺寸链、公差、装配顺序、走线 |
| `docs/固件设计说明.md` | ZMK 设计原理与取舍 |
| `docs/PCB设计规格书.md` | 封装坐标、布局、打样参数 |
| `docs/审批拨杆技术验证.md` | hooks 路线可行性报告 |
| `docs/采购清单.md` | BOM 与选型理由 |

---

## 许可

未定。

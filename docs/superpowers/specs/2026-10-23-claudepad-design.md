# ClaudePad 设计规格

- 日期：2026-10-23（2026-10-25 更新：取消审批拨杆与电源开关；完成 4 层 PCB 与 3D 打印外壳/定位板/键帽）
- 状态：已实现
- 需求来源：`ClaudePad-工程与键位.md`（原需求中的审批拨杆/自动批准已取消）
- 配套文档：`docs/BOM.md`、`docs/pcb.md`、`docs/cad.md`、`docs/preview/`、`docs/wiring.md`、`docs/keymap.md`

## 1. 目标

做一块专用于 Claude Code 的 ZMK 宏键盘：

- 11 个实体按键。
- 4 层 PCB，轴体/二极管/XIAO/JST 可直接焊接。
- 3D 打印底座、定位板、键帽；控制器仓敞开，USB-C/RESET 可直接操作。
- ZMK 固件通过 USB / BLE 输出普通 HID 键码与信号键。
- Windows 上位机读取 Claude Code 状态，执行权限复位与模型循环。
- **不提供审批拨杆/自动批准**；权限提示由人工回答。

非目标：注塑外壳、SMT 贴片、macOS/Linux 上位机（代码结构保留扩展点）。

## 2. 关键设计决策

1. **矩阵 3×5，11 个电气交点**：11 个二极管；R1/C1 为空位；矩阵走 4 层 PCB。
2. **方向键采用标准倒 T**：`↑` 位于 `↓` 正上方，`← ↓ →` 同一行。
3. **主控 Seeed XIAO nRF52840（`xiao_ble`）**：自带 RESET 键、USB-C、锂电充电和 BAT 焊盘。
4. **无电源开关**：JST 电池插头 + ZMK 深度睡眠；长期存放拔电池。
5. **无审批拨杆/自动批准**：不使用 F13，不安装 `hook_permission.py`。
6. **信号键**：PERM 单击附带 `F16` 档位同步；权限复位 `Ctrl+Alt+Shift+F15`；模型循环 `Ctrl+Alt+Shift+F14`。
7. **长按一律“按下即输出”**：避免 `@`、Tab 等字符自动重复。
8. **PCB 4 层、90×76mm**：F 走列线、In1/In2 走行线、B 走二极管/电池；DRC 0 错误。
9. **外壳 108×82mm、总高约 23.1mm**：定位板 1.2mm，键帽前先打 gap 校准试件；控制器仓敞开。

## 3. 硬件

### 3.1 主控与供电

- Seeed XIAO nRF52840 标准版，ZMK 板名 `xiao_ble`；用 **2×7 2.54mm 排针穿孔焊接**（PCB 上 14 个 1.0mm 孔），模块抬高约 2.5mm；排针脚焊后剪到 ≤4mm，避开外壳底（净空 5mm）。
- USB-C 与 RESET 键在同一条边，外壳需同时露出；USB-C 开口按排针高度上移。
- 电池线从 XIAO 背面 BAT+/BAT− 焊盘直接引到 JST 旁的 BAT1（不在主板下方）；电池可插拔。
- 无电源开关；`CONFIG_ZMK_SLEEP=y` 深度睡眠省电。

### 3.2 电气矩阵

| 信号 | XIAO 引脚 |
|---|---|
| R0 | D0 |
| R1 | D1 |
| R2 | D2 |
| C0 | D6 |
| C1 | D7 |
| C2 | D8 |
| C3 | D9 |
| C4 | D10 |

D3/D4/D5 留空（D4/D5 为 I2C）。

- 二极管方向：`col2row`，1N4148 阴极（色环）朝行线。
- ENTER 2u：两个轴并联，共用 1 个二极管（R2/C0）。
- SPACE 3u：三个轴并联，共用 1 个二极管（R2/C2）。
- R1/C1 空位，不接线。

### 3.3 物理与键位

```
PERM   MODEL   CMD    ↑    VOICE
STOP   (空)           ←    ↓    →
ENTER (2u)          SPACE (3u)
```

| 位置 | 键 | 行 | 列 |
|---|---|---|---|
| 0 | PERM | 0 | 0 |
| 1 | MODEL | 0 | 1 |
| 2 | CMD | 0 | 2 |
| 3 | ↑ | 0 | 3 |
| 4 | VOICE | 0 | 4 |
| 5 | STOP | 1 | 0 |
| 6 | ← | 1 | 2 |
| 7 | ↓ | 1 | 3 |
| 8 | → | 1 | 4 |
| 9 | ENTER | 2 | 0 |
| 10 | SPACE | 2 | 2 |

### 3.4 PCB

- 4 层、90×76×1.6mm；F.Cu 列线，In1.Cu ROW0/ROW1，In2.Cu ROW2，B.Cu 二极管/并联/电池。
- 14 个 Choc V2 轴位、11 个 1N4148（DO-35，背面）、XIAO 14 个 1.0mm 穿孔焊盘、JST-PH 2.0。
- 二极管在轴位之间的空行里水平放置，避开 Choc V2 中心定位柱/轴脚；本体到最近孔 ≥1.6mm，焊盘到最近其它焊盘 ≥1.1mm。
- XIAO 背面 BAT 焊盘直接引线到 JST 旁的 BAT1；PCB 在模块下方不再开电池窗口，只有 14 个排针孔。USB-C 端伸出 PCB 约 1.5mm。
- 无 PCB 螺丝孔，由外壳 4 个支撑柱托住；DRC 0 错误、0 未连接。
- 制造文件在 `pcb/output/gerbers/`，说明见 `docs/pcb.md`。

### 3.5 外壳 / 定位板 / 键帽

- 底座 108×82×14.8mm（到定位板顶面），整机含键帽约 23.1mm；底部 2.0mm，壁厚 2.4mm。
- 控制器仓在后方敞开；后壁有 XIAO 端部凹槽和 USB-C 开口（z≈10.5–14.3，已按 2.5mm 排针高度上移），RESET 直接从上方按。
- 定位板 102×57×1.2mm，14 个 14.6mm 轴孔 + 侧卡扣槽；4× M2 自攻螺丝。
- 键帽 1u/2u/3u 可打印；`SWITCH_PLATE_GAP` 用 `test_coupon.stl` 实测校准。
- STL 检查：全部闭合、0 条非流形边；尺寸与 PCB 坐标一致。

## 4. 固件（ZMK）

标准 zmk-config 结构，shield 名 `claudepad`，目标板 `xiao_ble`。

### 4.1 行为

| 键 | 单击 | 双击 | 长按 |
|---|---|---|---|
| PERM | `Shift+Tab` + `F16` | — | 250ms → `Ctrl+Alt+Shift+F15` |
| MODEL | 宏 `/model` + Enter | — | 250ms → `Ctrl+Alt+Shift+F14` |
| CMD | `/` | — | 200ms → `@` |
| STOP | `Esc` | 200ms 内 → `Ctrl+C` | 1200ms → `Ctrl+C` ×2 |
| ENTER | `Enter` | 200ms 内 → `Shift+Enter` | — |
| SPACE | `Space` | — | 300ms → `Tab`；quick-tap 150ms、prior-idle 120ms |
| VOICE | `Space` | 180ms 内 → `/voice` | 按住 → `Space` 对讲 |
| 方向键 | 系统原生自动重复 | — | — |

实现：`hold-tap`、`tap-dance`、`behavior-macro` / `behavior-macro-one-param`，不写 C 代码。

### 4.2 时间参数

- STOP：tap-dance 200ms + 内层 hold-tap 1000ms = 长按 1200ms。
- VOICE：tap-dance 180ms + 内层 hold-tap 50ms；按住约 230ms 后开始对讲。
- 宏 `wait-ms = 15`、`tap-ms = 10`。

### 4.3 构建

- `build.yaml`：`xiao_ble` + `claudepad`。
- `.github/workflows/build.yml` 使用 `zmkfirmware/zmk/.github/workflows/build-user-config.yml@main`。
- `config/west.yml` 引入 ZMK `main`。
- 本机没有 Zephyr SDK，固件编译以 GitHub Actions 为准。

## 5. 上位机（Windows）

Python 3.12，标准库 + ctypes，零第三方依赖。

### 5.1 组件

```
host/
  claudepad_host/
    core.py       状态目录、原子 JSON、会话合并、权限循环、模型选择
    winapi.py     SendInput、RegisterHotKey、GetAsyncKeyState、单实例
    actions.py    复位权限、循环模型
    daemon.py     F15/F14/F16 热键消息循环（注册失败时轮询 F14/F15）
    installer.py  settings.json 合并/备份/卸载
    __main__.py   run / install / uninstall / status
  scripts/
    statusline.py        写入模型/会话状态并输出状态栏
    hook_state.py        UserPromptSubmit / Stop / SessionStart / PermissionRequest：写入权限档位
  tests/
```

### 5.2 状态目录

`%LOCALAPPDATA%\ClaudePad\`：

| 文件 | 写入者 | 内容 |
|---|---|---|
| `config.json` | 安装器/用户 | 模型循环列表、权限循环、假设档位 |
| `sessions/<id>.status.json` | statusline | 模型 id/名称、cwd、更新时间 |
| `sessions/<id>.mode.json` | hooks | 权限档位、cwd、更新时间 |
| `daemon.log` | 守护进程 | 运行日志 |
| `hooks.log` | 脚本 | 异常日志 |

状态写入使用“临时文件 + `os.replace`”原子替换。status 与 mode 分文件，避免并发覆盖。

### 5.3 权限复位

- 当前档位来源：mode 文件 → statusline（若未来提供 `permission_mode`）→ 配置的假设档位。
- 循环：`default → acceptEdits → plan → auto → default`（可配置插入 `bypassPermissions`）。
- 计算到 `default` 的前进次数，注入 `Shift+Tab` N 次，间隔 80ms。
- 写入一条 daemon 来源的 mode 覆盖，供下一次操作使用。
- PERM 单击附带 `F16`，守护进程据此把档位前进一格；hooks 触发时用真实档位校正。

### 5.4 模型循环

- 从 status 文件读取 `model.id` / `display_name`，按 `config.models` 匹配别名。
- 发送 `/model <下一个>` + Enter（Unicode SendInput）。
- 默认列表：`opus → sonnet → haiku`。
- 说明：`/model <alias>` 会同时保存为新会话默认模型。

### 5.5 安装

- 复制 `core.py`、`statusline.py`、`hook_state.py` 到 `~/.claude/claudepad/`。
- 备份 `~/.claude/settings.json`。
- 在 `PermissionRequest`、`UserPromptSubmit`、`Stop`、`SessionStart` 注册 `hook_state.py`（只写状态，不做决策）。
- 设置 `statusLine` 为 `python "<dest>/statusline.py"`。
- 可选 `--autostart` 写入 Startup 的 `.vbs`。
- `uninstall` 移除本项目的 hook/statusLine，并恢复之前的 statusLine。
- 升级安装时清理旧的 `hook_permission.py` 和对应 hook 条目。

### 5.6 已知限制

- 注入按键发送到当前前台窗口；触发复位/切模型时需保持 Claude Code 终端聚焦。
- 多会话时使用“最近更新的会话”。
- 手动 Shift+Tab 改档位后，mode 文件会短暂过期；hooks 会尽快刷新。
- 若 `bypassPermissions` 出现在实际循环中，需要在 `config.json` 的 `permission_cycle` 里同步。
- 无物理电源开关；深度睡眠期间电池仍有极小待机电流，长期存放拔 JST。

## 6. 验证

- 固件：GitHub Actions 编译通过；本机做 devicetree/符号静态检查。
- 上位机：`python -m unittest discover -s host/tests -v`。
- 安装器：临时 settings.json 验证合并、幂等、卸载恢复、旧 hook 清理。
- PCB：KiCad DRC 0 violations / 0 unconnected；Gerber/钻孔/位置文件已导出。
- CAD：`python tools/check_cad.py` 校验 STL 尺寸与闭合；键位坐标与 PCB 一致。
- 手动：按键行为、复位、模型循环、深度睡眠唤醒、USB-C/电池（需真实硬件/终端）。

## 7. 交付物

- ZMK 工程 + GitHub Actions。
- 4 层 KiCad PCB + Gerber/钻孔/位置文件 + DRC 报告。
- 3D 打印底座/定位板/键帽 SCAD + STL + 校准试件。
- Windows 上位机 + 安装器 + hooks。
- BOM、PCB 文档、CAD 文档、键位文档、预览图。
- 设计规格与实施计划。

# ClaudePad 键位与固件说明

固件文件：

- `config/boards/shields/claudepad/claudepad.overlay`：矩阵、引脚、物理布局
- `config/boards/shields/claudepad/claudepad.keymap`：行为、宏、键位
- `config/boards/shields/claudepad/claudepad.conf`：ZMK 选项

主控为 **Seeed XIAO nRF52840**（ZMK 板名 `xiao_ble//zmk`），矩阵行用 D0/D1/D2，列用 D6–D10。无审批拨杆、无电源开关。
硬件：[PCB 制造与焊接](pcb.md)｜[外壳/定位板/键帽](cad.md)。

## 1. 物理布局

```
PERM   MODEL   CMD    ↑    VOICE
STOP   (空)           ←    ↓    →
ENTER (2u)          SPACE (3u)
```

位置顺序（矩阵变换与 keymap 一一对应）：

| # | 键 | 行/列 |
|---|---|---|
| 0 | PERM | R0/C0 |
| 1 | MODEL | R0/C1 |
| 2 | CMD | R0/C2 |
| 3 | ↑ | R0/C3 |
| 4 | VOICE | R0/C4 |
| 5 | STOP | R1/C0 |
| 6 | ← | R1/C2 |
| 7 | ↓ | R1/C3 |
| 8 | → | R1/C4 |
| 9 | ENTER | R2/C0 |
| 10 | SPACE | R2/C2 |

`R1/C1` 是空位，不接开关。

## 2. 行为表

| 键 | 单击 | 双击 | 长按 |
|---|---|---|---|
| PERM | `Shift+Tab` + `F16` 同步信号 | — | 250ms → `Ctrl+Alt+Shift+F15` |
| MODEL | `/model` + Enter | — | 250ms → `Ctrl+Alt+Shift+F14` |
| CMD | `/` | — | 200ms → `@` |
| STOP | `Esc` | 200ms 内 → `Ctrl+C` | 1200ms → `Ctrl+C` ×2 |
| ENTER | `Enter` | 200ms 内 → `Shift+Enter` | — |
| SPACE | `Space` | — | 300ms → `Tab` |
| VOICE | `Space` | 180ms 内 → `/voice` | 按住 → `Space` |
| ← ↑ ↓ → | 方向键 | — | 系统自动重复 |

## 3. 实现方式

全部用 ZMK 原生行为，没有自定义 C 代码。

### PERM / MODEL / CMD

- `hold-tap`，`flavor = "tap-preferred"`。
- 第一个参数是长按行为，第二个是单击行为。
- PERM：`&perm_ht LC(LA(LS(F15))) 0`；单击由 `mac_perm_cycle` 输出 `Shift+Tab`，再发一个 `F16` 给上位机同步档位。
- MODEL：`&model_ht LC(LA(LS(F14))) 0`（`0` 是给宏的占位参数）
- CMD：`&cmd_ht AT_SIGN SLASH`

### STOP（单击 / 双击 / 长按）

外层 `tap-dance`（200ms）：

```
tap-dance:
  bindings = <&stop_ht 0 ESC>, <&kp LC(C)>
```

- 第一次单击 → 200ms 后选中第一个 binding。
- 第二次在 200ms 内按下 → 直接发 `Ctrl+C`。
- 内层 `hold-tap` 的 `tapping-term-ms = 1000`，加上外层 200ms = **1200ms** 长按，触发 `Ctrl+C` ×2 宏。

### ENTER

`tap-dance`（200ms）：

```
bindings = <&kp ENTER>, <&kp LS(ENTER)>
```

### SPACE（三重防误触）

```
tapping-term-ms = 300
quick-tap-ms = 150
require-prior-idle-ms = 120
flavor = "tap-preferred"
```

- 按住 300ms 才变 Tab。
- 150ms 内连按强制判单击。
- 在其他键后 120ms 内按空格，禁用长按。

### VOICE

外层 `tap-dance`（180ms）：

```
bindings = <&voice_ht SPACE SPACE>, <&mac_voice>
```

- 单击 / 按住 → 内层 hold-tap 输出 `Space`；按住约 230ms 后保持按下（push-to-talk）。
- 180ms 内双击 → `/voice` 宏。

### 宏

- `mac_perm_cycle`：`Shift+Tab`，随后 `F16` 同步信号。
- `mac_model`：`/model` + Enter，`wait-ms=15`，`tap-ms=10`。
- `mac_voice`：`/voice` + Enter。
- `mac_stop_exit`：`Ctrl+C`、等待 60ms、再 `Ctrl+C`。
- 所有长按宏都是“按下即输出”，不会让系统自动重复字符。

## 4. 信号键契约

| 信号 | 键码 | 上位机动作 |
|---|---|---|
| 档位同步 | `F16`（PERM 单击附带） | 上位机把当前档位前进一格 |
| 权限复位 | `Ctrl+Alt+Shift+F15` | 读当前档位 → 按 N 次 `Shift+Tab` 回 default |
| 模型循环 | `Ctrl+Alt+Shift+F14` | 读当前模型 → `/model <下一个>` + Enter |

> 审批拨杆和自动批准已取消，因此不再使用 `F13`。Claude Code 的权限提示由人工回答。

为什么需要 F16：Claude Code 的 statusLine JSON 目前不提供 `permission_mode`（官方 issue #52083 / #54032 仍在请求），上位机无法直接读取当前档位。PERM 单击在 `Shift+Tab` 之后补一个 `F16`，上位机据此把状态向前推一格；其他 hooks 也会在触发时用真实档位校正。

## 5. 电源与睡眠

- 没有物理电源开关。
- `claudepad.conf` 已开启 `CONFIG_ZMK_SLEEP=y`：闲置一段时间后进入深度睡眠，按任意键唤醒并重连蓝牙。
- 硬关机/长期存放：拔掉 JST 电池插头。
- XIAO 自带 BQ25101 充电，USB-C 插入即可充电，电流较小。

## 6. 修改时间参数

所有时间都在 `claudepad.keymap` 中：

- PERM / MODEL 长按：`perm_ht` / `model_ht` 的 `tapping-term-ms`。
- CMD 长按：`cmd_ht` 的 `tapping-term-ms`。
- 空格防误触：`space_ht` 的 `tapping-term-ms` / `quick-tap-ms` / `require-prior-idle-ms`。
- STOP 双击窗口：`stop_td` 的 `tapping-term-ms`。
- STOP 长按：`stop_td` + `stop_ht` 的 tapping-term 之和（默认 200 + 1000 = 1200ms）。
- ENTER 双击窗口：`enter_td` 的 `tapping-term-ms`。
- VOICE 双击窗口 / 对讲延迟：`voice_td` + `voice_ht` 的 tapping-term。

改完运行：

```bash
python tools/check_firmware.py
```

再重新编译固件。

## 7. 编译与刷机

- GitHub Actions：推送仓库后自动构建 `claudepad-xiao_ble-zmk.uf2`（以 Actions 产物名为准）。
- 主控：Seeed XIAO nRF52840，ZMK 板名 `xiao_ble//zmk`。
- 刷机：双击 XIAO 上 USB-C 旁的 RESET 键进入 bootloader，拖入 uf2；首次蓝牙配对名称 `ClaudePad`。
- 本地编译需要 west + Zephyr SDK，参考 ZMK 文档。

## 8. 注意

- 固件只负责发键码；权限复位和模型循环由 Windows 上位机完成。
- 上位机不再返回 allow/deny，审批完全手动。
- 若实际权限循环包含 `bypassPermissions`，请同步修改上位机 `config.json` 的 `permission_cycle`。

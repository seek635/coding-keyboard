# ClaudePad 固件（ZMK）

三行五列 11 键 + 侧边审批拨杆的 ZMK shield 配置。

**主控**：nice!nano v2（nRF52840，Pro Micro 引脚兼容）
**固件框架**：[ZMK](https://zmk.dev)（BLE 键盘事实标准）

---

## 目录结构

```
firmware/
├── build.yaml                                  ← GitHub Actions 构建配置
├── config/
│   └── west.yml                                ← ZMK 上游依赖（版本锁定）
├── zephyr/
│   └── module.yml                              ← 模块定义
└── boards/shields/claudepad/
    ├── Kconfig.shield                          ← shield 标识
    ├── Kconfig.defconfig                       ← 设备名等默认配置
    ├── claudepad.overlay                       ← 矩阵 + 引脚 + 变换
    ├── claudepad.keymap                        ← ★ 键位与手势（核心）
    ├── claudepad.conf                          ← 配置建议
    └── claudepad.zmk.yml                       ← 硬件元数据
```

---

## 键位与手势总表

| 键位 | 单击 | 双击 | 长按 |
|---|---|---|---|
| **访问等级** | `Shift+Tab` 循环权限档位 | — | 复位到 default（发信号给上位机） |
| **↑ ↓ ← →** | 对应方向键 | — | 自动重复（系统原生） |
| **模型** | `/model` + Enter | — | 循环切换模型（发信号给上位机） |
| **命令行** | `/` | — | `@` 文件引用 |
| **停止** | `Esc` 中断生成 | `Ctrl+C` 强制取消 | `Ctrl+C` ×2 退出会话 |
| **回车** | `Enter` 发送 | `Shift+Enter` 换行 | — |
| **空格** | `Space` | — | `Tab` 自动补全 |
| **语音** | 按住 = `Space`（push-to-talk） | `/voice` 切换启用 | — |
| **审批拨杆** | 拨到 ON = 持续按下 `F13`；OFF = 释放 | — | — |

> 「发信号给上位机」= 发送 `Ctrl+Alt+Shift+F13` / `F14` 这类极难误触的组合键。
> 因为键盘**无法知道**当前权限档位或模型名，这两个操作必须由读取状态栏的上位机执行。
> 详见 `docs/固件设计说明.md`。

---

## 矩阵接线

电气上是 **3 行 × 6 列**，实际用到 12 个交点：

```
        列1    列2    列3    列4    列5    列6
       (D7)   (D8)   (D9)   (D10)  (D16)  (D14)
行1(D4) 访问    ↑     模型   命令行  停止   审批拨杆
行2(D5)  ←      ↓      →     回车     —      —
行3(D6) 空格    —      —      —     语音     —
```

**大键并联接法**（重要）：
- **回车 2u**：定位板开 2 个轴孔，两个轴体都接到 `(行2, 列4)`
- **空格 4u**：定位板开 3 个轴孔，三个轴体都接到 `(行3, 列1)`

即大键的多个轴体**电气上并联**，任一轴触发即响应。PCB 设计时要把这些焊盘接到同一条线。

> ⚠️ **引脚分配必须与实际 PCB 一致。** 上面是一套建议分配；
> 本项目 CAD 只定义了外壳和定位板，**PCB 尚未设计**。打板后如需调整，改
> `claudepad.overlay` 里的 `row-gpios` / `col-gpios` 即可，键位不用动。

---

## 怎么编译

### 方式一：GitHub Actions（推荐，零环境）

1. 把这个 `firmware/` 目录推到一个 GitHub 仓库
2. Actions 会自动构建（配置见 `build.yaml`）
3. 构建完成后在 Actions 的 Artifacts 里下载 `claudepad.uf2`

### 方式二：本地构建

需要 Zephyr SDK + west。步骤：

```bash
# 1. 初始化 workspace
west init -l firmware/config
cd firmware
west update

# 2. 构建
west build -p -b nice_nano_v2 -s zmk/app -- \
    -DSHIELD=claudepad \
    -DZMK_CONFIG="$(pwd)/config"

# 3. 产物
#   build/zephyr/zmk.uf2
```

> Windows 上本地构建环境配置较繁琐，**建议直接用 GitHub Actions**。

---

## 怎么刷固件

1. nice!nano 插 USB（**必须是数据线**）
2. **双击板上的复位按钮** → 出现名为 `NICENANO` 的 U 盘
3. 把 `claudepad.uf2` 拖进去
4. 板子自动重启，蓝牙广播名为 `ClaudePad`

之后改键位只需重新编译刷入，无需重新配对。

---

## 怎么改键位

**只改 `claudepad.keymap` 一个文件。**

改完**务必**跑一致性校验：

```bash
python tools/check_keymap.py
```

它会验证：
- 键位数量与 CAD 布局（`cad/lib/params.scad`）是否一致
- 每个键的顺序和功能是否与 PRD 相符
- 自定义行为的参数个数是否匹配

**改键位时注意**：`bindings` 的顺序必须与 `claudepad.overlay` 里 `default_transform` 的 `map` 顺序严格一致（都是从左到右、从上到下）。

---

## 常用调参

手感类参数都在 `claudepad.keymap` 的行为定义里：

| 想调什么 | 改哪个属性 | 当前值 |
|---|---|---|
| 空格误触 Tab | `spc_tab` 的 `tapping-term-ms` | 300（调大更不易误触） |
| 停止键误退会话 | `stop` 的 `tapping-term-ms` | 1200（调大更安全） |
| 双击判定窗口 | 各 tap-dance 的 `tapping-term-ms` | 200~250 |
| 快速连按不判长按 | `quick-tap-ms` | 150~200 |
| 打字时禁用长按 | `require-prior-idle-ms` | 120 |

---

## 已知限制

| 限制 | 说明 |
|---|---|
| **状态指示未实现** | PRD 第 8 章要求「按键 RGB 显示当前权限档位」，这需要自定义固件 + 上位机通过 GATT 回写状态。当前固件只做键位。 |
| **审批拨杆只上报状态** | 拨杆作为矩阵里的一个键（F13），上位机需自行监听。真正的自动审批逻辑在上位机侧。 |
| **引脚分配待 PCB 定稿** | 见上文。 |

详见 `docs/固件设计说明.md` 的「后续工作」。

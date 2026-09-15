# ClaudePad CAD 模型

3D 打印用的参数化结构模型。**改尺寸只需改一个文件**：`lib/params.scad`

整机 **107.10 × 71.10 × 20.10 mm**

---

## 依赖：大部分脚本不需要 OpenSCAD

这是刻意设计的。OpenSCAD 是整套工具链里最难装的东西（200MB、官方站和 GitHub 都常被拦），
所以**校验逻辑全部用纯 Python 实现**，不依赖它。

| 脚本 | 依赖 | 作用 |
|---|---|---|
| `view_model.py` | 纯 Python | **在浏览器里看三维模型** |
| `lint_scad.py` | 纯 Python | SCAD 语法与符号检查 |
| `check_dims.py` | 纯 Python | 26 项结构设计规则 |
| `verify_geometry.py` | 纯 Python | 孔位/对位验证 |
| `check_keymap.py` | 纯 Python | 固件 ↔ 结构一致性 |
| `verify_stl.py` | 纯 Python | STL 校验（读文件，不需要 CAD 软件） |
| `gen_pcb.py` | 纯 Python | PCB 网表与接线图 |
| `gen_viewer.py` | 纯 Python | **把尺寸注入三维查看器**（防漂移） |
| `draw_travel.py` | 纯 Python | 按键行程剖面图 |
| **`export_stl.py`** | **★ OpenSCAD** | **把 .scad 渲染成可打印的 STL** |

**实际含义**：

- **只装 Python** → 你能**看模型**、改所有尺寸、验证设计是否自洽、检查固件对不对。
  **完全够用来迭代设计。**
- **装了 OpenSCAD** → 才能把模型变成可以送切片软件的 STL。

不确定自己缺什么？跑这个：

```bash
python tools/check_env.py
```

它会逐项告诉你什么已就绪、什么缺失、缺的那个影响哪些功能。

> **本机现状**：OpenSCAD 已装在 `~/openscad-portable/`，6 个 STL 也已生成。
> 所以你现在直接跑任何脚本都可以。

---

## 怎么看到三维模型

**一条命令**：

```bash
python tools/view_model.py
```

会自动起本地服务并打开浏览器，里面是可旋转、可缩放、可爆炸拆解的实时三维模型。

**不需要 OpenSCAD，不需要任何 CAD 软件**——查看器读的是已经渲染好的 STL，
用浏览器的 WebGL 显示。

其它看模型的方式（都不需要软件）：

| 方式 | 位置 |
|---|---|
| 交互式三维查看器 | `python tools/view_model.py` |
| 渲染好的图片 | `cad/output/preview/*.png` |
| 丢进任意 STL 查看器 | `cad/output/*.stl` |
| 丢进切片软件（Cura / PrusaSlicer） | `cad/output/*.stl` |

**什么时候才需要 OpenSCAD**：改了 `params.scad` 里的尺寸，想看到新模型时。
因为 `.scad` 是模型源码，需要 OpenSCAD 求值才能变成几何体。

---

## 目录结构

```
cad/
├── lib/
│   └── params.scad          ← 所有尺寸都在这里，改这个
├── test_coupon.scad         ← ★ 校准试件（先打这个！）
├── plate.scad               ← 定位板（轴板）
├── case_bottom.scad         ← 底座
├── keycap.scad              ← 键帽（1u / 2u / 4u）
├── assembly.scad            ← 总装预览 + 爆炸图
└── output/                  ← 导出的 STL 放这里

tools/
├── check_env.py             ← 环境自检（先跑这个）
├── view_model.py            ← ★ 在浏览器里看三维模型（不需要 CAD）
├── check_dims.py            ← 设计规则校验（26 项）
├── lint_scad.py             ← 语法与符号检查
├── verify_geometry.py       ← 孔位与对位验证
├── verify_stl.py            ← STL 校验（尺寸/水密性/体积）
├── scad_params.py           ← 参数解析器（上面脚本共用）
├── canvas.py                ← 2D 画布（SVG + PNG 双后端，画图脚本共用）
├── gen_pcb.py               ← 生成 PCB 网表与接线图
├── gen_viewer.py            ← 把尺寸注入三维查看器（防漂移）
├── draw_travel.py           ← 生成按键行程剖面图
├── install_openscad.py      ← 自动下载安装 OpenSCAD（多镜像+断点续传）
└── export_stl.py            ← 一键导出全部 STL（★ 唯一需要 OpenSCAD 的）

docs/
└── 结构设计规格书.md          ← 尺寸 / 公差 / 装配 / 走线的完整说明
```

---

## 四步走

### 第 1 步：核参数（不需要装任何东西）

```bash
python tools/check_dims.py       # 16 项设计规则
python tools/lint_scad.py        # 语法、符号、死代码
python tools/verify_geometry.py  # 孔位、对称性、键帽对位
```

这三个脚本**不依赖 OpenSCAD**，纯 Python，随时可跑。

它们**直接从 `params.scad` 读参数**，所以不存在"改了参数但校验还用旧值"的问题。

**最有价值的是 `check_dims.py`** —— 它会抓出这些真实会翻车的问题：

- 内腔高度和零件堆叠对不上（会导致轴体够不到 PCB）
- 螺丝柱撞穿轴孔
- 拨杆螺母没有咬合长度
- 轴芯太长捅穿键帽顶面
- 主控放不进 PCB 与定位板之间
- 电池厚度超过可用空间
- 空格单轴支撑挠度超标

### 第 2 步：装 OpenSCAD

**方式一：自动安装（推荐）**

```bash
python tools/install_openscad.py
```

脚本会自动尝试多个 GitHub 加速镜像、支持断点续传，最后解压到 `~/openscad-portable/`。

**方式二：手动下载**

下载：https://openscad.org/downloads.html

装完确认能调到：

```bash
openscad --version
```

> **为什么需要专门的安装脚本**：`openscad.org` 官方站和 GitHub Release 的
> `objects.githubusercontent.com` 在部分网络环境会被拦，直连速度可能只有 20KB/s。
> 本脚本按顺序试 `ghproxy.net` / `gh-proxy.com` / `gitmirror` 等镜像，断流自动续传。
>
> Windows 上优先用 `openscad.com`（控制台版），它不会弹 GUI 窗口。

### 第 3 步：导出 STL

```bash
python tools/export_stl.py
```

| 文件 | 零件 | 材料 |
|---|---|---|
| `00_test_coupon.stl` | **校准试件** | PLA |
| `01_case_bottom.stl` | 底座 | PETG |
| `02_plate.stl` | 定位板 | PLA |
| `03_keycap_1u.stl` | 键帽（打 9 个） | PLA |
| `04_keycap_2u.stl` | 回车键帽 | PLA |
| `05_keycap_4u.stl` | 空格键帽 | PLA |

**导出后务必校验**：

```bash
python tools/verify_stl.py
```

它会检查每个 STL 的包围盒尺寸是否与设计一致、是否水密（无破面）、体积是否正常。
这一步能抓出 CSG 建模中的共面/非流形问题。

### 第 4 步：打印

**别一次打全套。** 按这个顺序：

| 顺序 | 打什么 | 验证 | 耗时 |
|---|---|---|---|
| ① | `00_test_coupon.stl` | **轴体卡扣间隙** | 15 min |
| ② | `02_plate.stl` | 轴孔松紧 | 40 min |
| ③ | `05_keycap_4u.stl` | 三轴支撑手感 | 35 min |
| ④ | `01_case_bottom.stl` | 孔位与装配 | 3–4 h |

---

## 预览图

渲染预览（OpenSCAD 已装好后可自己重跑）：

```bash
cd cad
OSC=~/openscad-portable/openscad-2021.01/openscad.com
"$OSC" -D 'VIEW="assembly"' --autocenter --viewall --imgsize=1000,700 \
       -o output/preview/assembly.png assembly.scad
```

`cad/output/preview/` 下已有：

| 文件 | 内容 |
|---|---|
| `assembly.png` | 整机总装（等轴测） |
| `explode.png` | **三层爆炸图**（底座 / 定位板 / 键帽） |
| `top_view.png` | 正俯视 —— 用于核对键位排布 |
| `case_iso.png` | 底座内部结构 |
| `side_90.png` | 右壁正视图（拨杆孔 + USB 开口） |
| `plate.png` | 定位板 |
| `keycap4u_bottom.png` | 4u 空格底面 —— 可见 3 个榫头柱与 3 条加强筋 |

---

## 校准试件怎么用（重要）

`SWITCH_PLATE_GAP`（PCB 到定位板的距离）是**整套模型里唯一无法从公开资料确定**的尺寸。Choc 官方没公开，社区实测在 3.5–6.0mm 之间浮动。

所以先打 `00_test_coupon.stl`，上面有 3 个测试位（间隙 3.50 / 4.25 / 5.00mm）：

1. 拿真实 Choc 轴体逐个插进去
2. 找那个「**卡扣清脆扣入 + 轴体底面刚好贴住基座**」的位置
3. 把 `params.scad` 里的 `SWITCH_PLATE_GAP` 改成该值
4. 重跑 `check_dims.py`、`gen_viewer.py` 和 `export_stl.py`

判读标准：

| 现象 | 结论 |
|---|---|
| 轴体底面与基座之间有缝 | 该位间隙**偏大** |
| 卡扣扣不上 / 扣上后底面顶住基座 | 该位间隙**偏小** |
| 完全贴合 + 卡扣清脆 | ✅ 就是它 |

三个都不合适 → 改 `test_coupon.scad` 里的 `GAPS` 数组，重打（15 分钟）。

---

## 在 OpenSCAD 里预览

```bash
openscad assembly.scad
```

`F5` 快速预览，`F6` 完全渲染。改文件里的 `VIEW` 变量：

| VIEW | 效果 |
|---|---|
| `"explode"` | 爆炸图（默认）—— 检查装配关系与干涉 |
| `"assembly"` | 合体图 |
| `"case"` | 只看底座 |
| `"plate"` | 只看定位板 |
| `"caps"` | 只看键帽 |

单独看键帽：

```bash
openscad keycap.scad
```

改文件里的 `keycap_mode` 为 `"1u"` / `"2u"` / `"4u"`。

---

## 最常改的参数

都在 `lib/params.scad`：

| 想做什么 | 改哪个 | 当前值 |
|---|---|---|
| **轴体卡扣位置**（最重要） | `SWITCH_PLATE_GAP` | `5.00` |
| 轴体装不进 / 太松 | `SWITCH_CUTOUT_TOL` | `0.10` |
| 键帽榫槽太紧 / 太松 | `CAP_STEM_GAP` | `0.95` |
| 键距 | `PITCH` | `18.0` |
| 键盘更薄 | `PCB_STANDOFF_H` | `5.00` |
| 换拨杆开关 | `SW_*` 系列 | 见文件 |
| 换电池 | `BATT_*` + `PCB_STANDOFF_H` | 见文件 |

**改完必跑**：

```bash
python tools/check_dims.py && python tools/lint_scad.py && python tools/verify_geometry.py
```

---

## 设计要点

### 垂直尺寸是推导出来的，不是写死的

```
内腔净高 = PCB_STANDOFF_H + PCB_T + SWITCH_PLATE_GAP
         = 5.0 + 1.6 + 5.0
         = 11.6 mm
```

改任何一个零件，整机高度自动跟着变。这样就不会出现"定位板抬高 4mm 导致轴体够不到 PCB"这类致命错误。

### 一个必须知道的耦合

**「PCB 到定位板的间隙」同时决定轴体卡扣位置和主控可用高度** —— 主控就装在这 5.0mm 里。

所以这个值不能随意调小：小于 3.7mm 主控就放不下。`check_dims.py` 会校验这一点。

### 空格为什么要 3 个轴

按无加强筋的最坏情况估算：

| 支撑方式 | 中点挠度（3N 按压力） |
|---|---|
| 单轴 | 1.59 mm ← 明显翘 |
| 三轴并联 | 0.20 mm ← 可接受 |

降幅约 87%。所以定位板在空格位开 3 个轴孔，键帽内对应 3 个榫槽。

### 螺丝柱为什么只能在边距里

轴孔之间净距只有 `18 − 13.9 = 4.1mm`，放不下螺丝柱。所以螺丝柱放在网格外缘到定位板边缘的 6mm 边距里，`check_dims.py` 会校验它与轴孔有 ≥0.8mm 余量。

---

## 关于 STL 文件

本仓库**不含预生成的 STL**，原因有二：

1. STL 是二进制大文件，参数一改就作废，不如源码干净
2. 你的打印机公差、材料、喷嘴直径都可能不同，**应该由你在本地导出**

导出是一次性的：装好 OpenSCAD 后跑 `python tools/export_stl.py`，几秒钟的事。

---

## 完整设计依据

尺寸从哪来、公差为什么是这个数、装配顺序、走线怎么走 —— 全在 **`docs/结构设计规格书.md`**。

那里也有「常见问题与对策」，遇到装不进、太松、翘曲先查那里。

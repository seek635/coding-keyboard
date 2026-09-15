#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClaudePad 环境自检
================================================================================
检查运行本项目各脚本所需的东西是否齐全，缺什么就告诉你装什么。

设计原则：**大部分脚本不依赖 OpenSCAD**。
  · 5 个校验脚本是纯 Python，没有 OpenSCAD 也能跑（改参数后先跑它们）
  · 只有 export_stl.py 需要 OpenSCAD（把 .scad 渲染成 STL）
  · 所以「没装 CAD」不影响你改尺寸和验证设计，只影响导出 STL

运行：python tools/check_env.py
"""

import importlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

OK, MISS, WARN = "✅", "❌", "⚠️"
rows = []


def add(status, name, detail, fix=""):
    rows.append((status, name, detail, fix))


# ============================== 1. Python ==================================
v = sys.version_info
if v >= (3, 8):
    add(OK, "Python", f"{v.major}.{v.minor}.{v.micro}")
else:
    add(MISS, "Python", f"{v.major}.{v.minor}（需要 ≥3.8）",
        "升级 Python：https://www.python.org/downloads/")

# ============================== 2. 项目文件 ================================
need_files = [
    ("cad/lib/params.scad", "参数表（所有尺寸的唯一来源）"),
    ("cad/plate.scad", "定位板模型"),
    ("cad/case_bottom.scad", "底座模型"),
    ("cad/keycap.scad", "键帽模型"),
    ("cad/test_coupon.scad", "校准试件"),
    ("firmware/boards/shields/claudepad/claudepad.keymap", "固件键位"),
    ("firmware/boards/shields/claudepad/claudepad.overlay", "固件矩阵"),
]
missing = [p for p, _ in need_files if not os.path.exists(os.path.join(ROOT, p))]
if not missing:
    add(OK, "项目文件", f"{len(need_files)} 个关键文件齐全")
else:
    add(MISS, "项目文件", f"缺少 {len(missing)} 个：{', '.join(missing[:3])}…",
        "确认你在项目根目录下运行本脚本")

# ============================== 3. OpenSCAD =================================
osc = None
try:
    from export_stl import find_openscad
    osc = find_openscad()
except Exception:
    pass

if osc and os.path.exists(osc):
    try:
        r = subprocess.run([osc, "--version"], capture_output=True, text=True, timeout=20)
        ver = (r.stdout or r.stderr).strip().split("\n")[0]
    except Exception:
        ver = "已找到但无法执行"
    add(OK, "OpenSCAD", ver)
else:
    add(WARN, "OpenSCAD", "未安装",
        "只影响「导出 STL」。校验脚本不需要它。\n"
        "     自动安装：python tools/install_openscad.py")

# ============================== 4. STL 产物 =================================
stl_dir = os.path.join(ROOT, "cad", "output")
stls = [f for f in os.listdir(stl_dir) if f.endswith(".stl")] if os.path.isdir(stl_dir) else []
if len(stls) >= 6:
    add(OK, "STL 文件", f"{len(stls)} 个已生成")
elif stls:
    add(WARN, "STL 文件", f"只有 {len(stls)} 个（应 6 个）",
        "重跑：python tools/export_stl.py")
else:
    add(WARN, "STL 文件", "未生成",
        "需要 OpenSCAD，然后：python tools/export_stl.py")

# ============================== 5. 可选第三方包 =============================
VENV_PY = os.path.join(os.path.expanduser("~"), ".workbuddy-ai", "binaries",
                       "python", "envs", "default", "Scripts", "python.exe")


def has_pkg_in(py, mod):
    """在指定解释器里检查某个包是否存在"""
    if not py or not os.path.exists(py):
        return False
    try:
        r = subprocess.run([py, "-c", f"import {mod}"],
                           capture_output=True, timeout=20)
        return r.returncode == 0
    except Exception:
        return False


pkgs = [
    ("PIL", "Pillow", "生成接线图 PNG（gen_pcb.py）"),
    ("pynput", "pynput", "键盘拨杆监听（claudepad_daemon.py）"),
]
pkg_ok = {}
for mod, pkg, why in pkgs:
    here = False
    try:
        importlib.import_module(mod)
        here = True
    except ImportError:
        pass
    if here:
        add(OK, f"Python 包 {pkg}", f"已安装 · 用于{why}")
        pkg_ok[pkg] = True
    elif has_pkg_in(VENV_PY, mod):
        add(OK, f"Python 包 {pkg}", f"装在独立 venv 里 · 用于{why}",
            f"要用 venv 的解释器跑：{VENV_PY}")
        pkg_ok[pkg] = True
    else:
        add(WARN, f"Python 包 {pkg}", f"未安装 · 影响{why}",
            f"pip install {pkg}\n"
            f"     若 PyPI 被拦，用国内镜像：\n"
            f"     pip install -i https://pypi.tuna.tsinghua.edu.cn/simple {pkg}")
        pkg_ok[pkg] = False

# ============================== 6. 脚本可运行性 =============================
SCRIPTS = [
    ("tools/check_env.py", "环境自检（本脚本）", False),
    ("tools/view_model.py", "浏览器里看三维模型", False),
    ("tools/lint_scad.py", "SCAD 语法与符号检查", False),
    ("tools/check_dims.py", "结构设计规则校验", False),
    ("tools/verify_geometry.py", "孔位与对位验证", False),
    ("tools/check_keymap.py", "固件 ↔ 结构一致性", False),
    ("tools/verify_stl.py", "STL 校验", False),
    ("tools/export_stl.py", "导出 STL", True),
    ("tools/gen_pcb.py", "生成 PCB 网表与接线图", False),
    ("tools/gen_viewer.py", "把尺寸注入三维查看器", False),
    ("tools/draw_travel.py", "生成按键行程剖面图", False),
    ("host/test_hook.py", "审批拨杆逻辑测试", False),
]


def main():
    print("=" * 76)
    print("ClaudePad 环境自检")
    print("=" * 76)
    print(f"项目目录：{ROOT}")
    print()

    for status, name, detail, fix in rows:
        print(f"{status} {name:<20} {detail}")
        if fix:
            print(f"     └ {fix}")

    print()
    print("-" * 76)
    print("脚本依赖一览（★ = 需要 OpenSCAD）")
    print("-" * 76)
    print(f"{'脚本':<28}{'作用':<26}{'依赖'}")
    print("-" * 76)
    for path, desc, need_osc in SCRIPTS:
        dep = "★ OpenSCAD" if need_osc else "纯 Python"
        exists = os.path.exists(os.path.join(ROOT, path))
        mark = "" if exists else "  （文件缺失）"
        print(f"{path:<28}{desc:<26}{dep}{mark}")

    print()
    print("-" * 76)
    has_osc = bool(osc and os.path.exists(osc))
    core_ok = not missing and not [r for r in rows if r[0] == MISS]
    opt_missing = [k for k, v in pkg_ok.items() if not v]
    has_stl = len(stls) >= 6

    if core_ok and has_osc and not opt_missing:
        print("✅ 环境完整，所有脚本都能跑。")
    else:
        if not has_osc and has_stl:
            print("ℹ️  没装 OpenSCAD —— 但**不影响看模型和改尺寸**。")
            print()
            print("   你现在就能做的（不需要 OpenSCAD）：")
            print("     python tools/view_model.py        # 在浏览器里看三维模型")
            print("     python tools/check_dims.py        # 改完参数先跑这个")
            print("     python tools/verify_geometry.py")
            print("     python tools/check_keymap.py")
            print()
            print("   只有「改了尺寸后重新生成 STL」才需要 OpenSCAD：")
            print("     python tools/install_openscad.py  # 自动安装（多镜像+断点续传）")
            print("     python tools/export_stl.py")
        elif not has_osc and not has_stl:
            print("⚠️  缺 OpenSCAD 且 STL 还没生成。")
            print("   → python tools/install_openscad.py   然后   python tools/export_stl.py")
        if opt_missing:
            print(f"ℹ️  可选包未装：{', '.join(opt_missing)}")
            print("   只影响对应脚本（PNG 预览 / 键盘监听），核心功能不受影响。")
        if core_ok and has_osc and opt_missing:
            print()
            print("✅ 核心功能完整。")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())

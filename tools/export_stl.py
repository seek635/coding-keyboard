# -*- coding: utf-8 -*-
"""
ClaudePad STL 导出脚本
------------------------
自动在以下位置寻找 OpenSCAD 可执行文件：
  1. 系统 PATH
  2. 便携版目录 %USERPROFILE%\\openscad-portable\\OpenSCAD\\openscad.exe
  3. 标准安装目录 C:\\Program Files\\OpenSCAD\\openscad.exe

运行：python tools/export_stl.py
产出：cad/output/*.stl
"""

import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad")
OUT = os.path.join(CAD, "output")

HOME = os.path.expanduser("~")


def find_openscad():
    """按优先级查找 openscad 可执行文件

    Windows 上优先用 openscad.com（控制台版），它不会弹 GUI 窗口；
    openscad.exe 是 GUI 版，命令行调用时也可能短暂弹窗。
    """
    # 1. 便携版目录（优先 console 版）
    for exe in ["openscad.com", "openscad.exe", "OpenSCAD.exe"]:
        hits = glob.glob(os.path.join(HOME, "openscad-portable", "**", exe),
                         recursive=True)
        if hits:
            return sorted(hits)[0]

    # 2. 系统 PATH
    for exe in ["openscad", "openscad.com", "openscad.exe"]:
        p = shutil.which(exe)
        if p:
            return p

    # 3. 标准安装位置
    for p in [r"C:\Program Files\OpenSCAD\openscad.com",
              r"C:\Program Files\OpenSCAD\openscad.exe",
              r"C:\Program Files (x86)\OpenSCAD\openscad.exe"]:
        if os.path.exists(p):
            return p

    return None


OPENSCAD = find_openscad()

# (源文件, 输出名, 额外 -D 参数)
JOBS = [
    ("test_coupon.scad", "00_test_coupon.stl", []),          # 先打这个！
    ("case_bottom.scad", "01_case_bottom.stl", []),
    ("plate.scad",       "02_plate.stl",       []),
    ("keycap.scad",      "03_keycap_1u.stl",   ["-D", 'keycap_mode="1u"']),
    ("keycap.scad",      "04_keycap_2u.stl",   ["-D", 'keycap_mode="2u"']),
    ("keycap.scad",      "05_keycap_4u.stl",   ["-D", 'keycap_mode="4u"']),
]


def main():
    if not OPENSCAD or not os.path.exists(OPENSCAD):
        print("❌ 未找到 OpenSCAD。")
        print("   请先安装： https://openscad.org/downloads.html")
        print("   或下载便携版解压到： ~/openscad-portable/")
        print("   也可在本脚本的 find_openscad() 里加自定义路径。")
        return 1

    print(f"使用 OpenSCAD：{OPENSCAD}")
    os.makedirs(OUT, exist_ok=True)
    fails = []
    for src, dst, extra in JOBS:
        src_path = os.path.join(CAD, src)
        dst_path = os.path.join(OUT, dst)
        cmd = [OPENSCAD, "-o", dst_path] + extra + [src_path]
        print(f"→ 渲染 {dst} ...")
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=CAD)
        if r.returncode != 0 or not os.path.exists(dst_path):
            msg = (r.stderr or r.stdout or "").strip()[:400]
            print(f"  ❌ 失败：{msg}")
            fails.append(dst)
        else:
            size = os.path.getsize(dst_path)
            print(f"  ✅ 完成（{size/1024:.1f} KB）")

    print()
    if fails:
        print(f"❌ {len(fails)} 个文件失败：{', '.join(fails)}")
        return 1
    print(f"✅ 全部完成，输出目录：{OUT}")
    print("   ⚠️ 打印前请先跑一遍 tools/check_dims.py 核对尺寸")
    return 0


if __name__ == "__main__":
    sys.exit(main())

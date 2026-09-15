# -*- coding: utf-8 -*-
"""
OpenSCAD 自动安装脚本（Windows / 便携版）
------------------------------------------
为什么需要这个脚本：
  · openscad.org 官方下载站在部分网络环境下会被拦（TLS 错误 0x80072f19）
  · GitHub Release 会跳转到 objects.githubusercontent.com，同样常被拦
  · 直连速度可能只有 20KB/s，中途断流，必须支持断点续传

本脚本按顺序尝试多个 GitHub 加速镜像，支持断点续传，最后自动解压。

运行：
    python tools/install_openscad.py

安装位置：~/openscad-portable/
完成后 tools/export_stl.py 会自动找到它。
"""

import os
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.request
import zipfile

HOME = os.path.expanduser("~")
DEST = os.path.join(HOME, "openscad-portable")
ZIP = os.path.join(DEST, "openscad.zip")

# OpenSCAD 2021.01 Windows 64 位便携版
ASSET = ("https://github.com/openscad/openscad/releases/download/"
         "openscad-2021.01/OpenSCAD-2021.01-x86-64.zip")

# 加速镜像前缀（按可用性排序，自动逐个尝试）
MIRRORS = [
    "",                                   # 直连
    "https://ghproxy.net/",
    "https://gh-proxy.com/",
    "https://hub.gitmirror.com/",
    "https://ghps.cc/",
]


def human(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def try_download(url, dest, expect_min=15 * 1024 * 1024):
    """支持断点续传；返回 True 表示文件已完整"""
    have = os.path.getsize(dest) if os.path.exists(dest) else 0
    req = urllib.request.Request(url)
    if have:
        req.add_header("Range", f"bytes={have}-")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            total = r.headers.get("Content-Length")
            total = int(total) + have if total else None
            mode = "ab" if have else "wb"
            done = have
            t0 = time.time()
            last = 0
            with open(dest, mode) as f:
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    now = time.time()
                    if now - last > 3:
                        last = now
                        spd = (done - have) / max(now - t0, 0.001)
                        pct = f"{done/total*100:.1f}%" if total else "?"
                        print(f"    {human(done)} / "
                              f"{human(total) if total else '?'}  "
                              f"({pct})  {human(spd)}/s", flush=True)
    except Exception as e:
        print(f"    ⚠️ 中断：{type(e).__name__}: {e}")
        return False

    size = os.path.getsize(dest)
    return size >= expect_min


def main():
    os.makedirs(DEST, exist_ok=True)

    if os.path.exists(ZIP):
        print(f"已存在部分下载：{human(os.path.getsize(ZIP))}，将尝试续传")

    for i, prefix in enumerate(MIRRORS):
        url = prefix + ASSET if prefix else ASSET
        name = prefix or "直连 GitHub"
        print(f"\n[{i+1}/{len(MIRRORS)}] 尝试 {name}")
        try:
            ok = try_download(url, ZIP)
        except KeyboardInterrupt:
            print("\n已取消。")
            return 1
        if ok:
            print(f"  ✅ 下载完成：{human(os.path.getsize(ZIP))}")
            break
        print(f"  ↻ {name} 未完成，换下一个镜像")
    else:
        print("\n❌ 所有镜像都失败。")
        print("   建议：挂代理后重跑，或手动下载后放到：")
        print(f"   {DEST}")
        print(f"   下载地址：{ASSET}")
        return 1

    # ---- 校验并解压 ----
    print("\n校验压缩包 ...")
    try:
        with zipfile.ZipFile(ZIP) as z:
            bad = z.testzip()
            if bad:
                raise ValueError(f"压缩包损坏：{bad}")
            names = z.namelist()
            print(f"  ✅ 压缩包完整，含 {len(names)} 个文件")
            print("解压中 ...")
            z.extractall(DEST)
    except Exception as e:
        print(f"  ❌ 校验/解压失败：{e}")
        print(f"   请删除 {ZIP} 后重跑本脚本")
        return 1

    # ---- 定位可执行文件 ----
    exe = None
    for root, _, files in os.walk(DEST):
        for fn in files:
            if fn.lower() == "openscad.exe":
                exe = os.path.join(root, fn)
                break
        if exe:
            break

    print()
    if exe:
        print("✅ 安装完成")
        print(f"   可执行文件：{exe}")
        print()
        print("   现在可以导出 STL 了：")
        print("     python tools/export_stl.py")
        print("     python tools/verify_stl.py")
    else:
        print("⚠️  解压完成，但没找到 openscad.exe")
        print(f"   请检查目录：{DEST}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

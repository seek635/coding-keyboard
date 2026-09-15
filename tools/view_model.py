#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一条命令查看 ClaudePad 三维模型
================================================================================
启动本地服务并打开浏览器里的交互式三维查看器。

**不需要 OpenSCAD，不需要任何 CAD 软件。**
查看器用的是已经渲染好的 STL 文件（`cad/output/*.stl`），
在浏览器里用 WebGL 实时显示，可以旋转、缩放、爆炸拆解。

如果 STL 还没生成，本脚本会提示你先跑 export_stl.py（那一步才需要 OpenSCAD）。

运行：
    python tools/view_model.py            # 自动选端口并打开浏览器
    python tools/view_model.py --port 9000
    python tools/view_model.py --no-open  # 只起服务，不自动开浏览器
"""

import argparse
import http.server
import os
import socket
import socketserver
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "cad", "output")
VIEWER = os.path.join(OUT, "viewer.html")

REQUIRED_STL = [
    "01_case_bottom.stl", "02_plate.stl",
    "03_keycap_1u.stl", "04_keycap_2u.stl", "05_keycap_4u.stl",
]


def free_port(start=8080, tries=40):
    """从 start 开始找一个能绑定的端口"""
    for p in range(start, start + tries):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    return None


def main():
    ap = argparse.ArgumentParser(description="查看 ClaudePad 三维模型")
    ap.add_argument("--port", type=int, default=None, help="指定端口（默认自动选）")
    ap.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args()

    print("=" * 68)
    print("ClaudePad 三维模型查看器")
    print("=" * 68)

    # ---- 前置检查 ----
    if not os.path.exists(VIEWER):
        print(f"❌ 找不到查看器页面：{VIEWER}")
        return 1

    missing = [f for f in REQUIRED_STL if not os.path.exists(os.path.join(OUT, f))]
    if missing:
        print(f"❌ 还缺 {len(missing)} 个 STL 文件：{', '.join(missing)}")
        print()
        print("   STL 需要 OpenSCAD 渲染生成。两种办法：")
        print("     1. 装 OpenSCAD 后跑：python tools/export_stl.py")
        print("     2. 自动安装 OpenSCAD：python tools/install_openscad.py")
        print()
        print("   ℹ️  但「看模型」还有更省事的办法——直接看已渲染好的图片：")
        pv = os.path.join(OUT, "preview")
        if os.path.isdir(pv):
            for f in sorted(os.listdir(pv)):
                if f.endswith(".png"):
                    print(f"        {os.path.join(pv, f)}")
        return 1

    n_stl = len([f for f in os.listdir(OUT) if f.endswith(".stl")])
    print(f"  ✅ 找到 {n_stl} 个 STL 模型文件")
    print(f"  ✅ 查看器页面就绪")

    # ---- 选端口 ----
    port = args.port or free_port()
    if not port:
        print("❌ 找不到可用端口，用 --port 手动指定")
        return 1

    # ---- 起服务 ----
    os.chdir(OUT)          # 让 STL 能被相对路径访问

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass           # 静音，不刷屏

    try:
        httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        print(f"❌ 端口 {port} 无法绑定：{e}")
        return 1

    url = f"http://127.0.0.1:{port}/viewer.html"
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    print()
    print(f"  🌐 地址：{url}")
    print()
    print("  操作：左键拖动旋转 · 滚轮缩放 · 右键平移")
    print("        右侧面板可开关零件、拖动爆炸拆解")
    print()
    print("  按 Ctrl+C 退出")
    print("=" * 68)

    if not args.no_open:
        try:
            webbrowser.open(url)
            print("  已尝试在浏览器中打开…")
        except Exception:
            print("  没能自动打开浏览器，请手动访问上面的地址")

    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        print("\n正在退出…")
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

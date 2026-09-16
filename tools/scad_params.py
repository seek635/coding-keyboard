# -*- coding: utf-8 -*-
"""
SCAD 参数解析器
---------------
从 cad/lib/params.scad 里读出数值参数，供其他校验脚本使用。

这样做的价值：参数只在一处定义（params.scad），Python 校验脚本不再
硬编码一份副本 —— 改参数后校验结果自动同步，杜绝「两边数值漂移」。

支持：数字、+ - * /、括号、max()、min()、以及引用已定义参数。
不支持（会跳过）：列表（如 KEYMAP）、字符串、带 $ 的内建变量。

用法：
    from scad_params import load
    P = load()
    print(P["CASE_INNER_H"])
"""

import os
import re
import math


def find_project_root(start=None):
    """从 start 向上逐级查找含 cad/lib/params.scad 的目录。

    这样脚本无论放在 <project>/tools/ 还是被复制到别处（如 skill 的 scripts/）
    都能正确定位项目。
    """
    p = os.path.abspath(start or os.path.dirname(os.path.abspath(__file__)))
    for _ in range(10):
        if os.path.exists(os.path.join(p, "cad", "lib", "params.scad")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return None


ROOT = find_project_root() or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAMS = os.path.join(ROOT, "cad", "lib", "params.scad")


def _strip_comments(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    return t


def load(path=PARAMS):
    """返回 {参数名: 数值或布尔}"""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"找不到参数文件：{path}\n"
            "  本脚本需要在一个含 cad/lib/params.scad 的项目里运行。\n"
            "  当前工作目录不在任何项目内时会出现此提示。"
        )
    text = _strip_comments(open(path, encoding="utf-8").read())

    # 收集所有形如  NAME = expr;  的赋值（单行）
    raw = {}
    for line in text.split("\n"):
        m = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*;\s*$", line)
        if not m:
            continue
        name, expr = m.group(1), m.group(2)
        if name.startswith("$"):
            continue
        if "[" in expr or "]" in expr:      # 列表，跳过
            continue
        if '"' in expr:                     # 字符串，跳过
            continue
        raw[name] = expr

    # 迭代求值直到收敛（解决定义顺序问题）
    env = {}
    safe = {
        "max": max, "min": min, "abs": abs,
        "floor": math.floor, "ceil": math.ceil,
        "sqrt": math.sqrt, "pow": pow, "round": round,
        # OpenSCAD 的布尔字面量（Python 里是 True/False）
        "true": True, "false": False,
    }

    for _ in range(len(raw) + 2):
        progress = False
        for name, expr in raw.items():
            if name in env:
                continue
            try:
                val = eval(expr, {"__builtins__": {}}, {**safe, **env})
                # 布尔要先判断 —— bool 是 int 的子类，会被下面的分支吞掉
                if isinstance(val, bool):
                    env[name] = val
                    progress = True
                elif isinstance(val, (int, float)):
                    env[name] = float(val)
                    progress = True
            except Exception:
                continue
        if not progress:
            break

    unresolved = [n for n in raw if n not in env]
    if unresolved:
        print(f"⚠️  以下参数无法解析（可能是列表/字符串/依赖缺失）：{', '.join(unresolved)}")

    return env


# KEYMAP 是列表，单独解析
def load_keymap(path=PARAMS):
    """返回 [(列, 行, 宽度u, 标签), ...]"""
    text = _strip_comments(open(path, encoding="utf-8").read())
    m = re.search(r"KEYMAP\s*=\s*\[(.*?)\n\s*\];", text, flags=re.S)
    if not m:
        return []
    body = m.group(1)
    out = []
    for row in re.findall(r"\[([^\]]+)\]", body):
        parts = [p.strip() for p in row.split(",")]
        if len(parts) < 4:
            continue
        try:
            out.append((int(parts[0]), int(parts[1]), int(parts[2]),
                        parts[3].strip().strip('"')))
        except ValueError:
            continue
    return out


if __name__ == "__main__":
    try:
        P = load()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        raise SystemExit(1)
    print(f"参数文件：{PARAMS}")
    print(f"解析到 {len(P)} 个数值参数")
    for k in ["PITCH", "GRID_W", "PLATE_W", "CASE_INNER_H", "CASE_OUTER_H",
              "SWITCH_PLATE_GAP", "TOTAL_H", "SW_BOSS_T"]:
        if k in P:
            print(f"  {k} = {P[k]}")
    km = load_keymap()
    print(f"KEYMAP: {len(km)} 个键位")

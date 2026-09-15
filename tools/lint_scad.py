# -*- coding: utf-8 -*-
"""
OpenSCAD 源码静态检查（无 OpenSCAD 环境时的降级方案）
----------------------------------------------------
OpenSCAD 的 `include` 会把被包含文件的定义并入同一命名空间，
所以符号检查必须建立「全局符号表」，否则会把跨文件引用误报成死代码。

检查项：
  1. 括号 / 中括号 / 大括号 配对
  2. include / use 路径是否存在
  3. 定义了但全局从未引用的符号（真死代码）
  4. module 重名定义
  5. for 循环单字母变量与 translate 坐标混用（易错模式）
  6. 同一 module 内重复给同一变量赋值

运行：python tools/lint_scad.py
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad")

# 检查顺序 = 依赖顺序（params 先，assembly 最后）
FILES = [
    "lib/params.scad",
    "plate.scad",
    "case_bottom.scad",
    "keycap.scad",
    "test_coupon.scad",
    "assembly.scad",
]

BUILTIN = {
    "cube", "sphere", "cylinder", "polyhedron", "square", "circle", "polygon",
    "translate", "rotate", "scale", "mirror", "resize", "multmatrix", "color",
    "union", "difference", "intersection", "hull", "minkowski", "linear_extrude",
    "rotate_extrude", "offset", "surface", "projection", "render", "children",
    "if", "else", "for", "let", "echo", "assert", "function", "module", "each",
    "import", "text", "len", "min", "max", "abs", "floor", "ceil", "round",
    "sqrt", "pow", "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "exp", "ln", "log", "sign", "norm", "cross", "concat", "lookup", "search",
    "str", "chr", "ord", "is_undef", "is_bool", "is_num", "is_string", "is_list",
    "true", "false", "undef", "PI", "parent_module", "version", "rands",
}


def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    return t


def read_all():
    """读取所有文件（去注释），返回 {文件名: 文本}"""
    out = {}
    for f in FILES:
        p = os.path.join(CAD, f)
        if not os.path.exists(p):
            continue
        out[f] = strip_comments(open(p, encoding="utf-8").read())
    return out


def get_spec_only():
    """
    收集标记为 `[spec]` 的变量名。
    这类变量是「设计规格记录」——给人和 PCB 设计用的参数，
    不参与 3D 几何建模，因此不算死代码。
    标记写在定义行的注释里，例如：
        WIRE_MAX_D = 2.20;   // 可通过的最大线径 [spec]
    """
    spec = set()
    for f in FILES:
        p = os.path.join(CAD, f)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            if "[spec]" in line:
                m = re.match(r"\s*([A-Za-z_]\w*)\s*=", line)
                if m:
                    spec.add(m.group(1))
    return spec


def check_balance(name, text):
    problems = []
    for o, c in [("{", "}"), ("(", ")"), ("[", "]")]:
        no, nc = text.count(o), text.count(c)
        if no != nc:
            problems.append(f"❌ {name}: '{o}{c}' 不配对（{o}={no}, {c}={nc}）")
    return problems


def main():
    print("=" * 70)
    print("OpenSCAD 源码静态检查（含跨文件符号表）")
    print("=" * 70)
    issues = []

    texts = read_all()
    all_text = "\n".join(texts.values())

    # ---- 1. 括号配对 ----
    for name, text in texts.items():
        issues += check_balance(name, text)

    # ---- 2. include / use 路径 ----
    for name, text in texts.items():
        for inc in re.findall(r'\b(?:include|use)\s*<([^>]+)>', text):
            if not os.path.exists(os.path.join(CAD, inc)):
                issues.append(f"❌ {name}: include 路径不存在 → {inc}")

    # ---- 3. 全局符号表 ----
    modules = {}
    functions = set()
    variables = set()
    for name, text in texts.items():
        for m in re.finditer(r"\bmodule\s+([A-Za-z_]\w*)\s*\(", text):
            modules.setdefault(m.group(1), []).append(name)
        for m in re.finditer(r"\bfunction\s+([A-Za-z_]\w*)\s*\(", text):
            functions.add(m.group(1))
        for m in re.finditer(r"^\s*([A-Za-z_]\w*)\s*=", text, flags=re.M):
            variables.add(m.group(1))

    # module 重名
    for mod, where in modules.items():
        if len(where) > 1:
            issues.append(f"❌ module {mod}() 重复定义于：{', '.join(where)}")

    known = set(modules) | functions | variables | BUILTIN

    # ---- 4. 真死代码：全局从未引用 ----
    # 只检查变量（module/function 常作为公开 API 保留）
    spec_only = get_spec_only()
    for v in sorted(variables):
        if v in spec_only:
            continue          # 设计规格记录，不算死代码
        # 统计全文件出现次数（减去定义那一处）
        n = len(re.findall(r"\b" + re.escape(v) + r"\b", all_text)) - 1
        if n <= 0:
            issues.append(f"⚠️  变量 {v} 全局定义了但从未引用（死代码）")

    # ---- 5. for 单字母循环变量 + translate 混用 ----
    for name, text in texts.items():
        for m in re.finditer(r"\bfor\s*\(\s*([A-Za-z_]\w*)\s*=", text):
            lv = m.group(1)
            if len(lv) == 1 and lv in "xyz":
                if re.search(r"translate\s*\(\s*\[\s*" + lv + r"\s*,", text):
                    issues.append(
                        f"⚠️  {name}: 循环变量 '{lv}' 与 translate 坐标混用（易错，建议改名）")

    # ---- 6. 同一 module 内重复赋值 ----
    for name, text in texts.items():
        for m in re.finditer(r"\bmodule\s+([A-Za-z_]\w*)\s*\([^)]*\)\s*\{", text):
            mod = m.group(1)
            start = m.end()
            depth, i = 1, start
            while i < len(text) and depth > 0:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            body = text[start:i]
            assigns = re.findall(r"^\s*([A-Za-z_]\w*)\s*=", body, flags=re.M)
            seen = {}
            for a in assigns:
                seen[a] = seen.get(a, 0) + 1
            for a, n in seen.items():
                if n > 1:
                    issues.append(
                        f"⚠️  {name}: module {mod}() 内变量 {a} 被赋值 {n} 次")

    # ---- 输出 ----
    print()
    if not issues:
        print("✅ 全部通过，未发现结构性问题")
    else:
        for it in issues:
            print(it)
        errs = sum(1 for i in issues if i.startswith("❌"))
        warns = len(issues) - errs
        print(f"\n合计：{errs} 个错误，{warns} 个提醒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

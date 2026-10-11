# -*- coding: utf-8 -*-
"""ClaudePad 元件 3D 模型生成器 v2（STEP AP214，零依赖）
--------------------------------------------------------
KiCad 10 官方库只用 STEP；WRL 在本机渲染管线行为异常（缩放/框架不可控），
故全部元件改用纯 Python 手写 STEP（长方体组合 + 颜色）。

坐标系（与 KiCad 一致）：x 右 / y 向下（KiCad 屏幕向）/ z 向上（+z = 正面朝外）
原点约定：
  choc_v2.step            轴芯中心, z=0 为 PCB 上表面
  header_pins_front.step  pad1（孔带顶端）, z=0 为 PCB 上表面
  header_plastic_back.step 同上, 胶条在 z<0（背面）
  promicro_at_JP1.step    偏移已烘焙（挂 JP1, offset 填 0）
  battery_at_PWR1.step    偏移已烘焙（挂 PWR1, offset 填 0）

重跑：C:\\Users\\尚\\AppData\\Local\\Programs\\Python\\Python312\\python.exe tools/gen_step_models.py
尺寸依据：cad/lib/params.scad §2/§6/§7
"""
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cad", "models")

# ---------------- STEP 写入器 ----------------
class StepBuilder:
    def __init__(self, name):
        self.name = name
        self.n = 0
        self.lines = []          # (id, body)
        self.solids = []         # solid ids

    def _add(self, body):
        self.n += 1
        self.lines.append((self.n, body))
        return self.n

    def box(self, cx, cy, cz, sx, sy, sz, rgb):
        """轴对齐长方体 → MANIFOLD_SOLID_BREP，返回 solid id。
        ★ 实测 KiCad STEP 管线镜像局部 Y（渲染位置 = fp + (x, −y, z)），
        故这里对 cy 取反预补偿；调用者给的 (cx,cy,cz) = 意图板坐标偏移。"""
        cy = -cy
        x0, x1 = cx - sx / 2, cx + sx / 2
        y0, y1 = cy - sy / 2, cy + sy / 2
        z0, z1 = cz - sz / 2, cz + sz / 2
        P = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
             (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
        # 顶点：8 个 CARTESIAN_POINT + 对应 VERTEX_POINT（EDGE_CURVE 只能引 VERTEX_POINT）
        cp = [self._add(f"CARTESIAN_POINT('',({x:.4f},{y:.4f},{z:.4f}))") for x, y, z in P]
        vp = [self._add(f"VERTEX_POINT('',#{cp[i]})") for i in range(8)]
        # 12 条边：底环 0-1-2-3、顶环 4-5-6-7、立边
        EDGES = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        ec = {}
        for i, (a, b) in enumerate(EDGES):
            dx, dy, dz = P[b][0]-P[a][0], P[b][1]-P[a][1], P[b][2]-P[a][2]
            ln = (dx*dx + dy*dy + dz*dz) ** 0.5
            d  = self._add(f"DIRECTION('',({dx/ln:.6f},{dy/ln:.6f},{dz/ln:.6f}))")
            v  = self._add(f"VECTOR('',#{d},{ln:.4f})")
            l  = self._add(f"LINE('',#{cp[a]},#{v})")
            e  = self._add(f"EDGE_CURVE('',#{vp[a]},#{vp[b]},#{l},.T.)")
            ec[i] = e
        # 6 个面：(环序列[(边id,正向?)...], 法线)
        # 顶: 4,5,6,7 全 T，法线 +z
        # 底: 0F,3F,2F,1F，法线 -z
        # +x: 9T,5F,10F,1F；-x: 11T,7F,8F,3F
        # +y: 10T,6T,11F,2F；-y: 0T,9F,4F,8F
        DIRS = {
            "+z": (0,0,1), "-z": (0,0,-1), "+x": (1,0,0), "-x": (-1,0,0), "+y": (0,1,0), "-y": (0,-1,0),
        }
        FACES = [
            ([(4,1),(5,1),(6,1),(7,1)], "+z"),
            ([(0,0),(3,0),(2,0),(1,0)], "-z"),
            ([(9,1),(5,0),(10,0),(1,0)], "+x"),
            ([(11,1),(7,0),(8,0),(3,0)], "-x"),
            ([(10,1),(6,1),(11,0),(2,0)], "+y"),
            ([(0,1),(9,0),(4,0),(8,0)], "-y"),
        ]
        shell = []
        for loop, nk in FACES:
            nx, ny, nz = DIRS[nk]
            oes = []
            for eid, forward in loop:
                oes.append(self._add(f"ORIENTED_EDGE('',*,*,#{ec[eid]},{'.T.' if forward else '.F.'})"))
            loop_id = self._add(f"EDGE_LOOP('',({','.join('#%d' % o for o in oes)}))")
            bound   = self._add(f"FACE_BOUND('',#{loop_id},.T.)")
            v0 = EDGES[loop[0][0]][0]
            nd = self._add(f"DIRECTION('',({nx},{ny},{nz}))")
            rd = self._add("DIRECTION('',(1,0,0))" if abs(nz) != 1 else "DIRECTION('',(0,1,0))")
            axp = self._add(f"AXIS2_PLACEMENT_3D('',#{cp[v0]},#{nd},#{rd})")
            pl  = self._add(f"PLANE('',#{axp})")
            fac = self._add(f"ADVANCED_FACE('',(#{bound}),#{pl},.T.)")
            shell.append(fac)
        sh = self._add(f"CLOSED_SHELL('',({','.join('#%d' % f for f in shell)}))")
        solid = self._add(f"MANIFOLD_SOLID_BREP('{self.name}_{len(self.solids)}',#{sh})")
        # 颜色（完整官方链：USAGE→SIDE→FILL_AREA→COLOUR）
        cr = self._add(f"COLOUR_RGB('',{rgb[0]:.3f},{rgb[1]:.3f},{rgb[2]:.3f})")
        fc = self._add(f"FILL_AREA_STYLE_COLOUR('',#{cr})")
        fs = self._add(f"FILL_AREA_STYLE('',(#{fc}))")
        sf = self._add(f"SURFACE_STYLE_FILL_AREA(#{fs})")
        ss = self._add(f"SURFACE_SIDE_STYLE('',(#{sf}))")
        su = self._add(f"SURFACE_STYLE_USAGE(.BOTH.,#{ss})")
        ps = self._add(f"PRESENTATION_STYLE_ASSIGNMENT((#{su}))")
        self._add(f"STYLED_ITEM('color',(#{ps}),#{solid})")
        self.solids.append(solid)
        return solid

    def save(self, path):
        # 骨架实体（编号紧接几何之后）
        pre = self.n
        ctx  = self._add("APPLICATION_CONTEXT('core data for automotive mechanical design processes')")
        self._add(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#{ctx})")
        pctx = self._add(f"PRODUCT_CONTEXT('',#{ctx},'mechanical')")
        prod = self._add(f"PRODUCT('{self.name}','{self.name}','',(#{pctx}))")
        pdf_ = self._add(f"PRODUCT_DEFINITION_FORMATION('','',#{prod})")
        dctx = self._add(f"PRODUCT_DEFINITION_CONTEXT('',#{ctx},'design')")
        pdef = self._add(f"PRODUCT_DEFINITION('','',#{pdf_},#{dctx})")
        pds  = self._add(f"PRODUCT_DEFINITION_SHAPE('','',#{pdef})")
        u1 = self._add("(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.))")
        u2 = self._add("(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))")
        u3 = self._add("(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT())")
        unc = self._add("UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#%d,'distance_accuracy_value','confusion accuracy')" % u1)
        gctx = self._add(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#{unc}))GLOBAL_UNIT_ASSIGNED_CONTEXT((#{u1},#{u2},#{u3}))REPRESENTATION_CONTEXT('','3D'))")
        oz = self._add("CARTESIAN_POINT('',(0,0,0))")
        dz = self._add("DIRECTION('',(0,0,1))")
        dx = self._add("DIRECTION('',(1,0,0))")
        ax = self._add(f"AXIS2_PLACEMENT_3D('',#{oz},#{dz},#{dx})")
        rep = self._add(f"SHAPE_REPRESENTATION('',(#{ax},{','.join('#%d' % s for s in self.solids)}),#{gctx})")
        self._add(f"SHAPE_DEFINITION_REPRESENTATION(#{pds},#{rep})")

        out = ["ISO-10303-21;", "HEADER;",
               "FILE_DESCRIPTION(('ClaudePad simplified component'),'2;1');",
               f"FILE_NAME('{self.name}.step','2026-10-09T12:00:00',(''),(''),'ClaudePad step gen','ClaudePad','');",
               "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
               "ENDSEC;", "DATA;"]
        out += [f"#{i}={body};" for i, body in self.lines]
        out += ["ENDSEC;", "END-ISO-10303-21;", ""]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(out))

# ---------------- 颜色 ----------------
GRAY_D = (0.22, 0.22, 0.26); GRAY_M = (0.34, 0.34, 0.40); GRAY_S = (0.30, 0.30, 0.35)
GOLD = (0.83, 0.69, 0.22); BLACK = (0.09, 0.09, 0.10); NAVY = (0.12, 0.23, 0.37)
SILVER = (0.75, 0.75, 0.78); BATT = (0.76, 0.78, 0.80); RED = (0.80, 0.20, 0.20)

def _promicro(b, dx, dy, dz):
    b.box(dx,      dy,      dz - 0.8,  17.78, 33.0, 1.6, NAVY)      # 主控板
    b.box(dx + 9.64, dy,   dz - 0.6,  1.5, 9.0, 1.8, SILVER)        # USB-C → +x（右壁）
    b.box(dx - 2.0,  dy + 4.0, dz - 2.1, 10.0, 10.0, 1.0, BLACK)    # NRF 屏蔽罩
    b.box(dx + 4.5,  dy - 8.0, dz - 1.95, 3.2, 2.0, 0.7, SILVER)    # 晶振
    b.box(dx - 7.0,  dy - 12.0, dz - 1.68, 2.5, 2.0, 0.16, GOLD)    # B+ 焊盘
    b.box(dx - 7.0,  dy - 8.5, dz - 1.68, 2.5, 2.0, 0.16, GOLD)     # B- 焊盘

def _battery(b, dx, dy, dz):
    """dz = 电池顶面高度：必须贴 PCB 底面 z=-1.6（顶面若在 z=0 会与板面共面 z-fighting）"""
    b.box(dx, dy, dz - 2.0, 30.0, 40.0, 4.0, BATT)
    b.box(dx + 14.6, dy + 2.5, dz - 3.6, 3.0, 1.0, 0.8, RED)        # 红线（B+）
    b.box(dx + 14.6, dy - 2.5, dz - 3.6, 3.0, 1.0, 0.8, BLACK)      # 黑线（B-）

def _aux_parts(b):
    """挂 PWR1(kicad 3,27)：电源开关 + 复位按钮 + 引线头（飞线示意，长线不画全）"""
    b.box(0, -2, 1.6, 6.0, 3.2, 3.2, BLACK)        # 电源开关本体 doc(3,25)
    b.box(0, -2, 3.8, 1.2, 1.2, 1.4, RED)          # 开关拨杆帽
    b.box(73, 6, 1.2, 4.4, 4.4, 2.4, BLACK)        # 复位按钮座 doc(76,17)
    b.box(73, 6, 3.0, 2.2, 2.2, 1.2, RED)          # 按钮帽
    b.box(6, -2, -0.8, 8.0, 0.8, 0.8, RED)         # 红线头（朝电池方向）
    b.box(6, -3.2, -0.8, 8.0, 0.8, 0.8, BLACK)     # 黑线头

def _lever(b):
    """挂 LEV1(kicad 89,33.5)：审批拨杆（实际装在外壳右壁，此处示意浮在缺口）"""
    b.box(7, 10.9, 0, 8.5, 13.0, 4.0, BLACK)       # 开关本体 doc(96,5.6)
    b.box(11.5, 10.9, 2.6, 1.6, 1.6, 5.2, SILVER)  # 螺纹轴套
    b.box(13.2, 10.9, 6.2, 3.2, 1.2, 1.2, SILVER)  # 拨杆手柄朝 +x（右壁外）

MODELS = {
    "choc_v2.step": lambda b: (
        b.box(0, 0, 0.8, 13.95, 13.95, 1.6, GRAY_D),                # 底座
        b.box(0, 0, 3.45, 15.0, 15.0, 3.7, GRAY_M),                 # 外壳（总高 5.3）
        b.box(0, 0, 6.0, 4.2, 1.3, 1.4, GRAY_S),                    # MX 十字 x
        b.box(0, 0, 6.0, 1.3, 4.2, 1.4, GRAY_S),                    # MX 十字 y
    ),
    "header_pins_front.step": lambda b: [b.box(0, k * 2.54, 1.8, 0.64, 0.64, 3.6, GOLD) for k in range(12)],
    "header_plastic_back.step": lambda b: b.box(0, 13.97, -1.25, 2.54, 27.94, 2.5, BLACK),
    "promicro_at_JP1.step": lambda b: _promicro(b, 7.62, 13.97, -2.5),   # 挂 JP1(kicad 80.97,7.03) → 中心 kicad (88.59,21)
    "battery_at_PWR1.step": lambda b: _battery(b, 13, -2, -1.6),         # 挂 PWR1(kicad 3,27) → 中心 kicad (16,25)，顶面贴板底
    "aux_parts_at_PWR1.step": _aux_parts,                                # 挂 PWR1：电源开关/复位按钮/引线头
    "lever_at_LEV1.step": _lever,                                        # 挂 LEV1：拨杆（缺口处示意）
}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, fn in MODELS.items():
        builder = StepBuilder(os.path.splitext(name)[0])
        fn(builder)
        path = os.path.join(OUT_DIR, name)
        builder.save(path)
        print(f"OK {name}  ({os.path.getsize(path)} B, {len(builder.solids)} solids)")

if __name__ == "__main__":
    main()

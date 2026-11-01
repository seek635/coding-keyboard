#!/usr/bin/env python3
"""Validate the exported ClaudePad STLs (bounding box + manifold edges)."""

from __future__ import annotations

import struct
import sys
from collections import Counter
from pathlib import Path

STL = Path(__file__).resolve().parents[1] / "cad" / "output" / "stl"

EXPECTED = {
    "case_bottom.stl": (108.0, 82.0, 14.8),
    "plate.stl": (102.0, 57.0, 1.2),
    "keycap_1u.stl": (17.6, 16.6, 5.0),
    "keycap_2u.stl": (35.6, 16.6, 5.0),
    "keycap_3u.stl": (53.6, 16.6, 5.0),
    "test_coupon.stl": (134.0, 44.0, 14.8),
}


def read_binary(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    data = path.read_bytes()
    if data[:5].lower() == b"solid":
        raise ValueError(f"{path.name}: ASCII STL not supported")
    n = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + n * 50:
        raise ValueError(f"{path.name}: truncated STL")
    tris = []
    for i in range(n):
        off = 84 + i * 50 + 12
        verts = []
        for v in range(3):
            verts.append(struct.unpack_from("<fff", data, off + v * 12))
        tris.append(tuple(verts))
    return tris


def main() -> int:
    failures = []
    for name, size in EXPECTED.items():
        path = STL / name
        if not path.exists():
            failures.append(f"{name}: missing")
            continue
        tris = read_binary(path)
        mins = [min(v[i] for tri in tris for v in tri) for i in range(3)]
        maxs = [max(v[i] for tri in tris for v in tri) for i in range(3)]
        bbox = tuple(maxs[i] - mins[i] for i in range(3))
        if any(abs(bbox[i] - size[i]) > 0.25 for i in range(3)):
            failures.append(f"{name}: bbox {bbox} != {size}")

        edges = Counter()
        for tri in tris:
            keys = [tuple(round(c, 4) for c in v) for v in tri]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edges[tuple(sorted((keys[a], keys[b])))] += 1
        bad = sum(1 for count in edges.values() if count != 2)
        if bad:
            failures.append(f"{name}: {bad} non-manifold edges")
        print(f"{name}: {len(tris)} triangles, bbox {tuple(round(v, 2) for v in bbox)}, "
              f"edges={len(edges)}, bad={bad}")

    if failures:
        print("FAIL")
        for failure in failures:
            print("  -", failure)
        return 1
    print("OK: all STLs are closed and sizes match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

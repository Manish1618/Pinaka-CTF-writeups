#!/usr/bin/env python3
"""Stage 1: decode survey_project.pinx and lidar_key.bin."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ashoka_io import read_pinx, read_lidar

F = sys.argv[1] if len(sys.argv) > 1 else "05-Ashokavana"
p = read_pinx(f"{F}/survey_project.pinx")
b, (off, _) = p["raw"], p["sections"]["CKSM"]
print("== survey_project.pinx ==")
for tag, (o, n) in p["sections"].items():
    print(f"  {tag}  offset={o:<5} size={n}")
s = sum(b[56:off]) & 0xffffffff
print(f"  CKSM stored={p['cksm'].hex()}  byte-sum(56..{off})={s:08x}  ->", "OK" if s == int(p["cksm"].hex(), 16) else "BAD")
fx, fy, cx, cy = p["intr"]
print(f"  INTR fx={fx} fy={fy} cx={cx} cy={cy}   <- focal length zeroed")
print(f"  IMGS {len(p['images'])} images, {sum(len(i['obs']) for i in p['images'])} observations")
k = p["images"][10]
print(f"  image 10: rvec={k['rvec']} C={k['C']}   <- key image pose zeroed")
print(f"  PT3D {len(p['points'])} points (ids {min(p['points'])}..{max(p['points'])})")
L = read_lidar(f"{F}/lidar_key.bin")
print("== lidar_key.bin ==")
print(f"  LPCD {len(L)} points, ids {min(L)}..{max(L)}")
for pid in (40, 44, 49):
    print(f"  {pid}: lidar={tuple(round(x, 3) for x in L[pid])}  survey={tuple(round(x, 2) for x in p['points'][pid])}")

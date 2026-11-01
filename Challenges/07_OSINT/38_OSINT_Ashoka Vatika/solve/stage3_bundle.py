#!/usr/bin/env python3
"""Stage 3: calibrate cameras, bundle-adjust with rolling shutter."""
import os, sys, pickle, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from ba import Problem

F = sys.argv[1] if len(sys.argv) > 1 else "05-Ashokavana"
OUT = sys.argv[2] if len(sys.argv) > 2 else "ba_result.pkl"
P = Problem(F)
s, R, t = P.align
print(f"survey -> lidar template similarity: scale={s:.4f}")
f0, fs, cams, pts = P.initial()
print(f"DLT focal per image: min={min(fs):.0f} median={f0:.0f} max={max(fs):.0f}")
x = P.pack(f0, np.zeros(4), cams, pts)
steps = [("pinhole", dict(distortion=False, rolling=False)),
         ("+ k1,k2", dict(distortion=True, tangential=False, rolling=False)),
         ("+ p1,p2", dict(distortion=True, tangential=True, rolling=False)),
         ("+ rolling shutter", dict(distortion=True, tangential=True, rolling=True))]
for name, opt in steps:
    P.distortion, P.tangential, P.rolling = opt["distortion"], opt.get("tangential", False), opt["rolling"]
    t0 = time.time()
    x, res = P.solve(x)
    r = P.residuals(x).reshape(-1, 2)
    e = np.hypot(r[:, 0], r[:, 1])
    print(f"  {name:<18} cost={res.cost:9.2f}  mean err={e.mean():.3f}px  max={e.max():.2f}px  ({time.time()-t0:.0f}s)")
f, lens, cams, pts = P.unpack(x)
print(f"focal f={f:.2f}  k1={lens[0]:.5f} k2={lens[1]:.5f} p1={lens[2]:.6f} p2={lens[3]:.6f}")
ri = P.residuals(x).reshape(-1, 2); iid = P._arrays()[0]
for i in (9, 10, 11):
    m = iid == i; print(f"  image {i:2d}: mean err {np.hypot(*ri[m].T).mean():.3f}px  |v|={np.linalg.norm(cams[i][6:9]):.3f} |w|={np.linalg.norm(cams[i][9:12]):.4f}")
pickle.dump({"x": x, "f": f, "lens": lens, "cams": cams, "pts": pts}, open(OUT, "wb"))
print(f"saved {OUT}")

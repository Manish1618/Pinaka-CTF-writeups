#!/usr/bin/env python3
"""Stage 4: city transform, key-camera pose, payload."""
import json, math, os, pickle, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from ashoka_io import load_json

F = sys.argv[1]; BA = sys.argv[2]; OUT = sys.argv[3] if len(sys.argv) > 3 else "submission.json"
city = load_json(f"{F}/city_model.json"); sens = load_json(f"{F}/sensor_calibration.json")
r = pickle.load(open(BA, "rb")); pts, cams = r["pts"], r["cams"]
lm = {d["id"]: np.array(d["xyz"]) for d in city["landmarks"]}
ids = sorted(lm)

# metric frame F: origin L0, +x toward L1 (horizontal), z up
L0, L1 = pts[0], pts[1]
h = (L1 - L0)[:2]; c, s = h / np.linalg.norm(h)
Rz = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
Fp = {k: Rz @ (pts[k] - L0) for k in ids}
b = city["benchmarks"]
est = np.linalg.norm(pts[b["ids"][1]] - pts[b["ids"][0]])
print(f"scale check: |L0L1| template={est:.4f} m  metric={b['baseline_metric_m']} m  k={b['baseline_metric_m']/est:.4f}")

# affine city xy -> F xy, constant z offset
Axy = np.array([[*lm[k][:2], 1] for k in ids]); Bxy = np.array([Fp[k][:2] for k in ids])
sol, *_ = np.linalg.lstsq(Axy, Bxy, rcond=None)
M, t = sol[:2].T, sol[2]
z_off = float(np.mean([Fp[k][2] - lm[k][2] for k in ids]))
res = Bxy - Axy @ sol
print(f"city->F affine: rms={math.sqrt((res**2).sum(1).mean()):.3f} m  det(M)={np.linalg.det(M):.4f}  (negative = mirrored)")
print(f"  M={M.round(5).tolist()}  t={t.round(3).tolist()}  z_off={z_off:.4f}")

# key camera at mid-readout (tau = 0), template frame
k = sens["key_observation"]["image_id"]
rv, C = cams[k][:3], cams[k][3:6]
qx, qy, qz, qw = Rot.from_rotvec(rv).as_quat()
quat = [qw, qx, qy, qz]
if quat[0] < 0: quat = [-q for q in quat]
datum = float(np.mean([lm[i][2] - Fp[i][2] for i in ids]))  # city z minus F z
alt = C[2] - L0[2] + datum  # C height in F, then to datum
print(f"key image {k}: C={np.round(C, 4).tolist()}  quat(w,x,y,z)={np.round(quat, 5).tolist()}")
print(f"altitude check: camera datum={alt:.3f} m  supplied={sens['key_observation']['altitude_m_above_datum']} m  diff={abs(alt-sens['key_observation']['altitude_m_above_datum'])*100:.1f} cm")
print(f"template origin datum: {-L0[2] + datum:.3f} m")

payload = {"garden_id": 2, "transform": {"M": M.tolist(), "t": t.tolist(), "z_off": z_off},
           "clock_skews": [0.37, -0.52, 0.21], "pose": {"C": C.tolist(), "quat": quat}}
json.dump(payload, open(OUT, "w"), indent=1)
print(f"wrote {OUT}")

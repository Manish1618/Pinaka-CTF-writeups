"""Readers for the Ashokavana survey files."""
import json, struct

def read_pinx(path):
    b = open(path, "rb").read()
    assert b[:4] == b"PINX"
    count = struct.unpack_from(">H", b, 6)[0]
    sec = {}
    for i in range(count):
        o = 8 + 12 * i
        sec[b[o:o+4].decode()] = (struct.unpack_from("<I", b, o+4)[0], struct.unpack_from(">I", b, o+8)[0])
    fx, fy, cx, cy = struct.unpack_from("<4d", b, sec["INTR"][0])
    o, _ = sec["IMGS"]
    n = struct.unpack_from(">I", b, o)[0]; o += 4
    images = []
    for _ in range(n):
        iid = struct.unpack_from("<I", b, o)[0]
        rvec = struct.unpack_from("<3d", b, o+4); C = struct.unpack_from("<3d", b, o+28)
        k = struct.unpack_from(">I", b, o+52)[0]; o += 56
        obs = []
        for _ in range(k):
            pid = struct.unpack_from("<I", b, o)[0]; u, v = struct.unpack_from("<2f", b, o+4)
            obs.append((pid, u, v)); o += 12
        images.append({"id": iid, "rvec": rvec, "C": C, "obs": obs})
    assert o == sum(sec["IMGS"])
    o, _ = sec["PT3D"]
    m = struct.unpack_from(">I", b, o)[0]; o += 4
    points = {}
    for _ in range(m):
        pid = struct.unpack_from("<I", b, o)[0]; points[pid] = struct.unpack_from("<3d", b, o+4); o += 28
    cksm = b[sec["CKSM"][0]:sum(sec["CKSM"])]
    return {"intr": (fx, fy, cx, cy), "images": images, "points": points, "cksm": cksm, "raw": b, "sections": sec}

def read_lidar(path):
    b = open(path, "rb").read()
    assert b[:4] == b"LPCD"
    n = struct.unpack_from("<I", b, 4)[0]
    pts = {}
    for i in range(n):
        pid = struct.unpack_from("<I", b, 8 + 28*i)[0]
        pts[pid] = struct.unpack_from("<3d", b, 12 + 28*i)
    return pts

def load_json(path):
    return json.load(open(path))

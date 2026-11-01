"""Shared bundle-adjustment model for Ashokavana."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
from ashoka_io import read_pinx, read_lidar

CX, CY, ROWS = 1500.0, 1000.0, 2000.0

def umeyama(src, dst):
    """Similarity dst ~ s*R@src + t."""
    ms, md = src.mean(0), dst.mean(0)
    A, B = src - ms, dst - md
    U, S, Vt = np.linalg.svd(B.T @ A / len(src))
    D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / (A ** 2).sum(1).mean()
    return s, R, md - s * R @ ms

def dlt(X, uv):
    rows = []
    for (x, y, z), (u, v) in zip(X, uv):
        P = [x, y, z, 1.0]
        rows.append([*P, 0, 0, 0, 0, *(-u * np.array(P))])
        rows.append([0, 0, 0, 0, *P, *(-v * np.array(P))])
    P = np.linalg.svd(np.array(rows))[2][-1].reshape(3, 4)
    M = P[:, :3]
    K, R = np.linalg.qr(np.linalg.inv(M))  # inv(M) = R^-1 K^-1
    K, R = np.linalg.inv(R), np.linalg.inv(K)
    S = np.diag(np.sign(np.diag(K))); K, R = K @ S, S @ R
    if np.linalg.det(R) < 0: R = -R
    C = -np.linalg.solve(M, P[:, 3])
    return K / K[2, 2], R, C

class Problem:
    def __init__(self, folder, distortion=True, rolling=True, tangential=True):
        self.p = read_pinx(f"{folder}/survey_project.pinx")
        self.L = read_lidar(f"{folder}/lidar_key.bin")
        self.distortion, self.rolling, self.tangential = distortion, rolling, tangential
        self.fixed = sorted(self.L)
        self.free = sorted(k for k in self.p["points"] if k not in self.L)
        self.nimg = len(self.p["images"])
        ids = sorted(self.L)
        s, R, t = umeyama(np.array([self.p["points"][k] for k in ids]), np.array([self.L[k] for k in ids]))
        self.align = (s, R, t)
        self.obs = [(im["id"], pid, u, v) for im in self.p["images"] for pid, u, v in im["obs"]]

    def to_template(self, X):
        s, R, t = self.align
        return s * R @ np.asarray(X) + t

    def initial(self):
        pts = {k: self.to_template(self.p["points"][k]) for k in self.free}
        pts.update({k: np.array(self.L[k]) for k in self.fixed})
        cams, fs = [], []
        for im in self.p["images"]:
            X = np.array([pts[pid] for pid, _, _ in im["obs"]])
            uv = np.array([(u, v) for _, u, v in im["obs"]])
            K, R, C = dlt(X, uv)
            fs.append((K[0, 0] + K[1, 1]) / 2)
            cams.append(np.r_[Rot.from_matrix(R).as_rotvec(), C, np.zeros(6)])
        f = float(np.median(fs))
        return f, fs, cams, pts

    def pack(self, f, lens, cams, pts):
        return np.r_[f, lens, np.concatenate(cams), np.concatenate([pts[k] for k in self.free])]

    def unpack(self, x):
        f, lens = x[0], x[1:5]
        o = 5
        cams = [x[o + 12 * i: o + 12 * i + 12] for i in range(self.nimg)]; o += 12 * self.nimg
        pts = {k: x[o + 3 * i: o + 3 * i + 3] for i, k in enumerate(self.free)}
        pts.update({k: np.array(self.L[k]) for k in self.fixed})
        return f, lens, cams, pts

    def project(self, f, lens, cam, X, row):
        rv, C, vel, om = cam[:3], cam[3:6], cam[6:9], cam[9:12]
        R = Rot.from_rotvec(rv).as_matrix()
        if self.rolling:
            tau = row / ROWS - 0.5
            R = Rot.from_rotvec(tau * om).as_matrix() @ R
            C = C + tau * vel
        Xc = R @ (X - C)
        x, y = Xc[0] / Xc[2], Xc[1] / Xc[2]
        k1, k2, p1, p2 = lens
        r2 = x * x + y * y
        if self.distortion:
            rad = 1 + k1 * r2 + k2 * r2 * r2
            xd, yd = x * rad, y * rad
            if self.tangential:
                xd += 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
                yd += p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        else:
            xd, yd = x, y
        return f * xd + CX, f * yd + CY

    def _arrays(self):
        if not hasattr(self, "_A"):
            self._A = (np.array([o[0] for o in self.obs]), np.array([o[1] for o in self.obs]),
                       np.array([o[2] for o in self.obs]), np.array([o[3] for o in self.obs]))
        return self._A

    def residuals(self, x):
        f, lens, cams, pts = self.unpack(x)
        iid, pid, u, v = self._arrays()
        cam = np.array(cams)[iid]
        X = np.array([pts[k] for k in range(max(pts) + 1)])[pid]
        rv, C, vel, om = cam[:, :3], cam[:, 3:6], cam[:, 6:9], cam[:, 9:12]
        R = Rot.from_rotvec(rv).as_matrix()
        if self.rolling:
            tau = (v / ROWS - 0.5)[:, None]
            R = Rot.from_rotvec(tau * om).as_matrix() @ R
            C = C + tau * vel
        Xc = np.einsum("nij,nj->ni", R, X - C)
        x_, y_ = Xc[:, 0] / Xc[:, 2], Xc[:, 1] / Xc[:, 2]
        k1, k2, p1, p2 = lens
        r2 = x_ * x_ + y_ * y_
        xd, yd = x_, y_
        if self.distortion:
            rad = 1 + k1 * r2 + k2 * r2 * r2
            xd, yd = x_ * rad, y_ * rad
            if self.tangential:
                xd = xd + 2 * p1 * x_ * y_ + p2 * (r2 + 2 * x_ * x_)
                yd = yd + p1 * (r2 + 2 * y_ * y_) + 2 * p2 * x_ * y_
        return np.ravel(np.column_stack([f * xd + CX - u, f * yd + CY - v]))

    def solve(self, x0):
        mask = np.ones_like(x0, bool)
        if not self.distortion: mask[1:5] = False
        if not self.tangential: mask[3:5] = False
        if not self.rolling:
            for i in range(self.nimg): mask[5 + 12 * i + 6: 5 + 12 * i + 12] = False
        idx = np.where(mask)[0]
        def fun(z):
            x = x0.copy(); x[idx] = z
            return self.residuals(x)
        res = least_squares(fun, x0[idx], method="trf", x_scale="jac", max_nfev=400)
        x = x0.copy(); x[idx] = res.x
        return x, res

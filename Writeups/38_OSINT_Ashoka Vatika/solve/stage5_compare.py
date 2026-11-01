#!/usr/bin/env python3
"""Stage 5: compare the new payload with the one the validator accepted earlier."""
import json, sys
import numpy as np

new = json.load(open(sys.argv[1])); old = json.load(open(sys.argv[2]))
def row(name, a, b):
    a, b = np.ravel(a), np.ravel(b)
    print(f"  {name:<12} max |diff| = {np.abs(a - b).max():.5f}")
print("== this solve vs. previously accepted payload ==")
print(f"  garden_id    {new['garden_id']} vs {old['garden_id']}")
row("clock_skews", new["clock_skews"], old["clock_skews"])
row("M", new["transform"]["M"], old["transform"]["M"])
row("t", new["transform"]["t"], old["transform"]["t"])
row("z_off", new["transform"]["z_off"], old["transform"]["z_off"])
row("pose.C", new["pose"]["C"], old["pose"]["C"])
row("pose.quat", new["pose"]["quat"], old["pose"]["quat"])
qa, qb = np.array(new["pose"]["quat"]), np.array(old["pose"]["quat"])
ang = 2 * np.degrees(np.arccos(min(1.0, abs(qa @ qb))))
print(f"  rotation difference: {ang:.4f} deg")
print(f"  camera centre difference: {np.linalg.norm(np.subtract(new['pose']['C'], old['pose']['C']))*100:.1f} cm")

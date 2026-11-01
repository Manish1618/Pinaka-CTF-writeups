#!/usr/bin/env python3
"""Stage 2: route ledger, tower clock skews, TDOA."""
import heapq, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ashoka_io import load_json

F = sys.argv[1] if len(sys.argv) > 1 else "05-Ashokavana"
routes = load_json(f"{F}/supply_routes.json")
city = load_json(f"{F}/city_model.json")
towers = load_json(f"{F}/watchtower_log.json")
speed = load_json(f"{F}/sensor_calibration.json")["watchtowers"]["signal_relay_speed"]

print("== route ledger ==")
graph = {}
for e in routes["edges"]:
    if e["time"] < 0:
        print(f"  dropping poisoned edge {e['a']}-{e['b']} (time {e['time']})")
        continue
    graph.setdefault(e["a"], []).append((e["b"], e["time"]))
    graph.setdefault(e["b"], []).append((e["a"], e["time"]))
dist, pq = {0: 0.0}, [(0.0, 0)]
while pq:
    d, n = heapq.heappop(pq)
    if d > dist.get(n, math.inf): continue
    for m, w in graph.get(n, []):
        if d + w < dist.get(m, math.inf):
            dist[m] = d + w; heapq.heappush(pq, (d + w, m))
target = routes["measured_travel_time_to_observed_garden"]
for g, node in routes["garden_node_map"].items():
    mark = "  <- match" if abs(dist[node] - target) < 1e-9 else ("  <- decoy" if abs(dist[node] - target) < 1 else "")
    print(f"  garden {g}: {dist[node]:g}{mark}")
print(f"  measured: {target}")

print("== tower clocks ==")
gate = city["city_gate_xy"]
txy = {t["id"]: t["xy"] for t in towers["towers"]}
cal = next(e for e in towers["events"] if e["event"] == "gate_calibration_flare")
skew = {}
for a in cal["arrivals"]:
    d = math.dist(gate, txy[a["tower"]])
    skew[a["tower"]] = round(a["recorded_time"] - d / speed, 4)
    print(f"  tower {a['tower']}: dist={d:.3f}  recorded={a['recorded_time']}  skew={skew[a['tower']]}")
gf = next(e for e in towers["events"] if e["event"] == "garden_flare")
t = {a["tower"]: a["recorded_time"] - skew[a["tower"]] for a in gf["arrivals"]}
dd = speed * (t[0] - t[1])
print(f"== TDOA ==\n  corrected arrivals {t}\n  d0 - d1 = {dd:.3f} m")
for g in city["garden_candidates"]:
    r = math.dist(g["xy"], txy[0]) - math.dist(g["xy"], txy[1])
    print(f"  garden {g['id']}: d0-d1 = {r:8.3f}  off by {abs(r - dd):7.3f}" + ("  <- on hyperbola" if abs(r - dd) < 0.5 else ""))

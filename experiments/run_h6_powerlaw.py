#!/usr/bin/env python3
"""H6: Message-size power law for anti-benefit BW threshold (derived from sweep_360)."""
import csv as csvmod, math

data = {}
with open('/home/azureuser/research-astra-sim/experiments/data/sweep_360.csv') as f:
    for row in csvmod.DictReader(f):
        key = (row['bw_ratio'], row['n_total'], row['msg_mb'])
        eff = float(row['eff_bw'])
        if key not in data: data[key] = {}
        data[key][f"{row['algo']}_{row['opt']}"] = eff

ratios_val = {'1:1':1,'2:1':2,'4:1':4,'8:1':8,'16:1':16,'24:1':24,'48:1':48}
ratios_order = list(ratios_val.keys())

print("=== Anti-benefit threshold by message size (N=16) ===")
crossover_pts = {}
for msg in ['1','10','100','1000']:
    first_ab = None; last_ok = None
    for bw in ratios_order:
        k = (bw, '16', msg)
        if k not in data: continue
        d = data[k]
        flat = d.get('oneRing_baseline', d.get('oneRing_localBWAware'))
        hier = d.get('ring_ring_baseline')
        if not flat or not hier: continue
        ratio = hier/flat
        if ratio < 1.0 and first_ab is None: first_ab = ratios_val[bw]
        if ratio >= 1.0: last_ok = ratios_val[bw]
    crossover_pts[int(msg)] = (last_ok, first_ab)
    print(f"  msg={msg}MB: hierarchy worse-than-flat starts at BW > {last_ok}:1 (first anti-benefit at {first_ab}:1)")

pts = []
for msg, (lo, hi) in sorted(crossover_pts.items()):
    if hi is not None:
        mid = math.sqrt((lo if lo else hi) * hi)
        pts.append((math.log10(msg), math.log10(mid)))

if len(pts) >= 2:
    n = len(pts)
    sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxy = sum(p[0]*p[1] for p in pts); sxx = sum(p[0]**2 for p in pts)
    alpha = (n*sxy - sx*sy) / (n*sxx - sx**2)
    beta = (sy - alpha*sx) / n
    print(f"\nPower law: threshold_BW ≈ {10**beta:.1f} × msg_mb^({alpha:.3f})")
    print(f"  α = {alpha:.3f}")
    print(f"  1MB prediction: {10**(alpha*0+beta):.0f}:1 (explains no anti-benefit seen for 1MB)")
    print(f"  5000MB prediction: {10**(alpha*math.log10(5000)+beta):.1f}:1")

with open('/home/azureuser/research-astra-sim/experiments/data/h6_powerlaw.csv','w') as f:
    w = csvmod.writer(f)
    w.writerow(['msg_mb','threshold_lower_bw','threshold_upper_bw'])
    for msg, (lo, hi) in sorted(crossover_pts.items()):
        w.writerow([msg, lo, hi])
print("\nSaved: data/h6_powerlaw.csv")

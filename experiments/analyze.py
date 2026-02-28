#!/usr/bin/env python3
"""Analysis of Astra-Sim efficiency experiments."""
import csv, sys
from collections import defaultdict

def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def analyze_sweep(rows):
    """Anti-benefit analysis: ring_ring_baseline vs oneRing."""
    # Group by (bw_ratio, n_total, msg_mb)
    by_config = defaultdict(dict)
    for r in rows:
        if r['status'] != 'ok':
            continue
        key = (r['bw_ratio'], r['n_total'], r['msg_mb'])
        label = f"{r['algo']}_{r['opt']}"
        by_config[key][label] = float(r['wall_ns'])

    anti_benefit = []
    rescued = []
    total_cells = 0

    for key, vals in by_config.items():
        if 'oneRing_baseline' not in vals or 'ring_ring_baseline' not in vals:
            continue
        total_cells += 1
        ratio = vals['ring_ring_baseline'] / vals['oneRing_baseline']
        row = {'config': key, 'ring_ring_vs_flat': ratio}
        if ratio < 1.0:
            anti_benefit.append(row)
            if 'ring_ring_localBWAware' in vals:
                lbw_ratio = vals['ring_ring_localBWAware'] / vals['oneRing_baseline']
                if lbw_ratio >= 1.0:
                    rescued.append({**row, 'lbw_ratio': lbw_ratio})
    return total_cells, anti_benefit, rescued

def analyze_active_chunks(rows):
    by_config = defaultdict(dict)
    for r in rows:
        if r['status'] != 'ok': continue
        key = (r['bw_ratio'], r['msg_mb'])
        by_config[key][int(r['active'])] = float(r['ebu'])
    return by_config

print("=== SWEEP ANALYSIS ===")
rows = load_csv('/home/azureuser/research-astra-sim/experiments/data/sweep_360.csv')
total, ab, rescued = analyze_sweep(rows)
print(f"Total configs: {total}")
print(f"Anti-benefit cells (ring_ring_baseline < oneRing): {len(ab)}/{total}")
print(f"Rescued by localBWAware: {len(rescued)}/{len(ab)}")
print("\nWorst anti-benefit cases:")
ab_sorted = sorted(ab, key=lambda x: x['ring_ring_vs_flat'])
for r in ab_sorted[:5]:
    bw, n, msg = r['config']
    print(f"  BW={bw}, N={n}, msg={msg}MB → ring_ring_baseline = {r['ring_ring_vs_flat']:.2f}× flat")

print("\n=== ACTIVE CHUNKS ANALYSIS ===")
ac_rows = load_csv('/home/azureuser/research-astra-sim/experiments/data/active_chunks.csv')
ac_data = analyze_active_chunks(ac_rows)
print("EBU (GB/s) by active_chunks, BW ratio, msg_mb:")
for (bw, msg), by_ac in sorted(ac_data.items()):
    vals = [by_ac.get(ac, float('nan')) for ac in [1, 2, 4, 8]]
    if by_ac.get(1) and by_ac.get(8):
        mult = by_ac[8] / by_ac[1]
        print(f"  BW={bw}:1, msg={msg}MB → ac1={vals[0]:.1f}, ac8={vals[3]:.1f} GB/s → {mult:.1f}× scaling")


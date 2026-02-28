#!/usr/bin/env python3
"""Exp2: active-chunks=16 test to check if linear scaling continues."""
import subprocess, json, os, csv, re, tempfile

BINARY = "/home/azureuser/astra-sim-repo/build/astra_analytical/build/bin/AstraSim_Analytical_Congestion_Unaware"
WORKLOAD_BASE = "/home/azureuser/astra-sim-repo/examples/workload/microbenchmarks/all_reduce/16npus_1MB/all_reduce"

def run_sim(ac, bw_gbps=50.0, lat_ns=500.0):
    with tempfile.TemporaryDirectory() as tmpdir:
        sys_cfg = {
            "scheduling-policy": "FIFO", "endpoint-delay": 10,
            "active-chunks-per-dimension": ac, "preferred-dataset-splits": 4,
            "all-reduce-implementation": ["ring"], "all-gather-implementation": ["ring"],
            "reduce-scatter-implementation": ["ring"], "all-to-all-implementation": ["ring"],
            "collective-optimization": "localBWAware", "local-mem-bw": 1600,
            "boost-mode": 0, "roofline-enabled": 0, "peak-perf": 900
        }
        with open(f"{tmpdir}/sys.json","w") as f: json.dump(sys_cfg, f)
        with open(f"{tmpdir}/net.yml","w") as f:
            f.write(f"topology: [ Ring ]\nnpus_count: [ 16 ]\nbandwidth: [ {bw_gbps} ]\nlatency: [ {lat_ns} ]\n")
        with open(f"{tmpdir}/rem.json","w") as f: json.dump({"enabled": 0}, f)
        r = subprocess.run([BINARY,
            f"--workload-configuration={WORKLOAD_BASE}",
            f"--system-configuration={tmpdir}/sys.json",
            f"--remote-memory-configuration={tmpdir}/rem.json",
            f"--network-configuration={tmpdir}/net.yml"],
            capture_output=True, text=True, timeout=120)
        times = re.findall(r"Wall time: (\d+)", r.stdout + r.stderr)
        return max(int(t) for t in times) if times else None

print("=== Exp2: ac=16 check ===")
for ac in [1, 2, 4, 8, 16]:
    w = run_sim(ac)
    ebu = 2*1e6/w if w else None
    print(f"ac={ac:2d}: wall_ns={w}, ebu={ebu:.4f} GB/s" if w else f"ac={ac}: FAILED")

#!/usr/bin/env python3
"""H1.1: Fine-grained BW crossover - exact anti-benefit onset.
Uses n0=8,n1=2 (=16 NPUs) matching the workload, bw0=600 GB/s intra fixed."""
import subprocess, json, os, csv, re, tempfile

BINARY = "/home/azureuser/astra-sim-repo/build/astra_analytical/build/bin/AstraSim_Analytical_Congestion_Unaware"
WORKLOAD = "/home/azureuser/astra-sim-repo/examples/workload/microbenchmarks/all_reduce/16npus_1MB/all_reduce"
REM_CFG = {"memory-type": "NO_MEMORY_EXPANSION"}

def run_sim(algo, sched, bw0, bw1):
    """algo: flat|hier, sched: baseline|localBWAware"""
    with tempfile.TemporaryDirectory() as d:
        if algo == "flat":
            sys_cfg = {
                "scheduling-policy": "FIFO", "endpoint-delay": 10,
                "active-chunks-per-dimension": 1, "preferred-dataset-splits": 4,
                "all-reduce-implementation": ["ring"], "all-gather-implementation": ["ring"],
                "reduce-scatter-implementation": ["ring"], "all-to-all-implementation": ["ring"],
                "collective-optimization": "baseline", "local-mem-bw": 1600,
                "boost-mode": 0, "roofline-enabled": 0, "peak-perf": 900
            }
            net = f"topology: [ Ring ]\nnpus_count: [ 16 ]\nbandwidth: [ {bw0} ]\nlatency: [ 500.0 ]\n"
        else:
            sys_cfg = {
                "scheduling-policy": "FIFO", "endpoint-delay": 10,
                "active-chunks-per-dimension": 1, "preferred-dataset-splits": 4,
                "all-reduce-implementation": ["ring","ring"], "all-gather-implementation": ["ring","ring"],
                "reduce-scatter-implementation": ["ring","ring"], "all-to-all-implementation": ["ring","ring"],
                "collective-optimization": sched, "local-mem-bw": 1600,
                "boost-mode": 0, "roofline-enabled": 0, "peak-perf": 900
            }
            net = (f"topology: [ Ring, Ring ]\nnpus_count: [ 8, 2 ]\n"
                   f"bandwidth: [ {bw0}, {bw1} ]\nlatency: [ 500.0, 2000.0 ]\n")

        with open(f"{d}/sys.json","w") as f: json.dump(sys_cfg, f)
        with open(f"{d}/net.yml","w") as f: f.write(net)
        with open(f"{d}/rem.json","w") as f: json.dump(REM_CFG, f)

        r = subprocess.run([BINARY,
            f"--workload-configuration={WORKLOAD}",
            f"--system-configuration={d}/sys.json",
            f"--remote-memory-configuration={d}/rem.json",
            f"--network-configuration={d}/net.yml"],
            capture_output=True, text=True, timeout=120)
        times = re.findall(r"Wall time: (\d+)", r.stdout + r.stderr)
        return max(int(t) for t in times) if times else None

BW0 = 600.0  # intra-node fixed (matches sweep_360)
# ratios: bw0/bw1 → bw1 = bw0/ratio
ratios = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 12.0, 24.0, 48.0]

print(f"{'ratio':>6} {'flat_ns':>10} {'hier_base':>12} {'hier_lbw':>10} {'r_base':>8} {'r_lbw':>8}")
results = []
for ratio in ratios:
    bw1 = BW0 / ratio
    flat_ns = run_sim("flat", "baseline", BW0, bw1)
    hier_base_ns = run_sim("hier", "baseline", BW0, bw1)
    hier_lbw_ns = run_sim("hier", "localBWAware", BW0, bw1)
    r_base = round(hier_base_ns / flat_ns, 4) if (flat_ns and hier_base_ns) else None
    r_lbw = round(hier_lbw_ns / flat_ns, 4) if (flat_ns and hier_lbw_ns) else None
    print(f"{ratio:>6.1f} {str(flat_ns):>10} {str(hier_base_ns):>12} {str(hier_lbw_ns):>10} {str(r_base):>8} {str(r_lbw):>8}")
    results.append({"ratio": ratio, "flat_ns": flat_ns, "hier_base_ns": hier_base_ns,
                    "hier_lbw_ns": hier_lbw_ns, "r_base": r_base, "r_lbw": r_lbw})

with open("/home/azureuser/research-astra-sim/experiments/data/bw_crossover.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["ratio","flat_ns","hier_base_ns","hier_lbw_ns","r_base","r_lbw"])
    w.writeheader(); w.writerows(results)
print("\nSaved bw_crossover.csv")
anti = [(r["ratio"], r["r_base"]) for r in results if r["r_base"] and r["r_base"] > 1.0]
if anti:
    print(f"Anti-benefit onset: first at ratio={anti[0][0]:.1f} (r_base={anti[0][1]:.3f})")
    # Find the sharp crossover
    no_anti = [r["ratio"] for r in results if r["r_base"] and r["r_base"] <= 1.0]
    if no_anti:
        print(f"Last safe ratio: {max(no_anti):.1f}")
else:
    print("No anti-benefit found in tested range")

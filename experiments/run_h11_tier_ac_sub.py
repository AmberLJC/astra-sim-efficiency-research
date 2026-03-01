#!/usr/bin/env python3
"""H11: Unified Tier-AC Substitution Model"""
import subprocess, json, csv, re, tempfile

BINARY = "/home/azureuser/astra-sim-repo/build/astra_analytical/build/bin/AstraSim_Analytical_Congestion_Unaware"

WL_MAP = {
    "1MB":    "/home/azureuser/astra-sim-repo/all_reduce/16npus_100MB/all_reduce",
    "100MB":  "/home/azureuser/astra-sim-repo/all_reduce/16npus_10485760MB/all_reduce",
    "1000MB": "/home/azureuser/astra-sim-repo/all_reduce/16npus_104857600MB/all_reduce",
}

def run_sim(net_yml, sys_cfg, workload):
    with tempfile.TemporaryDirectory() as d:
        with open(f"{d}/sys.json","w") as f: json.dump(sys_cfg, f)
        with open(f"{d}/net.yml","w") as f: f.write(net_yml)
        with open(f"{d}/rem.json","w") as f: json.dump({"memory-type": "NO_MEMORY_EXPANSION"}, f)
        r = subprocess.run([BINARY,
            f"--workload-configuration={workload}",
            f"--system-configuration={d}/sys.json",
            f"--remote-memory-configuration={d}/rem.json",
            f"--network-configuration={d}/net.yml"],
            capture_output=True, text=True, timeout=300)
        times = re.findall(r"Wall time: (\d+)", r.stdout + r.stderr)
        return max(int(t) for t in times) if times else None

def make_sys(algo_list, opt, ac):
    return {
        "scheduling-policy": "FIFO", "endpoint-delay": 10,
        "active-chunks-per-dimension": ac, "preferred-dataset-splits": 8,
        "all-reduce-implementation": algo_list, "all-gather-implementation": algo_list,
        "reduce-scatter-implementation": algo_list, "all-to-all-implementation": algo_list,
        "collective-optimization": opt,
        "local-mem-bw": 1600, "boost-mode": 0, "roofline-enabled": 0, "peak-perf": 900
    }

rows = []

for wl_tag, wl_path in WL_MAP.items():
    for ratio in [1, 2, 4, 8]:
        bw_intra = 600.0
        bw_inter = bw_intra / ratio
        bw_inter2 = bw_inter / ratio

        # 1D ring + varying AC
        net_1d = f"topology: [ Ring ]\nnpus_count: [ 16 ]\nbandwidth: [ {bw_intra} ]\nlatency: [ 500.0 ]\n"
        for ac in [1, 2, 3, 4, 8]:
            w = run_sim(net_1d, make_sys(["ring"], "baseline", ac), wl_path)
            rows.append({"wl":wl_tag,"ratio":ratio,"tier":"1D","ac":ac,"tier_ac_prod":1*ac,"wall_ns":w})
            print(f"{wl_tag} r={ratio} 1D ac={ac}: {w}")

        # 2D ring + ac
        net_2d = f"topology: [ Ring, Ring ]\nnpus_count: [ 8, 2 ]\nbandwidth: [ {bw_intra}, {bw_inter:.1f} ]\nlatency: [ 500.0, 2000.0 ]\n"
        for ac in [1, 2, 4]:
            w = run_sim(net_2d, make_sys(["ring","ring"], "localBWAware", ac), wl_path)
            rows.append({"wl":wl_tag,"ratio":ratio,"tier":"2D","ac":ac,"tier_ac_prod":2*ac,"wall_ns":w})
            print(f"{wl_tag} r={ratio} 2D ac={ac}: {w}")

        # 3D ring + ac
        net_3d = f"topology: [ Ring, Ring, Ring ]\nnpus_count: [ 4, 2, 2 ]\nbandwidth: [ {bw_intra}, {bw_inter:.1f}, {bw_inter2:.1f} ]\nlatency: [ 500.0, 2000.0, 10000.0 ]\n"
        for ac in [1, 2]:
            w = run_sim(net_3d, make_sys(["ring","ring","ring"], "localBWAware", ac), wl_path)
            rows.append({"wl":wl_tag,"ratio":ratio,"tier":"3D","ac":ac,"tier_ac_prod":3*ac,"wall_ns":w})
            print(f"{wl_tag} r={ratio} 3D ac={ac}: {w}")

out = "/home/azureuser/research-astra-sim/experiments/data/h11_tier_ac_sub.csv"
with open(out, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=["wl","ratio","tier","ac","tier_ac_prod","wall_ns"])
    wr.writeheader(); wr.writerows(rows)
print(f"\nSaved {len(rows)} rows to {out}")

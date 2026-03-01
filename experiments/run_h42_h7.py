#!/usr/bin/env python3
"""H4.2 + H7"""
import subprocess, json, csv, re, tempfile, math, os

BINARY = "/home/azureuser/astra-sim-repo/build/astra_analytical/build/bin/AstraSim_Analytical_Congestion_Unaware"

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
            capture_output=True, text=True, timeout=180)
        times = re.findall(r"Wall time: (\d+)", r.stdout + r.stderr)
        return max(int(t) for t in times) if times else None

def make_sys(algo_list, opt, ac, splits):
    return {
        "scheduling-policy": "FIFO", "endpoint-delay": 10,
        "active-chunks-per-dimension": ac, "preferred-dataset-splits": splits,
        "all-reduce-implementation": algo_list,
        "all-gather-implementation": algo_list,
        "reduce-scatter-implementation": algo_list,
        "all-to-all-implementation": algo_list,
        "collective-optimization": opt,
        "local-mem-bw": 1600, "boost-mode": 0, "roofline-enabled": 0, "peak-perf": 900
    }

WL_BASE = "/home/azureuser/astra-sim-repo/examples/workload/microbenchmarks/all_reduce"
available_wl = {}
for tag in ["1MB","10MB","100MB","1000MB"]:
    path = f"{WL_BASE}/16npus_{tag}/all_reduce"
    if os.path.exists(path) or os.path.exists(path+".txt"):
        available_wl[tag] = path

print(f"Available workloads: {list(available_wl.keys())}")

# H4.2: underprovision regime
print("\n=== H4.2: Underprovision (splits=8, ac=1..16, BW 8:1) ===")
BW0, BW1 = 600.0, 75.0
h42_rows = []
for wl_tag, wl_path in available_wl.items():
    ac1_wall = None
    for ac in [1, 2, 4, 8, 16]:
        net = f"topology: [ Ring, Ring ]\nnpus_count: [ 8, 2 ]\nbandwidth: [ {BW0}, {BW1} ]\nlatency: [ 500.0, 2000.0 ]\n"
        sys = make_sys(["ring","ring"], "localBWAware", ac, 8)
        w = run_sim(net, sys, wl_path)
        msg_mb = float(wl_tag.replace("MB",""))
        ebu = 2*msg_mb*1e6/w if w else None
        if ac == 1: ac1_wall = w
        spd = round(ac1_wall/w, 3) if (w and ac1_wall) else None
        h42_rows.append({"wl":wl_tag,"ac":ac,"splits":8,"wall_ns":w,"ebu_gbs":round(ebu,2) if ebu else None,"speedup_vs_ac1":spd})
        print(f"  {wl_tag} ac={ac:2d}: wall={w} ebu={ebu:.2f if ebu else 'N/A'} spd_vs_ac1={spd}")

# H7: 3D anti-benefit power law (100MB, vary BW ratio)
print("\n=== H7: 3D power law (4x2x2=16npus, 100MB, ratios vary) ===")
h7_rows = []
wl_path = available_wl.get("100MB")
if wl_path:
    for ratio in [1, 2, 4, 8, 16, 48]:
        bw1 = 600.0 / max(ratio, 1)
        bw2 = bw1 / max(ratio, 1) if ratio > 1 else bw1
        net3d = f"topology: [ Ring, Ring, Ring ]\nnpus_count: [ 4, 2, 2 ]\nbandwidth: [ 600.0, {bw1:.1f}, {bw2:.1f} ]\nlatency: [ 500.0, 2000.0, 10000.0 ]\n"
        flat_net = f"topology: [ Ring ]\nnpus_count: [ 16 ]\nbandwidth: [ 600.0 ]\nlatency: [ 500.0 ]\n"
        w3b = run_sim(net3d, make_sys(["ring","ring","ring"],"baseline",1,4), wl_path)
        w3l = run_sim(net3d, make_sys(["ring","ring","ring"],"localBWAware",1,4), wl_path)
        wf  = run_sim(flat_net, make_sys(["ring"],"baseline",1,4), wl_path)
        rb = round(w3b/wf, 4) if (w3b and wf) else None
        rl = round(w3l/wf, 4) if (w3l and wf) else None
        ab = "ANTI-BENEFIT" if (rb and rb>1) else "ok"
        h7_rows.append({"ratio":ratio,"bw1":round(bw1,1),"bw2":round(bw2,1),"flat_ns":wf,"3d_base_ns":w3b,"3d_lbw_ns":w3l,"ratio_3d_base_vs_flat":rb,"ratio_3d_lbw_vs_flat":rl,"ab_flag":ab})
        print(f"  {ratio}:1  3D_base/flat={rb}  3D_lbw/flat={rl}  {ab}")
else:
    print("  100MB workload not found")

out_dir = "/home/azureuser/research-astra-sim/experiments/data"
os.makedirs(out_dir, exist_ok=True)
with open(f"{out_dir}/h42_underprovision.csv","w") as f:
    w = csv.DictWriter(f, fieldnames=["wl","ac","splits","wall_ns","ebu_gbs","speedup_vs_ac1"])
    w.writeheader(); w.writerows(h42_rows)
if h7_rows:
    with open(f"{out_dir}/h7_3d_powerlaw.csv","w") as f:
        w = csv.DictWriter(f, fieldnames=list(h7_rows[0].keys()))
        w.writeheader(); w.writerows(h7_rows)
print("\nSaved results.")

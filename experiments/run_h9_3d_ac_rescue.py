#!/usr/bin/env python3
"""H9: Can higher ac rescue 3D hierarchy at moderate BW ratios?
H9 claim: ac=8 rescues 3D at BW≤8:1; 2D still wins at BW≥4:1.
"""
import subprocess, json, csv, re, tempfile, os

BINARY = "/home/azureuser/astra-sim-repo/build/astra_analytical/build/bin/AstraSim_Analytical_Congestion_Unaware"

WL_MAP = {
    "100MB":  "/home/azureuser/astra-sim-repo/all_reduce/16npus_100MB/all_reduce",
    "1000MB": "/home/azureuser/astra-sim-repo/all_reduce/16npus_1048576MB/all_reduce",
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
            capture_output=True, text=True, timeout=180)
        times = re.findall(r"Wall time: (\d+)", r.stdout + r.stderr)
        return max(int(t) for t in times) if times else None

def make_sys(algo_list, opt, ac, splits=8):
    return {
        "scheduling-policy": "FIFO", "endpoint-delay": 10,
        "active-chunks-per-dimension": ac, "preferred-dataset-splits": splits,
        "all-reduce-implementation": algo_list, "all-gather-implementation": algo_list,
        "reduce-scatter-implementation": algo_list, "all-to-all-implementation": algo_list,
        "collective-optimization": opt,
        "local-mem-bw": 1600, "boost-mode": 0, "roofline-enabled": 0, "peak-perf": 900
    }

rows = []
for wl_tag, wl_path in WL_MAP.items():
    for ratio in [1, 4, 8, 16]:
        intra_bw = 600.0
        inter_bw = intra_bw / ratio
        inter_bw2 = inter_bw / ratio  # 3rd tier: squared-down
        flat_net = "topology: [ Ring ]\nnpus_count: [ 16 ]\nbandwidth: [ 600.0 ]\nlatency: [ 500.0 ]\n"
        w_flat = run_sim(flat_net, make_sys(["ring"], "baseline", 1), wl_path)
        print(f"{wl_tag} ratio={ratio} flat={w_flat}")
        for ac in [1, 2, 4, 8, 16]:
            net2d = f"topology: [ Ring, Ring ]\nnpus_count: [ 8, 2 ]\nbandwidth: [ {intra_bw}, {inter_bw:.1f} ]\nlatency: [ 500.0, 2000.0 ]\n"
            net3d = f"topology: [ Ring, Ring, Ring ]\nnpus_count: [ 4, 2, 2 ]\nbandwidth: [ {intra_bw}, {inter_bw:.1f}, {inter_bw2:.1f} ]\nlatency: [ 500.0, 2000.0, 10000.0 ]\n"
            w2d = run_sim(net2d, make_sys(["ring","ring"], "localBWAware", ac), wl_path)
            w3d = run_sim(net3d, make_sys(["ring","ring","ring"], "localBWAware", ac), wl_path)
            r2f = round(w2d/w_flat, 4) if (w2d and w_flat) else None
            r3f = round(w3d/w_flat, 4) if (w3d and w_flat) else None
            r32 = round(w3d/w2d,  4) if (w3d and w2d)  else None
            rows.append({"wl":wl_tag,"ratio":ratio,"ac":ac,"flat_ns":w_flat,"2d_ns":w2d,"3d_ns":w3d,
                "2d_vs_flat":r2f,"3d_vs_flat":r3f,"3d_vs_2d":r32,
                "3d_beneficial":"yes" if (r3f and r3f<1) else "no",
                "3d_beats_2d":"yes" if (r32 and r32<1) else "no"})
            print(f"  ac={ac}: 2D/flat={r2f} 3D/flat={r3f} 3D/2D={r32}")

out_path = "/home/azureuser/research-astra-sim/experiments/data/h9_3d_ac_rescue.csv"
with open(out_path, "w") as f:
    dw = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    dw.writeheader(); dw.writerows(rows)
print(f"Saved: {out_path}")

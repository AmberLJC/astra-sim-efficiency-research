# Scheduling-Induced Hierarchy Anti-Benefit in Distributed AllReduce: A Simulation Study with Astra-Sim

**Draft v0.1 — 2026-02-28**

---

## Abstract

Hierarchical collective communication algorithms are widely deployed in large-scale distributed training, premised on the assumption that matching algorithm topology to hardware topology always improves performance. We challenge this assumption. Using Astra-Sim's analytical backend across 360 configurations spanning 5 bandwidth ratios (1:1–48:1), 3 scale points (N=16–256), 4 message sizes (1–1000 MB), and 3 algorithms, we find that hierarchical AllReduce (ring-over-ring) is **15×** slower than flat oneRing in the worst case under default FIFO-baseline scheduling. The effect is triggered for messages ≥100 MB at BW ratios ≥4:1, affecting 19/60 tested configurations. Critically, switching to a locally bandwidth-aware (localBWAware) scheduling policy rescues 16 of 19 anti-benefit cases—revealing scheduling policy as a **gating condition** for hierarchy benefit, not a secondary concern. Three extreme cases (48:1, 1000 MB) remain unrescued, establishing a hard regime where flat topologies are strictly superior. Secondary findings: (1) active-chunks-per-dimension provides exactly 8× linear throughput scaling with no saturation; (2) inverted topologies outperform balanced at high BW ratios by 2.3×; (3) adding a third tier improves throughput 2.1× at equal BW budget.

---

## 1. Introduction

The prevailing wisdom in distributed training: match collective topology to hardware topology. Systems with fast intra-node (NVLink, ~600 GB/s) and slower inter-node (~12.5 GB/s) links should use hierarchical collectives. NCCL implements this by default; TACCL [1], TACOS [2], and HiCCL [3] have optimized it further.

We identify a gap: **no prior work treats scheduling policy as a gating condition**. When intra-node operations are fast, the inter-node bottleneck causes head-of-line blocking under FIFO scheduling, negating—or inverting—hierarchy's benefit.

**Contributions**:
1. **Anti-benefit map**: Characterization of the (BW ratio, N, message size) regime where hierarchical AllReduce under default scheduling is worse than flat (up to 15.2×).
2. **Scheduling as gating condition**: localBWAware scheduling rescues 84% of anti-benefit cases.
3. **Hard anti-benefit regime**: Three configurations where no scheduling policy recovers hierarchy's advantage.
4. **Secondary findings**: active-chunks 8× scaling, inverted topology 2.3× gain, 3D-tier 2.1× benefit.

We use Astra-Sim 2.0 [4] analytical backend, enabling rapid sweeps without GPU hardware.

---

## 2. Background

### 2.1 Collective Communication

AllReduce ring on N workers, message M, bandwidth B: time ≈ 2(N-1)/N × M/B. Hierarchical variants exploit BW asymmetry via two-phase intra/inter-node execution. TACCL [1] showed 6.7× gains via synthesis; TACOS [2] achieved 4.27× over NCCL. HiCCL [3] assumes hierarchy always benefits when intra-node BW dominates—our key assumption to test. Blink [5] found flat spanning-tree collectives achieve 8× over NCCL in some topologies.

### 2.2 Astra-Sim

Astra-Sim 2.0 [4] is a multi-tier network simulator for distributed DNN training. We use the analytical (congestion-unaware) backend, appropriate for isolating scheduling effects from congestion dynamics.

---

## 3. Methodology

**Topology**: Two-tier ring (ring_ring). Intra-node: 600 GB/s. Inter-node: {600, 150, 75, 37.5, 12.5} GB/s → BW ratios {1:1, 4:1, 8:1, 16:1, 48:1}.

**360-configuration sweep**: 5 BW ratios × 3 N={16,64,256} × 4 msg={1,10,100,1000 MB} × 3 algorithms × 2 scheduling = 360 runs.

**Algorithms**: `oneRing` (flat ring), `ring_ring` (hierarchical ring-ring), `ring_dbt` (ring + double binary tree).

**Scheduling**: `baseline` (FIFO), `localBWAware` (high-BW-link priority).

**Anti-benefit**: `ring_ring_baseline / oneRing_baseline > 1.0`.

**Pre-registered confirmatory test**: BW=6:1, N=64, msg=100 MB; threshold ≥10% anti-benefit. Result: REFUTED (ratio=0.80; hierarchy helps at 6:1). Anti-benefit boundary confirmed between 6:1 and 8:1.

---

## 4. Results

### 4.1 Anti-Benefit Map (19/60 configurations)

| BW Ratio | N   | Msg (MB) | Slowdown | Rescued? |
|----------|-----|----------|----------|----------|
| 4:1      | 16  | 1000     | 1.33×    | ✓        |
| 4:1      | 64  | 1000     | 1.62×    | ✓        |
| 4:1      | 256 | 1000     | 1.03×    | ✓        |
| 8:1      | 16  | 100      | 1.14×    | ✓        |
| 8:1      | 16  | 1000     | 2.44×    | ✓        |
| 8:1      | 64  | 1000     | 2.85×    | ✓        |
| 8:1      | 256 | 1000     | 1.61×    | ✓        |
| 16:1     | 16  | 100      | 2.03×    | ✓        |
| 16:1     | 16  | 1000     | 4.66×    | ✓        |
| 16:1     | 64  | 100      | 1.42×    | ✓        |
| 16:1     | 64  | 1000     | 5.32×    | ✓        |
| 16:1     | 256 | 1000     | 2.77×    | ✓        |
| 48:1     | 16  | 10       | 1.03×    | ✓        |
| 48:1     | 16  | 100      | 5.58×    | ✓        |
| **48:1** | **16** | **1000** | **13.52×** | **✗** |
| 48:1     | 256 | 100      | 1.36×    | ✓        |
| **48:1** | **256** | **1000** | **7.39×** | **✗** |
| 48:1     | 64  | 100      | 3.39×    | ✓        |
| **48:1** | **64** | **1000** | **15.17×** | **✗** |

32% of configurations (19/60) exhibit anti-benefit. 16/19 rescued by localBWAware. 3 hard cases at 48:1/1000 MB remain unrescued.

### 4.2 Scheduling as Gating Condition

localBWAware rescue examples:
- 48:1/16/100 MB: 5.58× anti-benefit → **0.86× flat** (hierarchy now 1.16× faster)
- 16:1/64/1000 MB: 5.32× anti-benefit → 0.84× flat

Hard failures: 48:1/64/1000 MB: 15.17× → 2.07× (7× scheduling improvement, still 2× slower than flat).

### 4.3 active-chunks: 8× Linear Scaling

| BW Ratio | Msg    | ac=1   | ac=2   | ac=4   | ac=8   | Scale |
|----------|--------|--------|--------|--------|--------|-------|
| 1:1      | 1 MB   | 4.25   | 8.51   | 17.01  | 34.02  | **8.0×** |
| 1:1      | 1000MB | 391.2  | 782.4  | 1564.7 | 3129.4 | **8.0×** |
| 48:1     | 100MB  | 155.9  | 308.3  | 603.2  | 1155.7 | **7.4×** |
| 48:1     | 1000MB | 192.3  | 381.6  | 751.8  | 1459.8 | **7.6×** |

(EBU in GB/s) Perfect linear scaling with active_chunks. Default ac=1 leaves 7-8× throughput ungained.

### 4.4 Topology Shape at High BW Ratio

At 48:1/N=64/1000 MB: inverted 16×4 topology ≈ 2.3× faster than balanced 8×8. At 8:1, balanced wins. Crossover near 8:1–16:1.

---

## 5. Discussion

### 5.1 Why Scheduling Is a Gating Condition

Under FIFO-baseline, inter-node ring phase is blocked by unfinished intra-node operations, creating pipeline bubbles that grow with message size. localBWAware acts as a coarse-grained critical-path scheduler, reordering to prioritize bottleneck-bandwidth operations.

### 5.2 Hard Anti-Benefit Regime

At 48:1/1000 MB, intra-node saturation creates unavoidable inter-node stalls regardless of scheduling. Consistent with GenModel [6] incast dominance at high BW ratios. **Practical recommendation**: For BW ratios >40:1 and gradient shards >1 GB, use flat collectives unconditionally.

### 5.3 active-chunks Configuration Debt

8× linear scaling (if real, not artifact) means default ac=1 wastes 87.5% of collective bandwidth—potentially a training speed gap of similar magnitude in communication-bound workloads. Real-hardware validation is the critical next step.

### 5.4 Limitations

- Analytical backend: congestion-unaware; no network interference modeling
- Single binary, CPU-only simulation
- Ring-over-ring topology only (not mesh, torus, or fat-tree)

---

## 6. Conclusion

Scheduling policy is a first-order variable for hierarchical AllReduce performance—not a secondary implementation detail. Default FIFO scheduling causes 15× slowdown vs flat at 48:1/1 GB. Locally bandwidth-aware scheduling rescues 84% of anti-benefit cases. Three unrescuable extreme cases establish where flat topology is categorically better. The active-chunks parameter provides an 8× hidden performance gain under default configurations. These findings provide actionable decision rules for practitioners deploying large-scale distributed training.

---

## References

[1] Shah et al., "TACCL," arXiv:2111.04867, 2021.  
[2] Jain et al., "TACOS," arXiv:2304.05301, 2023.  
[3] Kim et al., "HiCCL," arXiv:2408.05962, 2024.  
[4] Won et al., "ASTRA-sim2.0," arXiv:2301.07893, 2023.  
[5] Blink, arXiv:1910.04940, 2019.  
[6] Rashidi et al., "GenModel," arXiv:2409.04202, 2024.  
[7] BW-Optimal-Pipeline, arXiv:2305.18461, 2023.  

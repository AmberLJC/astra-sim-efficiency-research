# Literature Survey: Training Systems Efficiency via Astra-Sim
Date: 2026-02-28 | Phase: Literature Survey

## Research Question
How can training system efficiency be improved from multiple perspectives
(collective communication, topology design, scheduling policy, memory, parallelism)
using Astra-Sim as the simulation backbone?

## Key Papers

| Paper | Year | Core Finding | Gap It Reveals |
|-------|------|-------------|----------------|
| TACOS (2304.05301) | 2023 | Topology-aware synthesis 4.27× over NCCL | Studies algorithm; ignores scheduling policy |
| TACCL (2111.04867) | 2021 | Sketch-guided 6.7× over NCCL on DGX-2 | Default heuristics systematically suboptimal |
| HiCCL (2408.05962) | 2024 | 17× over GPU-aware MPI via primitive decomp | Assumes hierarchy ALWAYS helps — no anti-benefit analysis |
| GenModel/GenTree (2409.04202) | 2024 | Extended (α,β,γ,incast) model; 1.22–1.65× over NCCL | Shows incast is a first-order term standard model misses |
| BW-Optimal Pipeline (2305.18461) | 2023 | Polynomial-time optimal chunk pipelining | Assumes monotone improvement with chunks — may not hold |
| ASTRA-sim 2.0 (Rashidi et al.) | 2024 | Hierarchical multi-tier simulation platform | Our experimental substrate |
| Demystifying NCCL (2507.04786) | 2025 | First NCCL internals analysis: ring vs. tree | Ground truth for simulation calibration |
| Blink (1910.04940) | 2019 | Spanning-tree flat collectives 8× over NCCL | Strong flat baseline to compare hierarchy against |
| BandPilot (2506.15595) | 2025 | Learns BW model; 92–97% efficiency on H100 | Practitioners consistently fail to achieve peak BW |
| SWOT (2510.19322) | 2025 | Overlap reconfiguration + data; 89.7% reduction | Scheduling decisions dominate collective performance |

## Critical Novelty Gaps

1. **Scheduling-induced anti-benefit of hierarchy**: No prior work shows scheduling policy
   can flip hierarchy from slower-than-flat to faster-than-flat. HiCCL et al. never test
   the anti-benefit regime.

2. **active-chunks-per-dimension as hidden knob**: No paper characterizes how concurrent
   active chunks per dimension affects EBU — practitioners likely leave 8× on the table.

3. **Non-monotone chunk granularity**: BW-optimal pipeline theory assumes monotone improvement;
   empirically the optimum is BW-ratio-dependent with 7× penalty at extremes.

4. **Asymmetric topology optimality**: No study predicts which topology shape (n0×n1) is
   optimal as a function of BW ratio alone.

5. **3D vs 2D topology at equal BW budget**: Counter-intuitive improvement from adding a
   third network tier — mechanism and generality not studied.

## Verdict: Proceed to Hypothesis Generation
Clear novelty gap in scheduling-topology interaction space.

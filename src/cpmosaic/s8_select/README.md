# Stage 8 · Choose the best product

**Status:** planned — not built yet. Stage 1 (collector) runs first so that images start accumulating.

**Framework:** Phase 6

**Input:** data/verify/ (last 14 days)

**Output:** selection/current.json, selection/history.csv

**Plan**
- Rule v1 in config/select.yaml: daily ranking on pooled wet cycles, ranks averaged over four scores,
- switch only after 3 consecutive daily wins (and bootstrap P(better) ≥ 0.8), Extrapolation as the last fallback.
- Planned modules: aggregate.py, rank.py, switch.py.

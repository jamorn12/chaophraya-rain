# Stage 7 · Verify every forecast

**Status:** planned — not built yet. Stage 1 (collector) runs first so that images start accumulating.

**Framework:** Phase 5–6

**Input:** archived nowcasts + the mosaic observed later

**Output:** data/verify/<YYYY>/<MM>/<DD>.parquet: raw contingency counts (20/35 dBZ), FSS sums (30 dBZ, 10 km), squared errors, per model × lead

**Plan**
- Stored, never shown on the public site.
- Inside the basin and QI ≥ 0.5 only (config/select.yaml).

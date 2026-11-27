# Stage 5 · Nowcast

**Status:** planned — not built yet. Stage 1 (collector) runs first so that images start accumulating.

**Framework:** Phase 6 (RQ3)

**Input:** the last 4 mosaics

**Output:** data/nowcast/<issue>Z_<model>.nc: +15 to +120 min every 15 min

**Plan**
- Models: Extrapolation, S-PROG, STEPS (central value shown), LINDA; persistence as the baseline.
- Same pySTEPS settings as the thesis unless the mosaic needs a change; every forecast is archived.

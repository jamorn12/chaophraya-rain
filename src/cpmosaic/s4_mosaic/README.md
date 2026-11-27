# Stage 4 · Composite the nine radars

**Status:** planned — not built yet. Stage 1 (collector) runs first so that images start accumulating.

**Framework:** Phase 4 (RQ2)

**Input:** data/qc/... (all radars of one 15-min slot)

**Output:** data/mosaic/<YYYY>/<MM>/<DD>/mosaic_<slot>Z.nc: dBZ + QI + source radar, basin + 50 km, AEQD 1 km

**Plan**
- Four methods to compare: M1 maximum, M2 nearest radar, M3 inverse distance, M4 QI-weighted.
- Rule for a missing radar; a slot is published if the core radars are present.

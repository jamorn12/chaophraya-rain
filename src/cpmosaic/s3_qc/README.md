# Stage 3 · Per-radar quality control

**Status:** planned — not built yet. Stage 1 (collector) runs first so that images start accumulating.

**Framework:** Phase 3 (RQ1)

**Input:** data/decoded/...

**Output:** data/qc/<CODE>/... dBZ + quality index QI ∈ [0, 1] per pixel + QC log

**Plan**
- Interference rays, static clutter from echo frequency (include fixed mountain-top echoes), speckle.
- Beam blockage and beam height from the DEM (4/3 Earth).
- Range and attenuation flags; inter-radar bias from the overlaps.

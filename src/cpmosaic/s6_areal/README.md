# Stage 6 · Rain by area

**Status:** planned — not built yet. Stage 1 (collector) runs first so that images start accumulating.

**Framework:** Phase 6

**Input:** mosaic and best-product nowcast

**Output:** data/areal/<issue>Z.parquet: sub-basin, district, sub-district rain class and mm/h, now / +30 / +60 / 3-h total

**Plan**
- TanFon method: area mean of rain rate, cells below 16.5 dBZ count as zero (Z = 200R^1.6).
- Boundaries: RTSD via OCHA HDX (districts, sub-districts); HydroBASINS level 6 (sub-basins).

# Stage 2 · Decode images to dBZ

**Status:** planned — not built yet. Stage 1 (collector) runs first so that images start accumulating.

**Framework:** Phase 2 (RQ1)

**Input:** data/raw/<CODE>/...jpg + config/radars.yaml (layout A–D)

**Output:** data/decoded/<CODE>/<YYYY>/<MM>/<DD>/<CODE>_<scan>Z.nc (dBZ on the radar's own polar/pixel grid) + decode log

**Plan**
- Read the scan time from the footer by OCR (the server gives no Last-Modified header); one footer box per layout.
- Georeference each layout by fitting the range rings, checked with town markers (target ≤ 1 km).
- Invert the colour table to dBZ; remove map lines, labels and rings.
- Report the decoding error per layout (RQ1). Start with layout A, which TanFon already decodes.

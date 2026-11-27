"""Conceptual framework: Chao Phraya basin radar mosaic built from TMD operational "High Quality" radar images.
Drawn, no data. Six phases; each row = inputs -> processing -> outputs and checks.

    python conceptual_framework_mosaic.py [out_basename]
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

OUT = sys.argv[1] if len(sys.argv) > 1 else "conceptual_framework_mosaic"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

PH = ["#37474f", "#1565c0", "#00838f", "#2e7d32", "#ef6c00", "#6a1b9a", "#ad1457"]   # phase 0-6
IN_FC, PR_FC, OUT_FC = "#f3f5f8", "#ffffff", "#f6f9f1"

W, H = 100.0, 131.0
fig = plt.figure(figsize=(13.5, 13.5 * H / W * 0.92))
ax = fig.add_axes((0.005, 0.005, 0.99, 0.99)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")


def box(x, y, w, h, title, body, fc, ec, fs=8.4, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12,rounding_size=0.6", fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x + 0.8, y + h - 0.7, title, ha="left", va="top", fontsize=fs + 0.6, fontweight="bold", color=ec, zorder=3)
    ax.text(x + 0.8, y + h - 2.9, body, ha="left", va="top", fontsize=fs, linespacing=1.32, zorder=3)


def arrow(p0, p1, color="0.25", lw=1.3, ls="-", rad=0.0, ms=12):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=4, shrinkA=0, shrinkB=0))


# ---------------- title ----------------
ax.text(1, H - 1.2, "Conceptual framework — a basin-scale radar mosaic for the Chao Phraya basin "
        "built from TMD operational radar images", ha="left", va="top", fontsize=13.5, fontweight="bold")
ax.text(1, H - 4.4, "9 radars (CRI, LMP, TAK, PHS, PHB, CHN, KKW, SVP, SKM) · 15-min scans · own decoding, "
        "quality control and compositing (TMD national composite not used as the product)",
        ha="left", va="top", fontsize=9.6, color="0.3")

# column headers
X0, XI, XP, XO = 1.0, 12.6, 35.6, 70.2      # phase tag, inputs, processing, outputs
WI, WP, WO = 21.6, 33.0, 23.8
hy = H - 8.6
for x, w, t in ((XI, WI, "Inputs"), (XP, WP, "Processing"), (XO, WO, "Outputs and checks")):
    ax.text(x + w / 2, hy, t, ha="center", va="center", fontsize=10.5, fontweight="bold", color="0.25")
    ax.plot([x, x + w], [hy - 1.2, hy - 1.2], color="0.6", lw=0.8)
ax.text(X0 + 5.6, hy, "Phase", ha="center", va="center", fontsize=10.5, fontweight="bold", color="0.25")

# ---------------- phases ----------------
phases = [
    ("0", "Scope and\nbase data",
     "Base data", "• Radar sites (radars.csv, verified\n  to ≤3 km from image fits)\n• Basin + rivers (HydroBASINS,\n  HydroRIVERS), provinces (RTSD)\n• DEM (SRTM / Copernicus 30 m)\n• Rain gauges (TMD, RID, HII …)",
     "Design", "• Domain: Chao Phraya + Tha Chin basin (157,000 km²)\n  plus 50-km buffer; common grid AEQD 1 km\n• Coverage analysis: 7 radars cover 87 % ≤120 km;\n  ≥2 radars 40 %, ≥3 radars 12 %\n• Select study period and storm cases\n  (pre-monsoon, monsoon, stratiform)",
     "Deliverables", "• gis_base library (fixed layers)\n• Radar network + coverage map\n• Study-period definition",
     11.5),
    ("1", "Acquisition\nand archive",
     "TMD web products", "• {code}240_HQ_latest.jpg × 9\n  (overwritten every 15 min,\n  no archive online)\n• Short loops for gap recovery",
     "Automated collector (GitHub Actions, every 15 min)", "• Download 9 images; hash de-duplication\n• Read scan time from the footer (OCR ensemble)\n  and check against the slot / file time\n• Store raw JPG (cloud storage) + inventory table\n• Log gaps, late scans, layout changes",
     "Raw archive", "• Raw images, one per station\n  per 15-min slot\n• Inventory: availability %,\n  gap length, timing offset",
     11.5),
    ("2", "Image\ndecoding",
     "Per-station image layout", "• 4 layouts: CRI/PHS/CHN/SKM;\n  LMP (800 px); TAK/KKW/SVP;\n  PHB (CMAX)\n• Colour bar of each layout\n• Range rings, crosshair,\n  town markers",
     "Image → dBZ field", "• Georeference: centre + km/px from ring fit;\n  validate with town markers (target error ≤1 km)\n• Colour-table inversion → dBZ (nearest colour,\n  JPEG-noise tolerance)\n• Remove map, borders, labels, rings (masks)\n• Product metadata: PPI elevation or CMAX",
     "Per-station dBZ grids", "• dBZ on native image grid\n  (≈0.30 km/px) → polar/AEQD\n• Decoding error: ring fit (px),\n  town error (km), colour\n  misclassification rate",
     12.5),
    ("3", "Per-station\nquality control",
     "Per-station dBZ + DEM", "• Decoded dBZ fields\n• Long-term echo frequency\n• DEM for beam path",
     "Quality control and quality index (QI)", "• Interference rays (radial-line detection)\n• Static clutter (echo-frequency map), speckle filter\n• Beam blockage + beam height (4/3-Earth, DEM)\n• Range / attenuation flags; QI per pixel ∈ [0, 1]\n• Inter-radar bias from overlap zones (ΔdBZ)",
     "QC'd fields", "• dBZ + QI per station\n• Static masks (clutter,\n  blockage) per radar\n• Bias table between radars",
     12.0),
    ("4", "Compositing\n(mosaic)",
     "QC'd fields of 9 radars", "• Same 15-min slot\n  (time tolerance rule)\n• Different products:\n  PPI 0.5–1.6°, CMAX (PHB)",
     "Compositing methods (compared)", "• M1 maximum dBZ\n• M2 nearest radar\n• M3 inverse-distance weighting\n• M4 QI-weighted (beam height, blockage, range)\n• Missing-radar rule (re-composite without it)",
     "Mosaic product", "• Basin mosaic dBZ, AEQD 1 km,\n  15 min, + QI and source map\n• NetCDF (CF), reproducible\n  from raw images",
     11.0),
    ("5", "Evaluation",
     "Independent references", "• Rain gauges (hourly)\n• Overlap zones\n  (≥2 radars)\n• TMD composite\n  (benchmark only, optional)",
     "Verification", "• Inter-radar consistency in overlaps (bias, RMSD)\n• Radar QPE (Z-R) vs gauges: bias, RMSE, r, CSI\n• Seam / discontinuity check along range limits\n• Leave-one-radar-out test\n• Case studies by storm type",
     "Best method + error budget", "• Ranking of M1–M4\n• Error budget: decoding vs QC\n  vs compositing\n• Limits: mountains, far range",
     11.5),
    ("6", "Application",
     "Mosaic time series", "• Basin mosaic 15 min\n• Single-radar PHS\n  (baseline)",
     "Nowcasting with pySTEPS", "• Same models on mosaic vs single radar\n• Lead time 15–120 min; CSI, FSS, BIAS,\n  skill horizon; inflow from upstream radars\n• Basin / sub-basin rain accumulation",
     "Paper + TanFon", "• Gain of a mosaic over one radar\n• Basin rainfall product\n• Live mosaic layer in TanFon",
     10.5),
]

y = hy - 2.6
centers = []
for k, (num, name, ti, bi, tp, bp, to, bo, hh) in enumerate(phases):
    col = PH[k]
    top = y; bot = y - hh
    ax.add_patch(Rectangle((X0 - 0.2, bot - 0.6), XO + WO - X0 + 0.6, hh + 1.2, fc=col, alpha=0.05, ec="none", zorder=0))
    ax.add_patch(FancyBboxPatch((X0, bot), 10.4, hh, boxstyle="round,pad=0.12,rounding_size=0.8", fc=col, ec=col, zorder=2))
    ax.text(X0 + 5.2, bot + hh * 0.66, f"Phase {num}", ha="center", va="center", fontsize=11.5, fontweight="bold",
            color="white", zorder=3)
    ax.text(X0 + 5.2, bot + hh * 0.33, name, ha="center", va="center", fontsize=9.6, color="white", zorder=3,
            linespacing=1.2)
    box(XI, bot, WI, hh, ti, bi, IN_FC, col)
    box(XP, bot, WP, hh, tp, bp, PR_FC, col, lw=1.6)
    box(XO, bot, WO, hh, to, bo, OUT_FC, col)
    arrow((XI + WI + 0.3, bot + hh / 2), (XP - 0.3, bot + hh / 2), color=col)
    arrow((XP + WP + 0.3, bot + hh / 2), (XO - 0.3, bot + hh / 2), color=col)
    centers.append((bot, top))
    if k < len(phases) - 1:
        # output of this phase feeds the inputs of the next
        # straight elbow: down from the output box, across the gap, down into the next input box
        xa, xb, ym = XO + WO / 2, XI + WI / 2, bot - 1.5
        ax.plot([xa, xa, xb], [bot - 0.15, ym, ym], color="0.45", lw=1.1, zorder=4, solid_joinstyle="miter")
        arrow((xb, ym), (xb, bot - 2.88), color="0.45", lw=1.1, ms=10)
    y = bot - 3.0

# feedback loop: evaluation tunes decoding / QC / compositing
b5, t5 = centers[5]; b2, t2 = centers[2]
xr = XO + WO + 1.6
ax.plot([XO + WO + 0.3, xr], [b5 + 3.0, b5 + 3.0], color=PH[5], lw=1.2, ls="--")
ax.plot([xr, xr], [b5 + 3.0, t2 - 3.0], color=PH[5], lw=1.2, ls="--")
arrow((xr, t2 - 3.0), (XO + WO + 0.3, t2 - 3.0), color=PH[5], ls="--", lw=1.2)
ax.text(xr + 0.6, (b5 + t2) / 2, "tune thresholds,\nweights and\ncolour tables", rotation=90, ha="left", va="center",
        fontsize=8.2, color=PH[5])

# ---------------- research questions ----------------
yq = y - 0.5
ax.text(X0, yq, "Research questions", ha="left", va="top", fontsize=11, fontweight="bold", color="0.2")
rqs = [("RQ1", "Can operational radar display images be\nturned into quantitative dBZ fields\nwith a known, small error?", "Phases 1–3", PH[2]),
       ("RQ2", "Which compositing method gives the\nmost consistent basin mosaic,\nand where does it fail?", "Phases 4–5", PH[4]),
       ("RQ3", "Does the basin mosaic improve\nnowcast skill and lead time\nover a single radar (PHS)?", "Phase 6", PH[6])]
wq = (XO + WO - X0 - 2 * 1.2) / 3
for i, (tag, q, ph, col) in enumerate(rqs):
    xq = X0 + i * (wq + 1.2)
    ax.add_patch(FancyBboxPatch((xq, yq - 11.4), wq, 9.4, boxstyle="round,pad=0.12,rounding_size=0.6", fc="white",
                                ec=col, lw=1.4, zorder=2))
    ax.text(xq + 0.8, yq - 2.6, f"{tag}  ·  {ph}", ha="left", va="top", fontsize=9.6, fontweight="bold", color=col)
    ax.text(xq + 0.8, yq - 4.9, q, ha="left", va="top", fontsize=8.7, linespacing=1.3)

fig.savefig(OUT + ".png", dpi=220)
fig.savefig(OUT + ".pdf")
print("saved", OUT)

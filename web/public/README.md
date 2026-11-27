# Public site (planned)

Bilingual (ไทย / EN). Pages from the mock-up: rain map with the 2-h best-product forecast and switchable layers
(radar sites, 240/120 km rings per radar, basin, sub-basins, rivers, provinces, towns) · rain by area (sub-basin,
district, sub-district) · past rain (observed vs forecast made +15 to +120 min earlier) · about.

Not shown here: model choice, quality index, radar status, scores, raw images, NetCDF.
When the system is off (`data/status.json` has `"mode": "paused_loop_last_forecast"`): no live clock, no
"rain arrives in N min"; the map loops the last observed frames and the last 2-h forecast made before the pause,
with the banner text from `message_th` / `message_en` and the pause time. When `"mode": "live"`, normal behaviour.

Reads only: the latest mosaic tiles, `selection/current.json` (to label the forecast), and the areal tables.

# Expert / admin site

Main admin page: the Streamlit app in `admin/streamlit_app.py` (same look as the TanFon admin hub).
It reads the status bundle that the s1-collect workflow publishes to GitHub Pages
(`data/status/latest.json`, `history_48h.csv`, `thumbs/<CODE>.jpg`) and the GitHub API.
Secret `GITHUB_TOKEN` (fine-grained, this repo only, Actions: Read and write) enables the on/off switch.

`index.html` here is a light fallback (switch + recent runs) served at
https://jamorn12.github.io/chaophraya-rain/admin/

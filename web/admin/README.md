# Expert / admin site (planned)

Not linked from the public site. Pages from the mock-up: live (all layers, manual model choice, status of the nine
radars) · best product and other models · verification and selection ranking · detailed sub-basin and
district / sub-district tables · radars and data quality · archive and downloads (raw images, NetCDF, GIF).

Built: `index.html` (open it from disk or from Pages). Shows the system switch with an on/off button, the last
s1-collect runs and the switch history. The button calls the `control` workflow through the GitHub API with a
fine-grained token (this repo only, Actions: Read and write) kept in the browser's localStorage; without a token it
opens the Actions page so the workflow can be run by hand. `?repo=owner/name` points it at another repo.

Next page to build: collector health from `data/inventory` (images per radar per day, 96 expected).

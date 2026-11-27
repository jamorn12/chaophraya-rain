# Privacy · chaophraya-rclone

`chaophraya-rclone` is the Google OAuth client used only by the owner of this repository (jamorn12) to copy
the radar images this project collects into his own Google Drive with rclone.

- Scope: `drive.file` only. The app can see and change only files and folders that it created itself
  (the `ChaoPhraya_Radar_Archive` folder). It cannot read any other file in the Drive.
- No personal data is collected, stored, shared or sold. The only data handled are public weather-radar
  images published by the Thai Meteorological Department and the inventory files made from them.
- The OAuth token is kept as an encrypted GitHub Actions secret of this repository and is used only by the
  `s1-collect` workflow.
- Access can be removed at any time at https://myaccount.google.com/connections

Contact: open an issue at https://github.com/jamorn12/chaophraya-rain/issues

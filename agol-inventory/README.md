# Find connections between ArcGIS Online items.
- Standalone script: v 1.0, 2022-02-24
- Jupyter notebook: v 1.0, 2022-02-24

## Requirements
- Requires ArcGIS Pro.
  - Developed and tested in ArcGIS Pro 2.9.1 with the default ArcGIS Pro python environment.
- Requires a csv format item report generated in ArcGIS Online (AGOL).
  - Field names must be unchanged from original report.
- Requires user to be logged into AGOL Administrator (Admin) account through ArcGIS Pro.
  - Or **(Not Recommended)** have the username and password for an Admin account **(Not recommended)**.
  - If you use this method, credentials are entered and passed to AGOL as plain text. Delete after running the script.
- Cannot process Hub sites.
  - They are skipped and excluded from output.

## Input
- CSV file containing organization item information. Generated in AGOL and downloaded by user before using script.

## Output
- Excel table listing connections between organization items. Every connection (e.g., a layer is in a map, a map is in an app, etc.) is one line-item.

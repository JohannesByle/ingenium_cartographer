# LiDAR Averaging / Terrain Processing

This folder contains the LiDAR averaging and terrain-processing section of the larger project.

The main script is:

- `lidar_topography_tool.py`

It can:

- process a single scan into a cleaned terrain mesh
- batch-compare scans over time
- view final terrain meshes in chronological order
- generate synthetic test data if needed

## Install

Use the universal installer first:

```bash
python install_lidar_env.py
```

This works as the main installer on macOS, Linux, and Windows as long as Python 3 is installed.

OS-specific wrappers are also included if you want them:

- macOS / Linux: `./install_lidar_env.sh`
- Windows PowerShell: `.\install_lidar_env.ps1`
- Windows CMD: `install_lidar_env.cmd`

The installer:

- creates or reuses `open3d_env`
- installs the required libraries from `requirements-lidar.txt`
- verifies that `numpy`, `scipy`, and `open3d` import correctly

## Run

After installing, run:

```bash
python lidar_topography_tool.py
```

That opens the quick-start menu:

1. Process one point-cloud file
2. Batch compare a folder of scans
3. View all final meshes in the current directory
4. Generate synthetic point cloud

## Single-Scan Workflow

Use option `1` to process one scan.

Supported input formats include:

- `.ply`
- `.asc`
- `.pcd`
- `.xyz`
- `.xyzn`
- `.xyzrgb`
- `.pts`
- `.txt`

For each processed file, the script creates a folder named:

```text
<input_name>_outputs/
```

That folder contains:

- the final terrain mesh
- preview meshes
- the filtered near-ground cloud
- a short run summary

## Batch Workflow

Use option `2` to compare a folder of scans over time.

The script will:

- find supported scan files in the folder
- try to detect dates from filenames such as `YYYYMMDD` or `YYYY-MM-DD`
- show the detected chronological order and let you confirm or reorder it
- process the scans and compute progress metrics
- optionally append to an existing report folder or create a new one
- optionally play the final terrain meshes in chronological order

Batch output is written to a folder like:

```text
batch_volume_analysis_<timestamp>/
```

That folder contains:

- `batch_volume_report.txt`
- `per_scan_metrics.csv`
- `consecutive_differences.csv`
- `progress_graph.txt`
- `detected_excavation_mask_points.ply`

The reporting is percentage-first. The main progress metrics are:

- cumulative progress by scan
- daily share by interval

## View Existing Finals

Use option `3` to play all existing `*_terrain_final.ply` files found inside `*_outputs/` folders in the current directory.

The viewer:

- sorts them chronologically using detected dates
- loops them continuously
- shows terminal progress text while playing

## Notes

- Generated outputs, local environments, editor files, and caches are ignored by `.gitignore`.
- If filename date detection is wrong, rename files to include `YYYYMMDD` or `YYYY-MM-DD`.
- This section is designed to be committed cleanly without local output folders or virtual environments.

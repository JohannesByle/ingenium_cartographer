# LiDAR Averaging

Linux-only LiDAR terrain-processing workflow for cleaning scans, building terrain meshes, comparing excavation progress over time, and generating synthetic test data.

## Repository Layout

- `lidar_topography_tool.py`: main application script
- `install_lidar_env.sh`: Linux setup script for the local virtual environment
- `requirements-lidar.txt`: Python dependency list used by the installer

## Linux Requirements

- Linux
- Python `3.10`, `3.11`, or `3.12`
- `python3-venv`
- a working OpenGL-capable desktop session if you want the Open3D viewers

On Debian/Ubuntu, install the venv package first if needed:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv
```

## Install

Make the scripts executable and run the Linux installer:

```bash
chmod +x install_lidar_env.sh lidar_topography_tool.py
./install_lidar_env.sh
```

The installer:

- creates or reuses `open3d_env`
- upgrades `pip`, `setuptools`, and `wheel`
- installs the packages from `requirements-lidar.txt`
- verifies `numpy`, `scipy`, and `open3d`

If you need a different interpreter, set `PYTHON_BIN`:

```bash
PYTHON_BIN=python3.11 ./install_lidar_env.sh
```

## Run

Use the environment Python directly:

```bash
./open3d_env/bin/python ./lidar_topography_tool.py
```

Or activate the environment first:

```bash
source ./open3d_env/bin/activate
python ./lidar_topography_tool.py
```

The interactive menu provides:

1. Process one point-cloud file
2. Batch compare a folder of scans
3. View all final meshes in the current directory
4. Generate synthetic point cloud
5. Exit

## Command-Line Usage

```bash
./open3d_env/bin/python ./lidar_topography_tool.py menu
./open3d_env/bin/python ./lidar_topography_tool.py process ./scan.ply
./open3d_env/bin/python ./lidar_topography_tool.py batch ./scans --view-timeline
./open3d_env/bin/python ./lidar_topography_tool.py view-finals --dir .
./open3d_env/bin/python ./lidar_topography_tool.py generate --output synthetic_excavation.ply
```

## Supported Input Formats

- `.ply`
- `.asc`
- `.pcd`
- `.xyz`
- `.xyzn`
- `.xyzrgb`
- `.pts`
- `.txt`

## Output Structure

Single-file processing creates:

```text
<input_name>_outputs/
```

Typical contents:

- final terrain mesh
- preview meshes
- near-ground filtered cloud
- run summary

Batch comparison creates:

```text
batch_volume_analysis_<timestamp>/
```

Typical contents:

- `batch_volume_report.txt`
- `per_scan_metrics.csv`
- `consecutive_differences.csv`
- `progress_graph.txt`
- `detected_excavation_mask_points.ply`

## GitHub-Ready Notes

- `.gitignore` already excludes local environments, caches, and generated LiDAR outputs.
- Do not commit `open3d_env/` or any `*_outputs/` or `batch_volume_analysis_*` directories.
- If scan ordering is wrong, rename files to include `YYYYMMDD` or `YYYY-MM-DD`.

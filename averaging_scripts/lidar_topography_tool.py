#!/usr/bin/env python3

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import open3d as o3d
from scipy.ndimage import distance_transform_edt, gaussian_filter, median_filter


SUPPORTED_EXTS = {".ply", ".pcd", ".xyz", ".xyzn", ".xyzrgb", ".pts", ".asc", ".txt"}


@dataclass
class SyntheticConfig:
    area: float = 10.0
    res: float = 0.03
    pit_x0: float = 3.5
    pit_x1: float = 6.5
    pit_y0: float = 3.0
    pit_y1: float = 6.0
    pit_depth: float = 1.2
    wall_width: float = 0.5
    noise_z: float = 0.01
    noise_xy: float = 0.003
    n_trees: int = 20000
    n_outliers: int = 1000
    add_tarp: bool = True
    tarp_height: float = 0.55
    tarp_hole_fraction: float = 0.15
    seed: int = 0
    output_name: str = "synthetic_excavation.ply"


@dataclass
class TerrainConfig:
    num_levels: int = 3
    base_factor: float = 1.5
    step_factor: float = 0.75
    grid_scale: float = 3.5
    low_percentile: float = 5.0
    continuity_jump: float = 0.10
    max_hole_distance_cells: int = 25
    smooth_sigma: float = 1.0
    smooth_passes: int = 2
    max_slope: float = 0.18
    low_cluster_min_points: int = 2
    robust_z_clip_mad: float = 8.0
    use_statistical_outlier: bool = True
    stat_nb_neighbors: int = 24
    stat_std_ratio: float = 2.5
    use_radius_outlier: bool = False
    radius_nb_points: int = 8
    radius_mult: float = 2.5
    ground_keep_height: float = 0.35
    suppress_elevated_covers: bool = True
    cover_height_threshold: float = 0.30
    cover_min_cells: int = 20
    cover_median_window: int = 9
    despike_height_threshold: float = 0.18
    despike_window: int = 3
    ridge_height_threshold: float = 0.22
    ridge_window: int = 7
    ridge_min_component_cells: int = 4
    final_relief_clamp: float = 0.20
    excavation_detect_threshold: float = 0.12
    excavation_detect_window: int = 31
    excavation_min_cells: int = 25
    animate: bool = False
    overlay_points: bool = False
    save_mesh: bool = True
    save_ground_cloud: bool = True
    save_previews: bool = True


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            ans = input(f"{prompt} {suffix}: ").strip().lower()
        except EOFError:
            return default
        if not ans:
            return default
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Please enter y or n.")


def ask_int(prompt: str, min_v: int, max_v: int, default: Optional[int] = None) -> int:
    while True:
        default_label = f" [default {default}]" if default is not None else ""
        try:
            s = input(f"{prompt} ({min_v}-{max_v}){default_label}: ").strip()
        except EOFError:
            if default is not None:
                return default
            raise
        if s == "" and default is not None:
            return default
        try:
            value = int(s)
        except ValueError:
            value = None
        if value is not None and min_v <= value <= max_v:
            return value
        print(f"Enter an integer between {min_v} and {max_v}.")


def ask_float(prompt: str, min_v: float, max_v: float, default: Optional[float] = None) -> float:
    while True:
        default_label = f" [default {default}]" if default is not None else ""
        try:
            s = input(f"{prompt} ({min_v}-{max_v}){default_label}: ").strip()
        except EOFError:
            if default is not None:
                return float(default)
            raise
        if s == "" and default is not None:
            return float(default)
        try:
            value = float(s)
        except ValueError:
            value = None
        if value is not None and min_v <= value <= max_v:
            return value
        print(f"Enter a number between {min_v} and {max_v}.")


def list_point_cloud_files(directory: Path) -> list[Path]:
    files = [p for p in sorted(directory.iterdir()) if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    return files


def choose_point_cloud_file(directory: Path) -> Path:
    files = list_point_cloud_files(directory)
    if not files:
        raise FileNotFoundError(f"No supported point cloud files found in {directory}")

    print("\nPoint cloud files:")
    for i, f in enumerate(files, start=1):
        print(f"  {i}. {f.name}")
    idx = ask_int("Choose a file", 1, len(files), default=1)
    return files[idx - 1]


def cloud_from_points(points: np.ndarray) -> o3d.geometry.PointCloud:
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points.astype(np.float64))
    return pcd


def _looks_like_esri_ascii_grid(lines: list[str]) -> bool:
    header_keys = {"ncols", "nrows", "xllcorner", "yllcorner", "xllcenter", "yllcenter", "cellsize", "nodata_value"}
    checked = 0
    for line in lines[:10]:
        s = line.strip()
        if not s:
            continue
        checked += 1
        key = s.split()[0].lower()
        if key in header_keys:
            continue
        return False
    return checked >= 4


def load_esri_ascii_grid_as_point_cloud(path: Path) -> o3d.geometry.PointCloud:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        raw_lines = [line.rstrip("\n") for line in f if line.strip()]

    header = {}
    data_start = 0
    for i, line in enumerate(raw_lines):
        parts = line.split()
        if len(parts) >= 2 and parts[0].lower() in {
            "ncols", "nrows", "xllcorner", "yllcorner", "xllcenter", "yllcenter", "cellsize", "nodata_value"
        }:
            header[parts[0].lower()] = float(parts[1])
            data_start = i + 1
        else:
            break

    ncols = int(header.get("ncols", 0))
    nrows = int(header.get("nrows", 0))
    cellsize = float(header.get("cellsize", 0))
    if ncols <= 0 or nrows <= 0 or cellsize <= 0:
        raise ValueError("Invalid ESRI ASCII grid header.")

    x0 = header.get("xllcorner", header.get("xllcenter", 0.0))
    y0 = header.get("yllcorner", header.get("yllcenter", 0.0))
    use_center = "xllcenter" in header or "yllcenter" in header
    nodata = header.get("nodata_value", -9999.0)

    rows = []
    for line in raw_lines[data_start:]:
        vals = [float(v) for v in line.split()]
        if vals:
            rows.append(vals)
        if len(rows) >= nrows:
            break
    if len(rows) != nrows:
        raise ValueError(f"Expected {nrows} grid rows, found {len(rows)}.")

    Z = np.asarray(rows, dtype=np.float64)
    if Z.shape[1] != ncols:
        raise ValueError(f"Expected {ncols} columns, found {Z.shape[1]}.")

    mask = ~np.isclose(Z, nodata)
    iy, ix = np.where(mask)

    # ESRI ASCII grid rows are top-to-bottom; convert to increasing Y.
    ix_f = ix.astype(np.float64)
    iy_from_bottom = (nrows - 1 - iy).astype(np.float64)
    if use_center:
        xs = x0 + ix_f * cellsize
        ys = y0 + iy_from_bottom * cellsize
    else:
        xs = x0 + (ix_f + 0.5) * cellsize
        ys = y0 + (iy_from_bottom + 0.5) * cellsize
    zs = Z[iy, ix]

    return cloud_from_points(np.column_stack((xs, ys, zs)))


def load_ascii_xyz_point_cloud(path: Path) -> o3d.geometry.PointCloud:
    points = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            # Skip common headers/comments
            lower = s.lower()
            if lower.startswith(("#", "//", "x y", "x,y", "easting", "northing")):
                continue
            s = s.replace(",", " ")
            parts = s.split()
            if len(parts) < 3:
                continue
            try:
                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
            except ValueError:
                continue
            points.append((x, y, z))
    if not points:
        raise ValueError("No XYZ points found in ASCII file.")
    return cloud_from_points(np.asarray(points, dtype=np.float64))


def load_point_cloud(path: Path) -> o3d.geometry.PointCloud:
    ext = path.suffix.lower()
    if ext == ".asc":
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            head = [next(f, "") for _ in range(8)]
        if _looks_like_esri_ascii_grid(head):
            print("Detected ESRI ASCII grid (.asc); converting grid cells to point cloud...")
            return load_esri_ascii_grid_as_point_cloud(path)
        print("Detected ASCII point cloud (.asc); reading XYZ columns...")
        return load_ascii_xyz_point_cloud(path)
    if ext == ".txt":
        print("Detected ASCII point cloud (.txt); reading XYZ columns...")
        return load_ascii_xyz_point_cloud(path)

    return o3d.io.read_point_cloud(str(path))


def generate_synthetic_excavation(cfg: SyntheticConfig) -> Path:
    rng = np.random.default_rng(cfg.seed)

    xs = np.arange(0, cfg.area, cfg.res)
    ys = np.arange(0, cfg.area, cfg.res)
    X, Y = np.meshgrid(xs, ys)
    X = X.ravel()
    Y = Y.ravel()

    Z = 0.02 * X + 0.01 * Y + 0.03 * np.sin(0.8 * X) * np.cos(0.7 * Y)

    inside = (
        (X > cfg.pit_x0) & (X < cfg.pit_x1) &
        (Y > cfg.pit_y0) & (Y < cfg.pit_y1)
    )
    dx = np.minimum(X - cfg.pit_x0, cfg.pit_x1 - X)
    dy = np.minimum(Y - cfg.pit_y0, cfg.pit_y1 - Y)
    d_edge = np.minimum(dx, dy)
    wall_factor = np.clip(d_edge / cfg.wall_width, 0, 1)
    Z[inside] -= cfg.pit_depth * wall_factor[inside]

    Xj = np.clip(X + rng.normal(0, cfg.noise_xy, size=len(X)), 0, cfg.area)
    Yj = np.clip(Y + rng.normal(0, cfg.noise_xy, size=len(Y)), 0, cfg.area)
    Zj = Z + rng.normal(0, cfg.noise_z, size=len(Z))

    ground = np.column_stack((Xj, Yj, Zj))

    trees = np.column_stack((
        rng.uniform(0, cfg.area, cfg.n_trees),
        rng.uniform(0, cfg.area, cfg.n_trees),
        rng.uniform(0.5, 4.0, cfg.n_trees),
    ))

    outliers = np.column_stack((
        rng.uniform(0, cfg.area, cfg.n_outliers),
        rng.uniform(0, cfg.area, cfg.n_outliers),
        rng.uniform(-1.5, 6.0, cfg.n_outliers),
    ))

    blocks = [ground, trees, outliers]

    if cfg.add_tarp:
        tarp_mask = inside.copy()
        tarp_keep = rng.random(np.count_nonzero(tarp_mask)) > cfg.tarp_hole_fraction
        tarp_idx = np.flatnonzero(tarp_mask)[tarp_keep]
        tarp_z = Z[tarp_idx] + cfg.tarp_height + rng.normal(0, cfg.noise_z * 0.5, size=len(tarp_idx))
        tarp = np.column_stack((
            np.clip(X[tarp_idx] + rng.normal(0, cfg.noise_xy * 0.6, size=len(tarp_idx)), 0, cfg.area),
            np.clip(Y[tarp_idx] + rng.normal(0, cfg.noise_xy * 0.6, size=len(tarp_idx)), 0, cfg.area),
            tarp_z,
        ))
        blocks.append(tarp)

    points = np.vstack(blocks)
    out_path = Path(cfg.output_name).resolve()
    o3d.io.write_point_cloud(str(out_path), cloud_from_points(points))
    print(f"Saved {out_path.name} with {len(points):,} points")
    return out_path


def estimate_median_spacing(pcd: o3d.geometry.PointCloud) -> float:
    pts = np.asarray(pcd.points)
    if len(pts) < 2:
        raise ValueError("Point cloud needs at least 2 points.")

    tree = o3d.geometry.KDTreeFlann(pcd)
    sample_size = min(5000, len(pts))
    sample = np.random.choice(len(pts), sample_size, replace=False)
    dists = []
    for i in sample:
        _, idx, _ = tree.search_knn_vector_3d(pts[i], 2)
        if len(idx) == 2:
            dists.append(np.linalg.norm(pts[i] - pts[idx[1]]))
    if not dists:
        raise ValueError("Could not estimate point spacing.")
    return float(np.median(dists))


def robust_z_clip(points: np.ndarray, mad_mult: float) -> np.ndarray:
    z = points[:, 2]
    z_med = float(np.median(z))
    mad = float(np.median(np.abs(z - z_med)))
    if mad <= 1e-9:
        return points
    robust_sigma = 1.4826 * mad
    mask = np.abs(z - z_med) <= mad_mult * robust_sigma
    clipped = points[mask]
    return clipped if len(clipped) else points


def preclean_point_cloud(
    pcd: o3d.geometry.PointCloud,
    voxel: float,
    cfg: TerrainConfig,
) -> o3d.geometry.PointCloud:
    cloud = pcd

    if cfg.use_statistical_outlier and len(cloud.points) > cfg.stat_nb_neighbors:
        cloud, _ = cloud.remove_statistical_outlier(
            nb_neighbors=cfg.stat_nb_neighbors,
            std_ratio=cfg.stat_std_ratio,
        )

    if cfg.use_radius_outlier and len(cloud.points) > cfg.radius_nb_points:
        radius = max(voxel * cfg.radius_mult, 1e-6)
        cloud, _ = cloud.remove_radius_outlier(
            nb_points=cfg.radius_nb_points,
            radius=radius,
        )

    pts = np.asarray(cloud.points)
    if len(pts) == 0:
        return cloud
    pts = robust_z_clip(pts, cfg.robust_z_clip_mad)
    return cloud_from_points(pts)


def enforce_slope_masked(Z: np.ndarray, valid_mask: np.ndarray, max_slope: float, iterations: int = 10) -> np.ndarray:
    out = Z.copy()
    for _ in range(iterations):
        for y in range(out.shape[0]):
            for x in range(out.shape[1]):
                if not valid_mask[y, x]:
                    continue
                v = out[y, x]
                if np.isnan(v):
                    continue
                if y > 0 and valid_mask[y - 1, x]:
                    out[y - 1, x] = min(out[y - 1, x], v + max_slope) if not np.isnan(out[y - 1, x]) else out[y - 1, x]
                    out[y, x] = min(out[y, x], out[y - 1, x] + max_slope) if not np.isnan(out[y - 1, x]) else out[y, x]
                if x > 0 and valid_mask[y, x - 1]:
                    out[y, x - 1] = min(out[y, x - 1], v + max_slope) if not np.isnan(out[y, x - 1]) else out[y, x - 1]
                    out[y, x] = min(out[y, x], out[y, x - 1] + max_slope) if not np.isnan(out[y, x - 1]) else out[y, x]
    return out


def fill_holes_nearest(Z: np.ndarray, valid_mask: np.ndarray, max_dist_cells: int) -> np.ndarray:
    missing = valid_mask & np.isnan(Z)
    if not np.any(missing):
        return Z
    known = valid_mask & ~np.isnan(Z)
    if not np.any(known):
        raise ValueError("No valid grid cells found.")
    dist, (iy_near, ix_near) = distance_transform_edt(~known, return_indices=True)
    fill_ok = missing & (dist <= max_dist_cells)
    Z2 = Z.copy()
    Z2[fill_ok] = Z[iy_near[fill_ok], ix_near[fill_ok]]
    return Z2


def masked_gaussian_smooth(Z: np.ndarray, valid_mask: np.ndarray, sigma: float, passes: int = 1) -> np.ndarray:
    if sigma <= 0:
        return Z
    out = Z.copy()
    weights = valid_mask.astype(np.float64)
    for _ in range(max(1, passes)):
        src = np.where(valid_mask, out, 0.0)
        num = gaussian_filter(src, sigma=sigma)
        den = gaussian_filter(weights, sigma=sigma)
        smoothed = np.divide(num, den, out=np.zeros_like(num), where=den > 1e-9)
        out = np.where(valid_mask, smoothed, np.nan)
    return out


def despike_grid(Z: np.ndarray, valid_mask: np.ndarray, threshold: float, window: int) -> np.ndarray:
    if threshold <= 0:
        return Z
    work = Z.copy()
    fill_value = float(np.nanmedian(work[valid_mask]))
    tmp = np.where(valid_mask, work, fill_value)
    win = max(3, window)
    if win % 2 == 0:
        win += 1
    local_med = median_filter(tmp, size=win, mode="nearest")
    delta = tmp - local_med
    spike_mask = valid_mask & (np.abs(delta) > threshold)
    if np.any(spike_mask):
        work[spike_mask] = local_med[spike_mask]
    return work


def suppress_thin_ridges(
    Z: np.ndarray,
    valid_mask: np.ndarray,
    ridge_height_threshold: float,
    ridge_window: int,
    ridge_min_component_cells: int,
) -> np.ndarray:
    if ridge_height_threshold <= 0:
        return Z
    work = Z.copy()
    fill_value = float(np.nanmedian(work[valid_mask]))
    tmp = np.where(valid_mask, work, fill_value)
    win = max(3, ridge_window)
    if win % 2 == 0:
        win += 1
    local_bg = median_filter(tmp, size=win, mode="nearest")
    ridge_mask = valid_mask & ((tmp - local_bg) > ridge_height_threshold)
    labels, count, sizes = _connected_components(ridge_mask)
    if count == 0:
        return work

    # Remove both small ridges (spurious walls) and narrow components that are likely artifacts.
    replace_mask = np.zeros_like(ridge_mask)
    for label_id in range(1, count + 1):
        comp = labels == label_id
        n = int(sizes[label_id])
        if n == 0:
            continue
        ys, xs = np.where(comp)
        h = int(ys.max() - ys.min() + 1)
        w = int(xs.max() - xs.min() + 1)
        thinness = n / max(1, h * w)  # low fill ratio -> thin wall/ridge
        if n <= ridge_min_component_cells or thinness < 0.45:
            replace_mask |= comp

    if np.any(replace_mask):
        work[replace_mask] = local_bg[replace_mask]
    return work


def clamp_local_relief(Z: np.ndarray, valid_mask: np.ndarray, max_relief: float, window: int = 5) -> np.ndarray:
    if max_relief <= 0:
        return Z
    work = Z.copy()
    fill_value = float(np.nanmedian(work[valid_mask]))
    tmp = np.where(valid_mask, work, fill_value)
    win = max(3, window)
    if win % 2 == 0:
        win += 1
    local_med = median_filter(tmp, size=win, mode="nearest")
    tmp = np.clip(tmp, local_med - max_relief, local_med + max_relief)
    return np.where(valid_mask, tmp, np.nan)


def _connected_components(mask: np.ndarray) -> tuple[np.ndarray, int, np.ndarray]:
    labels = np.zeros(mask.shape, dtype=np.int32)
    sizes = [0]
    current = 0
    h, w = mask.shape
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or labels[y, x] != 0:
                continue
            current += 1
            stack = [(y, x)]
            labels[y, x] = current
            count = 0
            while stack:
                cy, cx = stack.pop()
                count += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and labels[ny, nx] == 0:
                        labels[ny, nx] = current
                        stack.append((ny, nx))
            sizes.append(count)
    return labels, current, np.asarray(sizes, dtype=np.int32)


def suppress_elevated_cover_patches(Z: np.ndarray, valid_mask: np.ndarray, cfg: TerrainConfig) -> np.ndarray:
    if not cfg.suppress_elevated_covers:
        return Z

    work = Z.copy()
    fill_value = float(np.nanmedian(work[valid_mask]))
    tmp = np.where(valid_mask, work, fill_value)

    win = max(3, cfg.cover_median_window)
    if win % 2 == 0:
        win += 1
    local_bg = median_filter(tmp, size=win, mode="nearest")
    elevated = valid_mask & ((tmp - local_bg) > cfg.cover_height_threshold)
    labels, count, sizes = _connected_components(elevated)
    if count == 0:
        return work

    patch_mask = np.zeros_like(elevated)
    for label_id in range(1, count + 1):
        if sizes[label_id] >= cfg.cover_min_cells:
            patch_mask |= labels == label_id

    if not np.any(patch_mask):
        return work

    work[patch_mask] = np.nan
    work = fill_holes_nearest(work, valid_mask, cfg.max_hole_distance_cells)
    return work


def grid_lower_envelope(
    points: np.ndarray,
    voxel: float,
    cfg: TerrainConfig,
) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    if len(points) == 0:
        raise ValueError("No points to grid.")

    xmin, ymin = points[:, 0].min(), points[:, 1].min()
    xmax, ymax = points[:, 0].max(), points[:, 1].max()

    cell = voxel * cfg.grid_scale
    if cell <= 0:
        raise ValueError("Invalid cell size.")

    nx = int((xmax - xmin) / cell) + 1
    ny = int((ymax - ymin) / cell) + 1
    if nx <= 2 or ny <= 2:
        raise ValueError(f"Grid too small: nx={nx}, ny={ny}")

    valid_mask = np.ones((ny, nx), dtype=bool)
    pad = 2
    if ny > 2 * pad and nx > 2 * pad:
        valid_mask[:pad, :] = False
        valid_mask[-pad:, :] = False
        valid_mask[:, :pad] = False
        valid_mask[:, -pad:] = False

    ix = np.floor((points[:, 0] - xmin) / cell).astype(np.int32)
    iy = np.floor((points[:, 1] - ymin) / cell).astype(np.int32)
    in_bounds = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    ix, iy = ix[in_bounds], iy[in_bounds]
    zvals = points[:, 2][in_bounds]

    in_mask = valid_mask[iy, ix]
    ix, iy, zvals = ix[in_mask], iy[in_mask], zvals[in_mask]
    if len(zvals) == 0:
        raise ValueError("No points inside processing mask.")

    cell_id = iy.astype(np.int64) * nx + ix.astype(np.int64)
    order = np.argsort(cell_id)
    cell_id = cell_id[order]
    zvals = zvals[order]

    uniq, start = np.unique(cell_id, return_index=True)
    start = np.append(start, len(cell_id))

    Z = np.full((ny, nx), np.nan, dtype=np.float32)

    for k, cid in enumerate(uniq):
        y = int(cid // nx)
        x = int(cid % nx)
        zs = np.sort(zvals[start[k]:start[k + 1]])
        if zs.size == 0:
            continue
        cut = max(3, int(np.ceil(zs.size * (cfg.low_percentile / 100.0))))
        low = zs[:cut]
        # If the very lowest point is an isolated outlier, skip it and use the next
        # continuous low cluster so we don't create needle-like pits/spikes.
        start_idx = 0
        cluster: list[float] = []
        while start_idx < len(low):
            cluster = [float(low[start_idx])]
            for v in low[start_idx + 1:]:
                if v - cluster[-1] <= cfg.continuity_jump:
                    cluster.append(float(v))
                else:
                    break
            if len(cluster) >= cfg.low_cluster_min_points or start_idx >= len(low) - cfg.low_cluster_min_points:
                break
            start_idx += 1
        Z[y, x] = float(np.median(cluster))

    Z = fill_holes_nearest(Z, valid_mask, cfg.max_hole_distance_cells)
    if np.isnan(Z).all():
        raise ValueError("All grid cells are NaN after lower-envelope extraction.")

    Z = suppress_elevated_cover_patches(Z, valid_mask, cfg)
    Z = despike_grid(Z, valid_mask, cfg.despike_height_threshold, cfg.despike_window)
    Z = despike_grid(Z, valid_mask, cfg.despike_height_threshold * 0.85, max(5, cfg.despike_window + 2))
    Z = suppress_thin_ridges(
        Z,
        valid_mask,
        cfg.ridge_height_threshold,
        cfg.ridge_window,
        cfg.ridge_min_component_cells,
    )
    if np.isnan(Z).any():
        Z = np.where(np.isnan(Z), np.nanmedian(Z), Z)

    Z = enforce_slope_masked(Z, valid_mask, cfg.max_slope)
    Z = masked_gaussian_smooth(Z, valid_mask, cfg.smooth_sigma, cfg.smooth_passes)
    Z = clamp_local_relief(Z, valid_mask, cfg.final_relief_clamp, window=5)
    Z = despike_grid(Z, valid_mask, cfg.despike_height_threshold * 0.8, cfg.despike_window)
    return Z, valid_mask, xmin, ymin, cell


def build_mesh_from_grid(
    Z: np.ndarray,
    valid_mask: np.ndarray,
    xmin: float,
    ymin: float,
    cell: float,
) -> o3d.geometry.TriangleMesh:
    verts = []
    idx_map = {}
    idx = 0
    ny, nx = Z.shape
    for y in range(ny):
        for x in range(nx):
            if not valid_mask[y, x] or np.isnan(Z[y, x]):
                continue
            verts.append([xmin + x * cell, ymin + y * cell, float(Z[y, x])])
            idx_map[(y, x)] = idx
            idx += 1

    tris = []
    for y in range(ny - 1):
        for x in range(nx - 1):
            a = idx_map.get((y, x))
            b = idx_map.get((y, x + 1))
            c = idx_map.get((y + 1, x))
            d = idx_map.get((y + 1, x + 1))
            if None in (a, b, c, d):
                continue
            tris.append([a, b, c])
            tris.append([b, d, c])

    mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.asarray(verts, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.asarray(tris, dtype=np.int32)),
    )
    mesh.compute_vertex_normals()
    vz = np.asarray(mesh.vertices)[:, 2]
    mesh.vertex_colors = o3d.utility.Vector3dVector(terrain_colormap(vz))
    return mesh


def terrain_colormap(z: np.ndarray) -> np.ndarray:
    z = (z - z.min()) / (z.max() - z.min() + 1e-12)
    c = np.zeros((len(z), 3))
    for i, t in enumerate(z):
        if t < 0.25:
            c[i] = [0.05, 0.25, 0.85]
        elif t < 0.5:
            c[i] = [0.05, 0.65, 0.35]
        elif t < 0.75:
            c[i] = [0.90, 0.85, 0.15]
        else:
            c[i] = [0.88, 0.25, 0.15]
    return c


def sample_grid_height(
    x: np.ndarray,
    y: np.ndarray,
    Z: np.ndarray,
    valid_mask: np.ndarray,
    xmin: float,
    ymin: float,
    cell: float,
) -> np.ndarray:
    ix = np.floor((x - xmin) / cell).astype(np.int32)
    iy = np.floor((y - ymin) / cell).astype(np.int32)
    inside = (
        (ix >= 0) & (ix < Z.shape[1]) &
        (iy >= 0) & (iy < Z.shape[0]) &
        valid_mask[np.clip(iy, 0, Z.shape[0] - 1), np.clip(ix, 0, Z.shape[1] - 1)]
    )
    out = np.full(len(x), np.nan, dtype=np.float64)
    out[inside] = Z[iy[inside], ix[inside]]
    return out


def extract_near_ground_points(
    points: np.ndarray,
    meta: tuple[np.ndarray, np.ndarray, float, float, float],
    keep_height: float,
) -> np.ndarray:
    Z, valid_mask, xmin, ymin, cell = meta
    z_ground = sample_grid_height(points[:, 0], points[:, 1], Z, valid_mask, xmin, ymin, cell)
    keep = ~np.isnan(z_ground) & (points[:, 2] <= z_ground + keep_height)
    return points[keep]


def build_surfaces(
    pcd: o3d.geometry.PointCloud,
    cfg: TerrainConfig,
) -> tuple[list[o3d.geometry.TriangleMesh], list[tuple[np.ndarray, np.ndarray, float, float, float]], float]:
    pts = np.asarray(pcd.points)
    if len(pts) == 0:
        raise ValueError("Loaded point cloud is empty.")
    median_spacing = estimate_median_spacing(pcd)
    print(f"Median spacing: {median_spacing:.6f}")

    surfaces = []
    metas = []
    for i in range(cfg.num_levels):
        factor = cfg.base_factor + i * cfg.step_factor
        voxel = max(1e-6, factor * median_spacing)
        cloud_in = pcd.voxel_down_sample(voxel)
        cloud_in = preclean_point_cloud(cloud_in, voxel, cfg)
        arr = np.asarray(cloud_in.points)
        print(f"Level {i+1}: voxel={voxel:.6f}, cleaned points={len(arr):,}")
        meta = grid_lower_envelope(arr, voxel, cfg)
        mesh = build_mesh_from_grid(*meta)
        surfaces.append(mesh)
        metas.append(meta)
    return surfaces, metas, median_spacing


def save_outputs(
    input_path: Path,
    pcd: o3d.geometry.PointCloud,
    surfaces: list[o3d.geometry.TriangleMesh],
    metas: list[tuple[np.ndarray, np.ndarray, float, float, float]],
    cfg: TerrainConfig,
) -> None:
    stem = input_path.stem
    out_root = Path(f"{stem}_outputs")
    out_root.mkdir(exist_ok=True)

    if cfg.save_previews:
        out_dir = out_root / "previews"
        out_dir.mkdir(exist_ok=True)
        for i, mesh in enumerate(surfaces, start=1):
            mesh_path = out_dir / f"{stem}_terrain_level_{i}.ply"
            o3d.io.write_triangle_mesh(str(mesh_path), mesh)
        print(f"Saved {len(surfaces)} terrain preview mesh(es) to {out_dir.resolve()}")

    if cfg.save_mesh and surfaces:
        final_path = out_root / f"{stem}_terrain_final.ply"
        o3d.io.write_triangle_mesh(str(final_path), surfaces[0])
        print(f"Saved terrain mesh: {final_path.resolve()}")

    if cfg.save_ground_cloud and metas:
        ground_points = extract_near_ground_points(np.asarray(pcd.points), metas[0], cfg.ground_keep_height)
        ground_path = out_root / f"{stem}_ground_filtered.ply"
        o3d.io.write_point_cloud(str(ground_path), cloud_from_points(ground_points))
        print(f"Saved near-ground filtered cloud: {ground_path.resolve()} ({len(ground_points):,} points)")

    summary_path = out_root / "run_summary.txt"
    summary_lines = [
        f"input={input_path.resolve()}",
        f"points={len(pcd.points)}",
        f"levels={cfg.num_levels}",
        f"cover_suppression={cfg.suppress_elevated_covers}",
        f"statistical_outlier={cfg.use_statistical_outlier}",
        f"radius_outlier={cfg.use_radius_outlier}",
        f"ground_keep_height={cfg.ground_keep_height}",
        f"smooth_sigma={cfg.smooth_sigma}",
        f"smooth_passes={cfg.smooth_passes}",
        f"despike_height_threshold={cfg.despike_height_threshold}",
        f"ridge_height_threshold={cfg.ridge_height_threshold}",
        f"final_relief_clamp={cfg.final_relief_clamp}",
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="ascii")
    print(f"Saved run summary: {summary_path.resolve()}")


def maybe_visualize(
    pcd: o3d.geometry.PointCloud,
    surfaces: list[o3d.geometry.TriangleMesh],
    cfg: TerrainConfig,
) -> None:
    if not cfg.animate or not surfaces:
        return

    vis = o3d.visualization.Visualizer()
    vis.create_window("LiDAR Terrain", 1400, 900)
    opt = vis.get_render_option()
    opt.mesh_show_back_face = True
    opt.background_color = np.asarray([1.0, 1.0, 1.0])

    live = surfaces[0]
    vis.add_geometry(live)
    if cfg.overlay_points:
        overlay = o3d.geometry.PointCloud(pcd)
        overlay.paint_uniform_color([0.4, 0.4, 0.4])
        vis.add_geometry(overlay)

    ctr = vis.get_view_control()
    bbox = live.get_axis_aligned_bounding_box()
    ctr.set_lookat(bbox.get_center())
    ctr.set_front([0, -0.35, -1.0])
    ctr.set_up([0, 1, 0])
    ctr.set_zoom(0.45)

    seq = list(range(len(surfaces))) + list(range(len(surfaces) - 2, 0, -1)) if len(surfaces) > 1 else [0]
    idx = 0
    import time
    last = time.time()
    while True:
        if not vis.poll_events():
            break
        if time.time() - last > 0.8 and len(surfaces) > 1:
            vis.remove_geometry(live, reset_bounding_box=False)
            live = surfaces[seq[idx % len(seq)]]
            vis.add_geometry(live, reset_bounding_box=False)
            idx += 1
            last = time.time()
        vis.update_renderer()
    vis.destroy_window()


def process_point_cloud(path: Path, cfg: TerrainConfig) -> None:
    print(f"\nLoading point cloud: {path}")
    pcd = load_point_cloud(path)
    if len(pcd.points) == 0:
        raise ValueError("Loaded point cloud is empty.")
    print(f"Loaded {len(pcd.points):,} points")

    surfaces, metas, _ = build_surfaces(pcd, cfg)
    save_outputs(path, pcd, surfaces, metas, cfg)
    maybe_visualize(pcd, surfaces, cfg)
    print("Done.")


def build_point_cloud_products(
    path: Path,
    cfg: TerrainConfig,
    save_outputs_enabled: bool = True,
    visualize: bool = False,
) -> tuple[o3d.geometry.PointCloud, list[o3d.geometry.TriangleMesh], list[tuple[np.ndarray, np.ndarray, float, float, float]]]:
    print(f"\nLoading point cloud: {path}")
    pcd = load_point_cloud(path)
    if len(pcd.points) == 0:
        raise ValueError(f"Loaded point cloud is empty: {path}")
    print(f"Loaded {len(pcd.points):,} points")
    surfaces, metas, _ = build_surfaces(pcd, cfg)
    if save_outputs_enabled:
        save_outputs(path, pcd, surfaces, metas, cfg)
    if visualize:
        maybe_visualize(pcd, surfaces, cfg)
    return pcd, surfaces, metas


def try_parse_date_from_filename(name: str) -> tuple[Optional[date], Optional[str]]:
    patterns = [
        r"(?<!\d)(20\d{2})[-_](\d{2})[-_](\d{2})(?!\d)",
        r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, name):
            y, mo, d = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            try:
                return date(y, mo, d), m.group(0)
            except ValueError:
                continue
    return None, None


def choose_folder_with_point_clouds() -> Path:
    while True:
        raw = input(f"Enter folder path with scans [default {Path.cwd()}]: ").strip()
        folder = Path(raw).expanduser() if raw else Path.cwd()
        if folder.is_dir():
            files = list_point_cloud_files(folder)
            if files:
                return folder.resolve()
            print("No supported point-cloud files found in that folder.")
            continue
        print("Folder not found.")


def resample_meta_to_reference(
    meta_src: tuple[np.ndarray, np.ndarray, float, float, float],
    meta_ref: tuple[np.ndarray, np.ndarray, float, float, float],
) -> tuple[np.ndarray, np.ndarray]:
    Zr, mask_r, xmin_r, ymin_r, cell_r = meta_ref
    ny, nx = Zr.shape
    yy, xx = np.indices((ny, nx))
    xs = xmin_r + xx.astype(np.float64) * cell_r
    ys = ymin_r + yy.astype(np.float64) * cell_r
    Zs, mask_s, xmin_s, ymin_s, cell_s = meta_src
    sampled = sample_grid_height(xs.ravel(), ys.ravel(), Zs, mask_s, xmin_s, ymin_s, cell_s).reshape(ny, nx)
    valid = mask_r & ~np.isnan(Zr) & ~np.isnan(sampled)
    return sampled, valid


def detect_excavation_mask_from_series(
    aligned_surfaces: list[np.ndarray],
    common_valid: np.ndarray,
    cfg: TerrainConfig,
) -> tuple[np.ndarray, np.ndarray]:
    win = max(5, cfg.excavation_detect_window)
    if win % 2 == 0:
        win += 1

    union_mask = np.zeros_like(common_valid, dtype=bool)
    depth_stack = []
    fill_value = 0.0
    if np.any(common_valid):
        fill_value = float(np.nanmedian(np.stack([np.where(common_valid, z, np.nan) for z in aligned_surfaces])))

    for Z in aligned_surfaces:
        tmp = np.where(common_valid, Z, fill_value)
        bg = median_filter(tmp, size=win, mode="nearest")
        depression = np.maximum(0.0, bg - tmp)
        depth_stack.append(depression)
        mask = common_valid & (depression >= cfg.excavation_detect_threshold)
        labels, count, sizes = _connected_components(mask)
        keep = np.zeros_like(mask)
        for label_id in range(1, count + 1):
            if sizes[label_id] >= cfg.excavation_min_cells:
                keep |= labels == label_id
        union_mask |= keep

    if not np.any(union_mask):
        # Fallback: use any notable depression, even if small, so analysis still runs.
        union_mask = common_valid & (np.max(np.stack(depth_stack), axis=0) >= max(0.03, cfg.excavation_detect_threshold * 0.5))

    max_depression = np.max(np.stack(depth_stack), axis=0)
    return union_mask, max_depression


def format_optional_date(d: Optional[date]) -> str:
    return d.isoformat() if d else "UNKNOWN"


def pct_bar(pct: float, width: int = 24) -> str:
    p = max(0.0, min(100.0, float(pct)))
    filled = int(round((p / 100.0) * width))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def choose_batch_output_folder(folder: Path) -> tuple[Path, bool]:
    existing = sorted([p for p in folder.glob("batch_volume_analysis_*") if p.is_dir()])
    if existing and ask_yes_no("Add this run to an existing report folder?", default=False):
        print("\nExisting report folders:")
        for i, p in enumerate(existing, start=1):
            print(f"  {i}. {p.name}")
        idx = ask_int("Choose report folder", 1, len(existing), default=len(existing))
        return existing[idx - 1], True

    out = folder / f"batch_volume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(exist_ok=True)
    return out, False


def write_csv_rows(path: Path, rows: list[dict], append: bool) -> Path:
    if not rows:
        return path
    fieldnames = list(rows[0].keys())
    target = path
    mode = "a" if append and target.exists() else "w"

    if append and target.exists():
        with target.open("r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            old_header = next(reader, None)
        if old_header is not None and old_header != fieldnames:
            target = path.with_name(f"{path.stem}_v2{path.suffix}")
            mode = "a" if target.exists() else "w"

    with target.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)
    return target


def confirm_or_adjust_order(records: list[dict]) -> list[dict]:
    print("\nDetected scan order:")
    for i, rec in enumerate(records, start=1):
        token = rec.get("date_token") or "-"
        print(f"  {i}. {rec['path'].name}  | date={format_optional_date(rec.get('scan_date'))} | token={token}")
    if ask_yes_no("Is this order correct?", default=True):
        return records

    print("Enter a manual order as comma-separated indices (example: 3,1,2).")
    print("If date parsing is wrong, rename files to include YYYYMMDD or YYYY-MM-DD anywhere in the filename.")
    while True:
        raw = input("Manual order: ").strip()
        try:
            order = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            order = []
        if len(order) == len(records) and sorted(order) == list(range(1, len(records) + 1)):
            return [records[i - 1] for i in order]
        print("Invalid order. Use each index exactly once.")


def discover_final_meshes(directory: Path) -> list[dict]:
    meshes = sorted(directory.glob("*_outputs/*_terrain_final.ply"))
    records: list[dict] = []
    for mesh in meshes:
        d, tok = try_parse_date_from_filename(mesh.name)
        if d is None:
            d2, tok2 = try_parse_date_from_filename(mesh.parent.name)
            if d2 is not None:
                d, tok = d2, tok2
        records.append({"path": mesh.resolve(), "scan_date": d, "date_token": tok})
    records.sort(key=lambda r: (r["scan_date"] is None, r["scan_date"] or date.max, r["path"].name.lower()))
    return records


def build_excavation_boundary_line_set(
    meta_ref: tuple[np.ndarray, np.ndarray, float, float, float],
    excavation_mask: np.ndarray,
) -> Optional[o3d.geometry.LineSet]:
    Z, valid_mask, xmin, ymin, cell = meta_ref
    mask = excavation_mask & valid_mask & ~np.isnan(Z)
    if not np.any(mask):
        return None

    z_vals = Z[mask]
    z_min = float(np.min(z_vals))
    z_max = float(np.max(z_vals))
    z_offset = max(0.01 * (z_max - z_min), 0.15 * cell, 1e-4)
    z_line = float(np.median(z_vals) + z_offset)

    point_idx: dict[tuple[float, float], int] = {}
    points_xy: list[tuple[float, float]] = []
    lines: list[list[int]] = []

    def get_idx(px: float, py: float) -> int:
        key = (round(px, 6), round(py, 6))
        idx = point_idx.get(key)
        if idx is None:
            idx = len(points_xy)
            point_idx[key] = idx
            points_xy.append((px, py))
        return idx

    ny, nx = mask.shape
    for y in range(ny):
        for x in range(nx):
            if not mask[y, x]:
                continue
            x0 = xmin + x * cell
            x1 = x0 + cell
            y0 = ymin + y * cell
            y1 = y0 + cell

            if y == 0 or not mask[y - 1, x]:
                lines.append([get_idx(x0, y0), get_idx(x1, y0)])
            if y == ny - 1 or not mask[y + 1, x]:
                lines.append([get_idx(x0, y1), get_idx(x1, y1)])
            if x == 0 or not mask[y, x - 1]:
                lines.append([get_idx(x0, y0), get_idx(x0, y1)])
            if x == nx - 1 or not mask[y, x + 1]:
                lines.append([get_idx(x1, y0), get_idx(x1, y1)])

    if not lines or not points_xy:
        return None

    points = np.array([[px, py, z_line] for px, py in points_xy], dtype=np.float64)
    line_set = o3d.geometry.LineSet(
        o3d.utility.Vector3dVector(points),
        o3d.utility.Vector2iVector(np.asarray(lines, dtype=np.int32)),
    )
    colors = np.tile(np.array([[0.85, 0.15, 0.15]], dtype=np.float64), (len(lines), 1))
    line_set.colors = o3d.utility.Vector3dVector(colors)
    return line_set


def compute_masked_volume_metrics(
    Za: np.ndarray,
    Zb: np.ndarray,
    mask: np.ndarray,
    cell: float,
) -> dict:
    valid = mask & ~np.isnan(Za) & ~np.isnan(Zb)
    area = float(cell * cell)
    if not np.any(valid):
        return {
            "cell_area": area,
            "cells": 0,
            "area_total": 0.0,
            "signed": 0.0,
            "removed": 0.0,
            "filled": 0.0,
            "removed_area": 0.0,
            "filled_area": 0.0,
        }
    dz = Zb - Za  # positive means later surface is higher
    signed = float(np.sum(dz[valid]) * area)
    removed_mask = valid & (Za > Zb)
    filled_mask = valid & (Zb > Za)
    removed = float(np.sum(np.maximum(0.0, Za - Zb)[valid]) * area)  # later lower than earlier
    filled = float(np.sum(np.maximum(0.0, Zb - Za)[valid]) * area)   # later higher than earlier
    return {
        "cell_area": area,
        "cells": int(np.count_nonzero(valid)),
        "area_total": float(np.count_nonzero(valid) * area),
        "signed": signed,
        "removed": removed,
        "filled": filled,
        "removed_area": float(np.count_nonzero(removed_mask) * area),
        "filled_area": float(np.count_nonzero(filled_mask) * area),
    }


def animate_chronological_finals(
    processed: list[dict],
    consecutive_rows: list[dict],
    delay_seconds: float = 1.0,
    boundary_line: Optional[o3d.geometry.LineSet] = None,
) -> None:
    delay_seconds = max(0.2, float(delay_seconds))
    meshes: list[o3d.geometry.TriangleMesh] = []
    labels: list[str] = []
    for rec in processed:
        mesh_path = Path(rec["terrain_final_path"])
        if not mesh_path.exists():
            continue
        mesh = o3d.io.read_triangle_mesh(str(mesh_path))
        if len(mesh.vertices) == 0:
            continue
        mesh.compute_vertex_normals()
        meshes.append(mesh)
        labels.append(f"{format_optional_date(rec.get('scan_date'))} | {rec['path'].name}")

    if len(meshes) < 2:
        print("Timeline view skipped: need at least 2 valid terrain_final meshes.")
        return

    print("\nOpening timeline viewer. Close the window to stop.")
    vis = o3d.visualization.Visualizer()
    vis.create_window("Chronological Terrain Timeline", 1400, 900)
    opt = vis.get_render_option()
    opt.mesh_show_back_face = True
    opt.background_color = np.asarray([1.0, 1.0, 1.0])

    idx = 0
    live = meshes[idx]
    vis.add_geometry(live)
    if boundary_line is not None:
        vis.add_geometry(boundary_line, reset_bounding_box=False)
    bbox = live.get_axis_aligned_bounding_box()
    ctr = vis.get_view_control()
    ctr.set_lookat(bbox.get_center())
    ctr.set_front([0, -0.35, -1.0])
    ctr.set_up([0, 1, 0])
    ctr.set_zoom(0.45)

    import time
    last = 0.0
    shown = -1
    while True:
        if not vis.poll_events():
            break
        now = time.time()
        if now - last >= delay_seconds:
            vis.remove_geometry(live, reset_bounding_box=False)
            live = meshes[idx]
            vis.add_geometry(live, reset_bounding_box=False)
            vis.update_renderer()

            if idx != shown:
                print(f"\nFrame {idx + 1}/{len(meshes)}: {labels[idx]}")
                if idx > 0 and idx - 1 < len(consecutive_rows):
                    step = consecutive_rows[idx - 1]
                    gap_txt = f"{step['day_gap']} days later" if step.get("day_gap") is not None else "date gap unknown"
                    daily_pct = step.get("daily_share_pct", None)
                    cumulative_pct = step.get("cumulative_progress_after_pct", None)
                    from_date = step.get("from_date", "UNKNOWN")
                    to_date = step.get("to_date", "UNKNOWN")
                    if daily_pct is not None:
                        cum_txt = f", cumulative {cumulative_pct:.1f}%" if cumulative_pct is not None else ""
                        print(f"  {to_date} ({gap_txt}) -> since {from_date}: daily share {daily_pct:.1f}%{cum_txt}")
                    else:
                        print(f"  {gap_txt}")
                shown = idx

            idx = (idx + 1) % len(meshes)
            last = now
    vis.destroy_window()


def view_all_finals_in_directory(directory: Path, delay_seconds: float = 1.0) -> None:
    records = discover_final_meshes(directory)
    if not records:
        print(f"No *_terrain_final.ply files found in output folders under {directory.resolve()}")
        return
    if len(records) == 1:
        print("Only one final mesh found; need at least two for timeline playback.")
        return

    print(f"\nFound {len(records)} final terrain meshes in {directory.resolve()}")
    records = confirm_or_adjust_order(records)

    processed = []
    for rec in records:
        processed.append({
            "path": rec["path"],
            "scan_date": rec.get("scan_date"),
            "terrain_final_path": rec["path"],
        })

    consecutive_rows = []
    for i in range(1, len(records)):
        d1 = records[i - 1].get("scan_date")
        d2 = records[i].get("scan_date")
        day_gap = (d2 - d1).days if (d1 is not None and d2 is not None) else None
        consecutive_rows.append({
            "from_date": format_optional_date(d1),
            "to_date": format_optional_date(d2),
            "day_gap": day_gap,
            "removed_area_since_prev": None,
            "removed_since_prev": None,
            "cumulative_progress_after_pct": None,
        })

    animate_chronological_finals(processed, consecutive_rows, delay_seconds=delay_seconds)


def run_batch_volume_timeseries(
    folder: Path,
    cfg: TerrainConfig,
    view_timeline: bool = False,
    timeline_delay: float = 1.0,
) -> None:
    files = list_point_cloud_files(folder)
    if len(files) < 2:
        raise ValueError("Need at least 2 supported point-cloud files in the folder for batch comparison.")

    records: list[dict] = []
    for p in files:
        d, tok = try_parse_date_from_filename(p.name)
        records.append({"path": p.resolve(), "scan_date": d, "date_token": tok})

    # Sort by parsed date first, then name. Unknown dates go to end.
    records.sort(key=lambda r: (r["scan_date"] is None, r["scan_date"] or date.max, r["path"].name.lower()))
    records = confirm_or_adjust_order(records)

    print("\nProcessing scans and building terrain surfaces...")
    batch_out, append_mode = choose_batch_output_folder(folder)
    run_tag = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    processed = []
    for i, rec in enumerate(records, start=1):
        print(f"\n[{i}/{len(records)}] {rec['path'].name}")
        pcd, surfaces, metas = build_point_cloud_products(rec["path"], cfg, save_outputs_enabled=True, visualize=False)
        rec2 = dict(rec)
        rec2["pcd_points"] = len(pcd.points)
        rec2["surface_meta"] = metas[0]  # terrain_final uses level 1
        rec2["terrain_final_path"] = (
            rec["path"].parent / f"{rec['path'].stem}_outputs" / f"{rec['path'].stem}_terrain_final.ply"
        ).resolve()
        processed.append(rec2)

    ref_meta = processed[0]["surface_meta"]
    Z_ref, mask_ref, _, _, cell_ref = ref_meta
    aligned_surfaces = [Z_ref]
    common_valid = mask_ref & ~np.isnan(Z_ref)

    for rec in processed[1:]:
        Z_aligned, valid = resample_meta_to_reference(rec["surface_meta"], ref_meta)
        aligned_surfaces.append(Z_aligned)
        common_valid &= valid

    # Recompute baseline through same path so all scans share exact alignment treatment.
    aligned_surfaces[0], valid0 = resample_meta_to_reference(processed[0]["surface_meta"], ref_meta)
    common_valid &= valid0

    if not np.any(common_valid):
        raise ValueError("No overlapping valid cells across all scans on the reference grid.")

    excavation_mask, _max_depression = detect_excavation_mask_from_series(aligned_surfaces, common_valid, cfg)
    if not np.any(excavation_mask):
        print("Warning: Excavation mask auto-detection found no cells. Falling back to all common overlapping cells.")
        excavation_mask = common_valid.copy()

    # Build per-scan metrics (vs baseline) and consecutive metrics.
    baseline_Z = aligned_surfaces[0]
    per_scan_rows = []
    for rec, Z in zip(processed, aligned_surfaces):
        m = compute_masked_volume_metrics(baseline_Z, Z, excavation_mask, cell_ref)
        per_scan_rows.append({
            "run_tag": run_tag,
            "file": rec["path"].name,
            "date": format_optional_date(rec.get("scan_date")),
            "terrain_final": str(rec["terrain_final_path"]),
            "points": rec["pcd_points"],
            "signed_vs_first": m["signed"],
            "removed_vs_first": m["removed"],
            "filled_vs_first": m["filled"],
        })

    max_removed = max((row["removed_vs_first"] for row in per_scan_rows), default=0.0)
    for row in per_scan_rows:
        row["cumulative_progress_pct"] = (100.0 * row["removed_vs_first"] / max_removed) if max_removed > 1e-12 else 0.0

    consecutive_rows = []
    for i in range(1, len(processed)):
        m = compute_masked_volume_metrics(aligned_surfaces[i - 1], aligned_surfaces[i], excavation_mask, cell_ref)
        d1 = processed[i - 1].get("scan_date")
        d2 = processed[i].get("scan_date")
        day_gap = (d2 - d1).days if (d1 is not None and d2 is not None) else None
        consecutive_rows.append({
            "run_tag": run_tag,
            "from_file": processed[i - 1]["path"].name,
            "to_file": processed[i]["path"].name,
            "from_date": format_optional_date(processed[i - 1].get("scan_date")),
            "to_date": format_optional_date(processed[i].get("scan_date")),
            "signed_change": m["signed"],
            "removed_since_prev": m["removed"],
            "removed_area_since_prev": m["removed_area"],
            "filled_since_prev": m["filled"],
            "day_gap": day_gap,
            "cumulative_progress_after_pct": per_scan_rows[i]["cumulative_progress_pct"],
        })

    total_removed_since_start = float(sum(max(0.0, row["removed_since_prev"]) for row in consecutive_rows))
    for row in consecutive_rows:
        row["daily_share_pct"] = (
            100.0 * max(0.0, row["removed_since_prev"]) / total_removed_since_start
            if total_removed_since_start > 1e-12 else 0.0
        )

    # Save outputs
    excavation_cells = int(np.count_nonzero(excavation_mask))
    mask_points = np.column_stack(np.where(excavation_mask))
    if len(mask_points):
        yy = mask_points[:, 0]
        xx = mask_points[:, 1]
        _, _, xmin_r, ymin_r, cell_r = ref_meta
        mask_xyz = np.column_stack((
            xmin_r + xx * cell_r,
            ymin_r + yy * cell_r,
            aligned_surfaces[0][yy, xx],
        ))
        o3d.io.write_point_cloud(str(batch_out / "detected_excavation_mask_points.ply"), cloud_from_points(mask_xyz))

    per_scan_csv = write_csv_rows(batch_out / "per_scan_metrics.csv", per_scan_rows, append=append_mode)
    consecutive_csv = None
    if consecutive_rows:
        consecutive_csv = write_csv_rows(batch_out / "consecutive_differences.csv", consecutive_rows, append=append_mode)

    summary_lines = []
    summary_lines.append("LiDAR Excavation Batch Volume Report")
    summary_lines.append(f"Run tag: {run_tag}")
    summary_lines.append(f"Folder: {folder.resolve()}")
    summary_lines.append(f"Scans processed: {len(processed)}")
    summary_lines.append(f"Reference scan: {processed[0]['path'].name}")
    summary_lines.append(f"Excavation mask cells: {excavation_cells}")
    summary_lines.append("")
    summary_lines.append("Per-scan progress:")
    for row in per_scan_rows:
        summary_lines.append(
            f"- {row['date']} | {row['file']} | cumulative progress={row['cumulative_progress_pct']:.1f}%"
        )
    summary_lines.append("")
    summary_lines.append("Cumulative progress graph (unit-free percentage):")
    for row in per_scan_rows:
        summary_lines.append(
            f"- {row['date']} {pct_bar(row['cumulative_progress_pct'])} {row['cumulative_progress_pct']:.1f}%"
        )
    if consecutive_rows:
        summary_lines.append("")
        summary_lines.append("Daily digging (since previous scan):")
        for row in consecutive_rows:
            gap_txt = f"{row['day_gap']} days later" if row["day_gap"] is not None else "gap unknown"
            summary_lines.append(
                f"- {row['from_date']} -> {row['to_date']} ({gap_txt}) | "
                f"daily share={row['daily_share_pct']:.1f}% | cumulative={row['cumulative_progress_after_pct']:.1f}%"
            )
        summary_lines.append("")
        summary_lines.append("Daily share graph (% of total removed across all intervals):")
        for row in consecutive_rows:
            label = f"{row['from_date']}->{row['to_date']}"
            summary_lines.append(f"- {label} {pct_bar(row['daily_share_pct'])} {row['daily_share_pct']:.1f}%")
    summary_lines.append("")
    summary_lines.append("Notes:")
    summary_lines.append("- Progress is computed from level-1 terrain differences (same surface used for *_terrain_final.ply), resampled to the first scan grid.")
    summary_lines.append("- Percentages are unit-free and are the primary progress metric.")
    summary_lines.append("- 'Removed' means later scan terrain is lower than earlier scan inside the detected excavation region.")
    summary_lines.append("- If date parsing is wrong, rename files to include YYYYMMDD or YYYY-MM-DD in the filename.")

    report_path = batch_out / "batch_volume_report.txt"
    report_block = "\n".join(summary_lines) + "\n"
    if append_mode and report_path.exists():
        with report_path.open("a", encoding="utf-8") as f:
            f.write("\n" + ("=" * 72) + "\n")
            f.write(report_block)
    else:
        report_path.write_text(report_block, encoding="utf-8")

    graph_lines = []
    graph_lines.append("CUMULATIVE PROGRESS (% of max dug state)")
    for row in per_scan_rows:
        graph_lines.append(f"{row['date']} {pct_bar(row['cumulative_progress_pct'])} {row['cumulative_progress_pct']:.1f}%")
    if consecutive_rows:
        graph_lines.append("")
        graph_lines.append("DAILY SHARE (% of total removed across all intervals)")
        for row in consecutive_rows:
            label = f"{row['from_date']}->{row['to_date']}"
            graph_lines.append(f"{label} {pct_bar(row['daily_share_pct'])} {row['daily_share_pct']:.1f}%")
    graph_path = batch_out / "progress_graph.txt"
    graph_block = "\n".join(graph_lines) + "\n"
    if append_mode and graph_path.exists():
        with graph_path.open("a", encoding="utf-8") as f:
            f.write("\n" + ("-" * 72) + "\n")
            f.write(f"RUN {run_tag}\n")
            f.write(graph_block)
    else:
        graph_path.write_text(graph_block, encoding="utf-8")

    print(f"\nSaved batch report: {report_path.resolve()}")
    print(f"Saved per-scan CSV: {per_scan_csv.resolve()}")
    if consecutive_csv is not None:
        print(f"Saved consecutive CSV: {consecutive_csv.resolve()}")
    print("\nProgress summary:")
    for row in per_scan_rows:
        print(f"  {row['date']} | {pct_bar(row['cumulative_progress_pct'])} {row['cumulative_progress_pct']:.1f}% | {row['file']}")
    if consecutive_rows:
        print("\nDaily share:")
        for row in consecutive_rows:
            print(f"  {row['from_date']} -> {row['to_date']} | {pct_bar(row['daily_share_pct'])} {row['daily_share_pct']:.1f}%")

    if view_timeline or ask_yes_no("View chronological animation of terrain_final meshes now?", default=False):
        boundary_line = build_excavation_boundary_line_set(ref_meta, excavation_mask)
        animate_chronological_finals(processed, consecutive_rows, delay_seconds=timeline_delay, boundary_line=boundary_line)


def interactive_generate_config() -> SyntheticConfig:
    cfg = SyntheticConfig()
    print("\nSynthetic Data Options")
    if not ask_yes_no("Use default synthetic settings?", default=True):
        cfg.area = ask_float("Area size (scan units)", 2.0, 100.0, cfg.area)
        cfg.res = ask_float("Sampling resolution", 0.005, 0.2, cfg.res)
        cfg.pit_depth = ask_float("Pit depth", 0.1, 10.0, cfg.pit_depth)
        cfg.n_trees = ask_int("Number of clutter points", 0, 500000, cfg.n_trees)
        cfg.n_outliers = ask_int("Number of stray outliers", 0, 100000, cfg.n_outliers)
        cfg.add_tarp = ask_yes_no("Add synthetic tarp-like elevated cover?", default=True)
        if cfg.add_tarp:
            cfg.tarp_height = ask_float("Tarp height above local ground", 0.05, 3.0, cfg.tarp_height)
            cfg.tarp_hole_fraction = ask_float("Tarp hole fraction (returns through tarp)", 0.0, 0.95, cfg.tarp_hole_fraction)
        cfg.seed = ask_int("Random seed", 0, 999999, cfg.seed)
        out = input(f"Output filename [default {cfg.output_name}]: ").strip()
        if out:
            cfg.output_name = out
    return cfg


def interactive_terrain_config() -> TerrainConfig:
    cfg = TerrainConfig()
    print("\nTerrain Processing Options")
    if ask_yes_no("Use recommended defaults?", default=True):
        return cfg

    cfg.num_levels = ask_int("Number of preview levels", 1, 10, cfg.num_levels)
    cfg.animate = ask_yes_no("Animate terrain levels in viewer?", default=False)
    if cfg.animate:
        cfg.overlay_points = ask_yes_no("Overlay original points in viewer?", default=False)
    cfg.save_mesh = ask_yes_no("Save final terrain mesh?", default=True)
    cfg.save_ground_cloud = ask_yes_no("Save near-ground filtered cloud (removes clutter/tarp points)?", default=True)
    cfg.suppress_elevated_covers = ask_yes_no("Suppress elevated cover patches (tarp/roof-like blobs)?", default=True)
    cfg.use_statistical_outlier = ask_yes_no("Use statistical outlier removal?", default=True)
    cfg.use_radius_outlier = ask_yes_no("Use radius outlier removal?", default=False)
    cfg.ground_keep_height = ask_float("Ground keep height (scan units above terrain)", 0.05, 2.0, cfg.ground_keep_height)
    cfg.smooth_sigma = ask_float("Smoothing sigma (higher = smoother)", 0.2, 5.0, cfg.smooth_sigma)
    cfg.smooth_passes = ask_int("Smoothing passes", 1, 5, cfg.smooth_passes)
    cfg.despike_height_threshold = ask_float("Despike threshold (scan units)", 0.03, 1.0, cfg.despike_height_threshold)
    cfg.ridge_height_threshold = ask_float("Thin ridge/wall suppression threshold (scan units)", 0.05, 1.5, cfg.ridge_height_threshold)
    cfg.final_relief_clamp = ask_float("Final local relief clamp (scan units)", 0.05, 2.0, cfg.final_relief_clamp)
    return cfg


def run_interactive_menu() -> None:
    cwd = Path.cwd()
    while True:
        print("\nLiDAR Terrain Tool - Quick Start")
        print("  1. Process one point-cloud file")
        print("  2. Batch compare a folder of scans")
        print("  3. View all final meshes in current directory (chronological loop)")
        print("  4. Generate synthetic point cloud")
        print("  5. Exit")
        choice = ask_int("Select an option", 1, 5, default=1)

        if choice == 5:
            print("Exiting.")
            return

        if choice == 1:
            path = choose_point_cloud_file(cwd)
            tcfg = interactive_terrain_config()
            process_point_cloud(path, tcfg)
            continue

        if choice == 2:
            folder = choose_folder_with_point_clouds()
            tcfg = interactive_terrain_config()
            tcfg.animate = False
            run_batch_volume_timeseries(folder, tcfg)
            continue

        if choice == 3:
            delay = ask_float("Seconds between frames", 0.2, 10.0, 1.0)
            view_all_finals_in_directory(cwd, delay_seconds=delay)
            continue

        if choice == 4:
            scfg = interactive_generate_config()
            generate_synthetic_excavation(scfg)
            continue


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LiDAR archaeology terrain/topography helper")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("menu", help="Run interactive menu")

    g = sub.add_parser("generate", help="Generate synthetic excavation test data")
    g.add_argument("--output", default="synthetic_excavation.ply")
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--no-tarp", action="store_true", help="Disable synthetic tarp-like elevated cover")

    proc = sub.add_parser("process", help="Process a point cloud into terrain meshes")
    proc.add_argument("input", nargs="?", help="Point cloud file path; if omitted, interactive file picker is used")
    proc.add_argument("--levels", type=int, default=3)
    proc.add_argument("--animate", action="store_true")
    proc.add_argument("--overlay", action="store_true")
    proc.add_argument("--no-cover-suppression", action="store_true")
    proc.add_argument("--no-stat-outlier", action="store_true")
    proc.add_argument("--radius-outlier", action="store_true")
    proc.add_argument("--ground-keep-height", type=float, default=0.35)
    proc.add_argument("--smooth-sigma", type=float, default=1.0)
    proc.add_argument("--smooth-passes", type=int, default=2)
    proc.add_argument("--despike-threshold", type=float, default=0.18)
    proc.add_argument("--ridge-threshold", type=float, default=0.22)
    proc.add_argument("--relief-clamp", type=float, default=0.20)

    gp = sub.add_parser("generate-process", help="Generate synthetic data then process it")
    gp.add_argument("--output", default="synthetic_excavation.ply")
    gp.add_argument("--seed", type=int, default=0)

    batch = sub.add_parser("batch", help="Process all scans in a folder and compute excavation volume changes over time")
    batch.add_argument("folder", nargs="?", help="Folder containing scan files (.ply/.asc/etc). If omitted, asks interactively.")
    batch.add_argument("--levels", type=int, default=1, help="Terrain preview levels to build (1 is fastest and used for metrics)")
    batch.add_argument("--smooth-sigma", type=float, default=1.2)
    batch.add_argument("--smooth-passes", type=int, default=2)
    batch.add_argument("--despike-threshold", type=float, default=0.14)
    batch.add_argument("--ridge-threshold", type=float, default=0.18)
    batch.add_argument("--relief-clamp", type=float, default=0.16)
    batch.add_argument("--excavation-threshold", type=float, default=0.12, help="Depth threshold for excavation-hole detection")
    batch.add_argument("--excavation-window", type=int, default=31, help="Median window for excavation-hole detection (cells)")
    batch.add_argument("--excavation-min-cells", type=int, default=25)
    batch.add_argument("--view-timeline", action="store_true", help="Automatically open chronological final-mesh animation after analysis")
    batch.add_argument("--timeline-delay", type=float, default=1.0, help="Seconds between timeline frames")

    vf = sub.add_parser("view-finals", help="View all *_terrain_final.ply files in current directory output folders")
    vf.add_argument("--dir", default=".", help="Directory to scan for *_outputs/*_terrain_final.ply")
    vf.add_argument("--delay", type=float, default=1.0, help="Seconds between timeline frames")

    return p


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.cmd is None or args.cmd == "menu":
        run_interactive_menu()
        return

    if args.cmd == "generate":
        scfg = SyntheticConfig(output_name=args.output, seed=args.seed, add_tarp=not args.no_tarp)
        generate_synthetic_excavation(scfg)
        return

    if args.cmd == "generate-process":
        scfg = SyntheticConfig(output_name=args.output, seed=args.seed)
        path = generate_synthetic_excavation(scfg)
        tcfg = TerrainConfig()
        process_point_cloud(path, tcfg)
        return

    if args.cmd == "process":
        if args.input:
            path = Path(args.input).expanduser().resolve()
        else:
            path = choose_point_cloud_file(Path.cwd())

        tcfg = TerrainConfig(
            num_levels=max(1, min(10, args.levels)),
            animate=args.animate,
            overlay_points=args.overlay,
            suppress_elevated_covers=not args.no_cover_suppression,
            use_statistical_outlier=not args.no_stat_outlier,
            use_radius_outlier=args.radius_outlier,
            ground_keep_height=args.ground_keep_height,
            smooth_sigma=max(0.0, args.smooth_sigma),
            smooth_passes=max(1, min(5, args.smooth_passes)),
            despike_height_threshold=max(0.0, args.despike_threshold),
            ridge_height_threshold=max(0.0, args.ridge_threshold),
            final_relief_clamp=max(0.0, args.relief_clamp),
        )
        process_point_cloud(path, tcfg)
        return

    if args.cmd == "batch":
        folder = Path(args.folder).expanduser().resolve() if args.folder else choose_folder_with_point_clouds()
        if not folder.is_dir():
            raise ValueError(f"Folder not found: {folder}")
        tcfg = TerrainConfig(
            num_levels=max(1, min(10, args.levels)),
            animate=False,
            overlay_points=False,
            smooth_sigma=max(0.0, args.smooth_sigma),
            smooth_passes=max(1, min(5, args.smooth_passes)),
            despike_height_threshold=max(0.0, args.despike_threshold),
            ridge_height_threshold=max(0.0, args.ridge_threshold),
            final_relief_clamp=max(0.0, args.relief_clamp),
            excavation_detect_threshold=max(0.0, args.excavation_threshold),
            excavation_detect_window=max(5, int(args.excavation_window)),
            excavation_min_cells=max(1, int(args.excavation_min_cells)),
        )
        run_batch_volume_timeseries(
            folder,
            tcfg,
            view_timeline=args.view_timeline,
            timeline_delay=max(0.2, float(args.timeline_delay)),
        )
        return

    if args.cmd == "view-finals":
        view_all_finals_in_directory(Path(args.dir).expanduser().resolve(), delay_seconds=max(0.2, args.delay))
        return

    parser.print_help()


if __name__ == "__main__":
    main()

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

from cocoracer.pgm import DEFAULT_THRESHOLD, drivable_mask, parse_pgm
from cocoracer.track import (
    Track,
    TrackError,
    _offset_walls,
    _resample_and_fit,
    _validate_walls,
)

DEFAULT_SCALE = 0.6
GRID_UPSAMPLE = 2
CENTERLINE_SPACING = 0.3
CORRIDOR_STEP = 0.3
CORRIDOR_EDGE_MARGIN = 1.0
WALL_OUTSIDE_TOL = 1.5


@dataclass(frozen=True)
class MapMetadata:
    resolution: float
    origin: tuple[float, float]


def parse_metadata(path: Path | str) -> MapMetadata:
    """Read resolution and origin from a robot-world PGM metadata YAML.

    Only the two fields the track build needs are read; the rest of the
    file is ignored.

    Args:
        path: Path to the .yaml metadata file.

    Returns:
        The image resolution (meters per pixel) and origin (corner, y-up)
        in native meters.

    Raises:
        TrackError: If the file cannot be read or a field is missing,
        non-numeric, or out of range.
    """
    try:
        with Path(path).open() as handle:
            raw = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise TrackError(f"cannot read metadata {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise TrackError(f"metadata {path} must be a mapping")
    try:
        resolution = float(raw["resolution"])
    except (KeyError, TypeError, ValueError):
        raise TrackError(f"metadata {path} has no numeric 'resolution'") from None
    if not resolution > 0:
        raise TrackError(f"metadata {path} 'resolution' must be positive")
    origin_raw = raw.get("origin")
    if not isinstance(origin_raw, (list, tuple)) or len(origin_raw) < 2:
        raise TrackError(f"metadata {path} has no [x, y] 'origin'")
    try:
        origin = (float(origin_raw[0]), float(origin_raw[1]))
    except (TypeError, ValueError):
        raise TrackError(f"metadata {path} 'origin' is not numeric") from None
    if not np.all(np.isfinite(origin)):
        raise TrackError(f"metadata {path} 'origin' is not finite")
    return MapMetadata(resolution=resolution, origin=origin)


def parse_centerline(path: Path | str) -> np.ndarray:
    """Read a centerline CSV as an (N, 4) array of x, y, w_right, w_left.

    Values are in the map's native meters (the PGM metadata frame).

    Args:
        path: Path to the centerline .csv file.

    Returns:
        One row per point: x, y, w_right, w_left in native meters.

    Raises:
        TrackError: If the file cannot be read, a row has the wrong column
        count or non-numeric values, a wall width is not positive, or fewer
        than four points remain.
    """
    try:
        text = Path(path).read_text()
    except OSError as exc:
        raise TrackError(f"cannot read centerline {path}: {exc}") from exc
    rows: list[list[float]] = []
    for lineno, row in enumerate(csv.reader(text.splitlines()), start=1):
        if not row:
            continue
        if len(row) != 4:
            raise TrackError(
                f"centerline {path} line {lineno}: expected 4 columns "
                f"(x, y, w_right, w_left), got {len(row)}"
            )
        try:
            values = [float(value) for value in row]
        except ValueError:
            raise TrackError(
                f"centerline {path} line {lineno}: non-numeric value in {row!r}"
            ) from None
        if not np.all(np.isfinite(values)):
            raise TrackError(
                f"centerline {path} line {lineno}: non-finite value in {row!r}"
            )
        rows.append(values)
    if len(rows) < 4:
        raise TrackError(f"centerline {path}: needs at least 4 points, got {len(rows)}")
    points = np.asarray(rows, dtype=np.float64)
    if np.any(points[:, 2:] <= 0):
        bad = int(np.argmax(points[:, 2:] <= 0))
        raise TrackError(
            f"centerline {path} line {bad + 1}: wall widths must be positive"
        )
    return points


def build_map_track(
    name: str,
    centerline_csv: Path | str,
    metadata_yaml: Path | str,
    image_pgm: Path | str,
    scale: float = DEFAULT_SCALE,
    threshold: int = DEFAULT_THRESHOLD,
) -> Track:
    """Build a Track from a map's centerline CSV, metadata YAML, and PGM image.

    Points and widths are converted from native meters to track world
    (origin at the image corner, y-up, scaled by scale/resolution), then
    the existing Frenet machinery resamples and splines the centerline.
    The wall curves are the pointwise normal offsets of the resampled
    centerline by the CSV's w_left and w_right. The occupancy grid is the
    largest-component drivable mask of the image, upsampled 2x.

    The build fails with TrackError when the CSV or metadata is malformed,
    a centerline point leaves the image, the walls sit outside the
    drivable surface, or the corridor between the walls crosses
    non-drivable pixels.

    Args:
        name: Track name.
        centerline_csv: Centerline file, one row per point:
            x, y, w_right, w_left in native meters.
        metadata_yaml: Robot-world PGM metadata (resolution, origin).
        image_pgm: The map's PGM P5 image.
        scale: Track scale, meters of track world per image pixel.
        threshold: Minimum pixel value that counts as drivable.

    Returns:
        The built Track.
    """
    meta = parse_metadata(metadata_yaml)
    native = parse_centerline(centerline_csv)
    image = parse_pgm(image_pgm)
    mask = drivable_mask(image, threshold)
    return _build_from_native(name, native, meta, image, mask, scale)


def _build_from_native(
    name: str,
    native: np.ndarray,
    meta: MapMetadata,
    image: np.ndarray,
    mask: np.ndarray,
    scale: float,
) -> Track:
    factor = scale / meta.resolution
    xy = (native[:, :2] - np.array(meta.origin, dtype=np.float64)) * factor
    widths = native[:, 2:] * factor
    _check_inside_image(name, xy, scale, image.shape)
    raw = _ring_raw(xy)
    centerline, track_length, spline_x, spline_y, tree, frenet_s = _resample_and_fit(
        raw, CENTERLINE_SPACING
    )
    s_vals = np.concatenate([frenet_s, [0.0]])
    s_cum = _ring_s_cum(xy)
    extended = np.vstack([widths, widths[:1]])
    w_right = np.interp(s_vals, s_cum, extended[:, 0])
    w_left = np.interp(s_vals, s_cum, extended[:, 1])
    left_wall, right_wall = _offset_walls(
        centerline, s_vals, spline_x, spline_y, w_left, w_right
    )
    _validate_walls(name, left_wall, right_wall)
    _check_walls_on_mask(name, left_wall, right_wall, mask, scale)
    _check_corridor(
        name, centerline, s_vals, spline_x, spline_y, w_left, w_right, mask, scale
    )
    # The mask's row 0 is the image top; the track grid's y axis points up
    # from the bottom corner, so the rows must be reversed before upsample.
    upsampled = np.kron(
        mask[::-1, :], np.ones((GRID_UPSAMPLE, GRID_UPSAMPLE), dtype=bool)
    )
    # Pointwise: the wall pairs share the centerline's s indices, so the
    # corridor width at each s is exactly w_left + w_right. A nearest-point
    # median would under-report it where the track's sections run close.
    width = float(np.median(w_left + w_right))
    return Track(
        name=name,
        width=width,
        resolution=scale / GRID_UPSAMPLE,
        track_length=track_length,
        centerline=centerline,
        left_wall=left_wall,
        right_wall=right_wall,
        spline_x=spline_x,
        spline_y=spline_y,
        grid_origin=(0.0, 0.0),
        grid_shape=upsampled.shape,
        occupied=~upsampled,
        frenet_tree=tree,
        frenet_s=frenet_s,
    )


def _ring_raw(xy: np.ndarray) -> np.ndarray:
    body = xy
    nxt = np.roll(body, -1, axis=0)
    prv = np.roll(body, 1, axis=0)
    heading = np.arctan2(nxt[:, 1] - prv[:, 1], nxt[:, 0] - prv[:, 0])
    yaw = np.unwrap(heading)
    raw = np.column_stack([body, yaw])
    return np.vstack([raw, [raw[0, 0], raw[0, 1], yaw[0]]])


def _ring_s_cum(xy: np.ndarray) -> np.ndarray:
    closed = np.vstack([xy, xy[:1]])
    steps = np.hypot(np.diff(closed[:, 0]), np.diff(closed[:, 1]))
    return np.concatenate([[0.0], np.cumsum(steps)])


def _check_inside_image(
    name: str, xy: np.ndarray, scale: float, shape: tuple[int, int]
) -> None:
    height, width = shape
    max_x = width * scale
    max_y = height * scale
    outside = (
        (xy[:, 0] < -1e-9)
        | (xy[:, 0] > max_x + 1e-9)
        | (xy[:, 1] < -1e-9)
        | (xy[:, 1] > max_y + 1e-9)
    )
    if outside.any():
        i = int(np.argmax(outside))
        raise TrackError(
            f"track {name!r} centerline point ({xy[i, 0]:.2f}, {xy[i, 1]:.2f}) "
            f"is outside the image"
        )


def _check_walls_on_mask(
    name: str,
    left_wall: np.ndarray,
    right_wall: np.ndarray,
    mask: np.ndarray,
    scale: float,
) -> None:
    if not mask.any():
        raise TrackError(f"track {name!r} image has no drivable surface")
    height, width = mask.shape
    points = np.vstack([left_wall, right_wall])
    col = points[:, 0] / scale
    row = height - points[:, 1] / scale
    inside = (col >= 0) & (col < width) & (row >= 0) & (row < height)
    irows = np.clip(row, 0, height - 1).astype(np.intp)
    icols = np.clip(col, 0, width - 1).astype(np.intp)
    on_surface = inside & mask[irows, icols]
    distances = np.zeros(len(points))
    missing = ~on_surface
    if missing.any():
        rws, cls = np.nonzero(mask)
        surface = np.column_stack([(cls + 0.5) * scale, (height - rws - 0.5) * scale])
        distances[missing] = cKDTree(surface).query(points[missing])[0]
    worst = int(np.argmax(distances))
    if distances[worst] > WALL_OUTSIDE_TOL:
        side = "left" if worst < len(left_wall) else "right"
        raise TrackError(
            f"track {name!r} {side} wall point ({points[worst, 0]:.2f}, "
            f"{points[worst, 1]:.2f}) is {distances[worst]:.2f} m from the "
            f"drivable surface"
        )


def _check_corridor(
    name: str,
    centerline: np.ndarray,
    s: np.ndarray,
    spline_x: CubicSpline,
    spline_y: CubicSpline,
    w_left: np.ndarray,
    w_right: np.ndarray,
    mask: np.ndarray,
    scale: float,
) -> None:
    height, width = mask.shape
    col0 = centerline[:, 0] / scale
    row0 = height - centerline[:, 1] / scale
    inside0 = (col0 >= 0) & (col0 < width) & (row0 >= 0) & (row0 < height)
    if not inside0.all():
        j = int(np.argmax(~inside0))
        raise _corridor_error(name, "centerline", float(s[j]), col0[j], row0[j])
    if not mask[row0.astype(np.intp), col0.astype(np.intp)].all():
        j = int(np.argmax(~mask[row0.astype(np.intp), col0.astype(np.intp)]))
        raise _corridor_error(name, "centerline", float(s[j]), col0[j], row0[j])
    dx = spline_x(s, 1)
    dy = spline_y(s, 1)
    norm = np.hypot(dx, dy)
    nx = -dy / norm
    ny = dx / norm
    for side, sign, w_side in (("left", 1.0, w_left), ("right", -1.0, w_right)):
        for i in range(len(s)):
            reach = w_side[i] - CORRIDOR_EDGE_MARGIN
            if reach <= 0:
                continue
            t = np.arange(0.0, reach, CORRIDOR_STEP)
            t = np.append(t, reach)
            px = centerline[i, 0] + sign * nx[i] * t
            py = centerline[i, 1] + sign * ny[i] * t
            col = px / scale
            row = height - py / scale
            inside = (col >= 0) & (col < width) & (row >= 0) & (row < height)
            if not inside.all():
                j = int(np.argmax(~inside))
                raise _corridor_error(name, side, float(s[i]), col[j], row[j])
            irows = row.astype(np.intp)
            icols = col.astype(np.intp)
            if not mask[irows, icols].all():
                j = int(np.argmax(~mask[irows, icols]))
                raise _corridor_error(name, side, float(s[i]), col[j], row[j])


def _corridor_error(
    name: str, side: str, s_value: float, col: float, row: float
) -> TrackError:
    return TrackError(
        f"track {name!r} {side} corridor is not drivable at s={s_value:.1f} m, "
        f"image pixel ({int(round(row))}, {int(round(col))})"
    )

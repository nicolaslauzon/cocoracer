from pathlib import Path

import numpy as np
import pytest

from cocoracer.maptrack import (
    DEFAULT_SCALE,
    build_map_track,
    parse_centerline,
    parse_metadata,
)
from cocoracer.track import TrackError

MAPS = Path(__file__).resolve().parent.parent / "maps"
SHIPPED = ["right-interior", "race_f1tenth_icra_2023_short", "icra-2025"]
# Start pixel of each shipped map at its first centerline point.
SHIPPED_STARTS = {
    "right-interior": (61, 174),
    "race_f1tenth_icra_2023_short": (30, 178),
    "icra-2025": (29, 163),
}


def _write_pgm(path: Path, image: np.ndarray) -> Path:
    height, width = image.shape
    header = f"P5\n{width} {height}\n255\n".encode()
    path.write_bytes(header + np.ascontiguousarray(image, dtype=np.uint8).tobytes())
    return path


def _write_metadata(path: Path, origin: tuple[float, float]) -> Path:
    path.write_text(f"resolution: 0.05\norigin: [{origin[0]}, {origin[1]}, 0.0]\n")
    return path


def _write_centerline(
    path: Path, n: int = 180, w_left: float = 0.5, w_right: float = 0.5
) -> Path:
    angles = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    xs = 3.0 + 2.0 * np.cos(angles)
    ys = 3.0 + 2.0 * np.sin(angles)
    lines = [
        f"{x:.6f},{y:.6f},{w_right:.6f},{w_left:.6f}"
        for x, y in zip(xs, ys, strict=True)
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def _write_image(
    path: Path,
    inner: float = 28.0,
    outer: float = 52.0,
    drivable: int = 254,
    wall: int = 205,
    stripe: bool = False,
) -> Path:
    size = 120
    yy, xx = np.mgrid[0:size, 0:size]
    radius = np.hypot(xx - 60.0, yy - 60.0)
    image = np.where((radius >= inner) & (radius <= outer), drivable, wall)
    if stripe:
        image[59:62, 92:97] = wall
    return _write_pgm(path, image.astype(np.uint8))


def _synthetic_map(
    tmp_path: Path,
    inner: float = 28.0,
    outer: float = 52.0,
    w_left: float = 0.5,
    w_right: float = 0.5,
    origin: tuple[float, float] = (0.0, 0.0),
    drivable: int = 254,
    wall: int = 205,
    stripe: bool = False,
) -> tuple[Path, Path, Path]:
    image = _write_image(
        tmp_path / "map.pgm",
        inner=inner,
        outer=outer,
        drivable=drivable,
        wall=wall,
        stripe=stripe,
    )
    metadata = _write_metadata(tmp_path / "map.yaml", origin)
    centerline = _write_centerline(tmp_path / "map.csv", w_left=w_left, w_right=w_right)
    return centerline, metadata, image


def test_parse_metadata_reads_resolution_and_origin(tmp_path: Path) -> None:
    path = _write_metadata(tmp_path / "map.yaml", (0.5, 0.25))
    meta = parse_metadata(path)
    assert meta.resolution == pytest.approx(0.05)
    assert meta.origin == (0.5, 0.25)


def test_parse_metadata_missing_resolution_is_error(tmp_path: Path) -> None:
    path = tmp_path / "map.yaml"
    path.write_text("origin: [0.0, 0.0, 0.0]\n")
    with pytest.raises(TrackError, match="resolution"):
        parse_metadata(path)


def test_parse_metadata_missing_origin_is_error(tmp_path: Path) -> None:
    path = tmp_path / "map.yaml"
    path.write_text("resolution: 0.05\n")
    with pytest.raises(TrackError, match="origin"):
        parse_metadata(path)


def test_parse_centerline_reads_native_rows(tmp_path: Path) -> None:
    path = _write_centerline(tmp_path / "map.csv")
    points = parse_centerline(path)
    assert points.shape == (180, 4)
    np.testing.assert_allclose(points[0], [5.0, 3.0, 0.5, 0.5], atol=1e-6)


def test_parse_centerline_wrong_column_count_is_error(tmp_path: Path) -> None:
    path = tmp_path / "map.csv"
    path.write_text("1.0,2.0,0.5\n")
    with pytest.raises(TrackError, match="4 columns"):
        parse_centerline(path)


def test_parse_centerline_non_numeric_is_error(tmp_path: Path) -> None:
    path = tmp_path / "map.csv"
    path.write_text("1.0,abc,0.5,0.5\n")
    with pytest.raises(TrackError, match="non-numeric"):
        parse_centerline(path)


def test_parse_centerline_too_few_points_is_error(tmp_path: Path) -> None:
    path = tmp_path / "map.csv"
    path.write_text("1.0,2.0,0.5,0.5\n3.0,4.0,0.5,0.5\n")
    with pytest.raises(TrackError, match="at least 4"):
        parse_centerline(path)


def test_parse_centerline_non_positive_width_is_error(tmp_path: Path) -> None:
    path = tmp_path / "map.csv"
    path.write_text(
        "1.0,2.0,0.0,0.5\n3.0,4.0,0.5,0.5\n5.0,6.0,0.5,0.5\n7.0,8.0,0.5,0.5\n"
    )
    with pytest.raises(TrackError, match="positive"):
        parse_centerline(path)


def test_synthetic_build_converts_to_track_world(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path)
    track = build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))
    assert track.centerline[0, 0] == pytest.approx(60.0, abs=1e-6)
    assert track.centerline[0, 1] == pytest.approx(36.0, abs=1e-6)
    assert track.start_pose[2] == pytest.approx(np.pi / 2.0, abs=0.01)
    assert track.track_length == pytest.approx(150.79, rel=1e-3)
    assert track.resolution == pytest.approx(0.3)
    assert track.grid_origin == (0.0, 0.0)
    assert track.grid_shape == (240, 240)
    assert track.occupied.shape == (240, 240)
    # Arena corner and the annulus hole are wall; mid-corridor is free.
    assert track.point_in_wall(0.3, 0.3)
    assert track.point_in_wall(36.0, 36.0)
    assert not track.point_in_wall(66.0, 36.0)


def test_synthetic_build_scale_override(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path)
    track = build_map_track(
        "syn", centerline, metadata, image, "ccw", (100, 60), scale=1.2
    )
    assert track.centerline[0, 0] == pytest.approx(120.0, abs=1e-6)
    assert track.centerline[0, 1] == pytest.approx(72.0, abs=1e-6)
    assert track.width == pytest.approx(24.0, abs=0.05)
    assert track.resolution == pytest.approx(0.6)


def test_synthetic_build_origin_applied(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path, origin=(0.1, 0.05))
    track = build_map_track("syn", centerline, metadata, image, "ccw", (98, 60))
    assert track.centerline[0, 0] == pytest.approx(58.8, abs=1e-6)
    assert track.centerline[0, 1] == pytest.approx(35.4, abs=1e-6)


def test_synthetic_build_walls_are_normal_offsets(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path)
    track = build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))
    center = np.array([36.0, 36.0])
    left_r = np.linalg.norm(track.left_wall[:-1] - center, axis=1)
    right_r = np.linalg.norm(track.right_wall[:-1] - center, axis=1)
    np.testing.assert_allclose(left_r, 18.0, atol=0.2)
    np.testing.assert_allclose(right_r, 30.0, atol=0.2)
    assert track.width == pytest.approx(12.0, abs=0.05)


def test_synthetic_threshold_override(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path, drivable=210, wall=100)
    with pytest.raises(TrackError, match="drivable surface"):
        build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))
    track = build_map_track(
        "syn", centerline, metadata, image, "ccw", (100, 60), threshold=200
    )
    assert track.width == pytest.approx(12.0, abs=0.05)


def test_wall_outside_drivable_surface_is_error(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path, w_left=0.9, w_right=0.9)
    with pytest.raises(TrackError, match="drivable surface"):
        build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))


def test_centerline_outside_drivable_surface_is_error(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path, inner=20.0, outer=36.0)
    with pytest.raises(TrackError, match="drivable"):
        build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))


def test_corridor_crossing_wall_stripe_is_error(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path, stripe=True)
    with pytest.raises(TrackError, match="corridor is not drivable"):
        build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))


@pytest.mark.parametrize("name", SHIPPED)
def test_shipped_map_builds_and_width_matches_csv(name: str) -> None:
    track = build_map_track(
        name,
        MAPS / f"{name}.csv",
        MAPS / f"{name}.yaml",
        MAPS / f"{name}.pgm",
        "ccw",
        SHIPPED_STARTS[name],
    )
    points = parse_centerline(MAPS / f"{name}.csv")
    expected = float(np.median((points[:, 2] + points[:, 3]) * (DEFAULT_SCALE / 0.05)))
    assert track.width == pytest.approx(expected, rel=0.1)
    assert track.grid_shape[0] % 2 == 0 and track.grid_shape[1] % 2 == 0
    np.testing.assert_allclose(
        track.centerline[0, :2], track.centerline[-1, :2], atol=1e-9
    )
    x, y, _ = track.start_pose
    assert not track.point_in_wall(x, y)


def test_synthetic_build_grid_is_upsampled_mask(tmp_path: Path) -> None:
    from cocoracer.pgm import drivable_mask, parse_pgm

    centerline, metadata, image = _synthetic_map(tmp_path)
    track = build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))
    mask = drivable_mask(parse_pgm(image))
    assert track.resolution == pytest.approx(0.3)
    assert track.grid_shape == tuple(2 * s for s in mask.shape)
    expected = ~np.kron(mask[::-1, :], np.ones((2, 2), dtype=bool))
    np.testing.assert_array_equal(track.occupied, expected)


def test_synthetic_build_is_frenet_ready(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path)
    track = build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))
    x, y, psi = track.to_cartesian(40.0, 0.0)
    s, d, yaw = track.to_frenet(x, y, psi)
    assert s == pytest.approx(40.0, abs=0.3)
    assert d == pytest.approx(0.0, abs=0.3)
    assert yaw == pytest.approx(0.0, abs=0.05)
    assert track.checkpoint_s == pytest.approx(track.track_length / 2.0)


def test_direction_ccw_matches_point_order(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path, w_left=0.4, w_right=0.6)
    track = build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))
    x, y, yaw = track.start_pose
    assert (x, y) == pytest.approx((60.0, 36.0))
    assert yaw == pytest.approx(np.pi / 2.0, abs=0.05)
    center = np.array([36.0, 36.0])
    left_r = np.linalg.norm(track.left_wall[:-1] - center, axis=1)
    right_r = np.linalg.norm(track.right_wall[:-1] - center, axis=1)
    np.testing.assert_allclose(left_r, 19.2, atol=0.2)
    np.testing.assert_allclose(right_r, 31.2, atol=0.2)


def test_direction_cw_reverses_centerline_and_swaps_walls(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path, w_left=0.4, w_right=0.6)
    ccw = build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))
    cw = build_map_track("syn", centerline, metadata, image, "cw", (100, 60))
    x, y, yaw = cw.start_pose
    assert (x, y) == pytest.approx((60.0, 36.0))
    assert yaw == pytest.approx(-np.pi / 2.0, abs=0.05)
    center = np.array([36.0, 36.0])
    left_r = np.linalg.norm(cw.left_wall[:-1] - center, axis=1)
    right_r = np.linalg.norm(cw.right_wall[:-1] - center, axis=1)
    np.testing.assert_allclose(left_r, 31.2, atol=0.2)
    np.testing.assert_allclose(right_r, 19.2, atol=0.2)
    n = len(ccw.centerline) - 1
    for k in (1, 2, 5, n // 2):
        np.testing.assert_allclose(
            cw.centerline[k, :2], ccw.centerline[(n - k) % n, :2], atol=0.05
        )


def test_start_line_lands_at_configured_pixel(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path)
    track = build_map_track("syn", centerline, metadata, image, "ccw", (60, 20))
    x, y, yaw = track.start_pose
    assert x == pytest.approx(36.0, abs=0.6)
    assert y == pytest.approx(60.0, abs=0.6)
    assert yaw == pytest.approx(-np.pi, abs=0.05)
    px = (60 + 0.5) * DEFAULT_SCALE
    py = (120 - 20 - 0.5) * DEFAULT_SCALE
    s, d, _ = track.to_frenet(px, py, yaw)
    assert min(s, track.track_length - s) <= 0.6
    assert d == pytest.approx(0.0, abs=0.6)
    mx, my, _ = track.to_cartesian(track.checkpoint_s, 0.0)
    assert (mx, my) == pytest.approx((36.0, 12.0), abs=0.3)


def test_start_pixel_outside_image_is_error(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path)
    with pytest.raises(TrackError, match="outside the image"):
        build_map_track("syn", centerline, metadata, image, "ccw", (500, 60))


def test_unknown_direction_is_error(tmp_path: Path) -> None:
    centerline, metadata, image = _synthetic_map(tmp_path)
    with pytest.raises(TrackError, match="direction"):
        build_map_track("syn", centerline, metadata, image, "sideways", (100, 60))


def test_build_track_dispatches_map_spec(tmp_path: Path) -> None:
    from cocoracer.config import MapSpec, TrackSpec
    from cocoracer.track import build_track

    centerline, metadata, image = _synthetic_map(tmp_path)
    spec = TrackSpec(
        name="syn",
        width=0.0,
        resolution=0.0,
        map=MapSpec(
            image=image, scale=0.6, threshold=250, direction="ccw", start=(100, 60)
        ),
    )
    track = build_track(spec)
    direct = build_map_track("syn", centerline, metadata, image, "ccw", (100, 60))
    np.testing.assert_allclose(track.centerline, direct.centerline, atol=1e-9)
    assert track.track_length == pytest.approx(direct.track_length)
    np.testing.assert_array_equal(track.occupied, direct.occupied)


@pytest.mark.parametrize("name", SHIPPED)
def test_shipped_map_grid_is_double_upsampled_mask(name: str) -> None:
    from cocoracer.pgm import drivable_mask, parse_pgm

    image = parse_pgm(MAPS / f"{name}.pgm")
    track = build_map_track(
        name,
        MAPS / f"{name}.csv",
        MAPS / f"{name}.yaml",
        MAPS / f"{name}.pgm",
        "ccw",
        SHIPPED_STARTS[name],
    )
    mask = drivable_mask(image)
    assert track.grid_shape == tuple(2 * s for s in mask.shape)
    assert track.resolution == pytest.approx(DEFAULT_SCALE / 2.0)
    expected = ~np.kron(mask[::-1, :], np.ones((2, 2), dtype=bool))
    np.testing.assert_array_equal(track.occupied, expected)

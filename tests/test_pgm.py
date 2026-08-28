from pathlib import Path

import numpy as np
import pytest
from scipy.ndimage import label

from cocoracer.pgm import DEFAULT_THRESHOLD, PgmError, drivable_mask, parse_pgm

MAPS = Path(__file__).resolve().parent.parent / "maps"


def _write_pgm(path: Path, image: np.ndarray) -> Path:
    height, width = image.shape
    header = f"P5\n{width} {height}\n255\n".encode()
    path.write_bytes(header + np.ascontiguousarray(image, dtype=np.uint8).tobytes())
    return path


def test_parse_p5_returns_image_at_image_dimensions(tmp_path: Path) -> None:
    image = np.arange(40, dtype=np.uint8).reshape(5, 8)
    path = _write_pgm(tmp_path / "img.pgm", image)
    parsed = parse_pgm(path)
    assert parsed.shape == (5, 8)
    assert parsed.dtype == np.uint8
    np.testing.assert_array_equal(parsed, image)


def test_parse_p5_skips_comment_lines_between_header_fields(tmp_path: Path) -> None:
    image = np.full((3, 4), 7, dtype=np.uint8)
    data = (
        b"P5\n"
        b"# Created by GIMP version 2.10.30 PNM plugin\n"
        b"4 3\n"
        b"# a comment between dimensions and maxval\n"
        b"255\n"
    ) + image.tobytes()
    path = tmp_path / "img.pgm"
    path.write_bytes(data)
    parsed = parse_pgm(path)
    assert parsed.shape == (3, 4)
    np.testing.assert_array_equal(parsed, image)


def test_parse_rejects_non_p5_magic(tmp_path: Path) -> None:
    path = tmp_path / "img.pgm"
    path.write_bytes(b"P2\n4 3\n255\n" + b"\x00" * 12)
    with pytest.raises(PgmError):
        parse_pgm(path)


def test_parse_rejects_truncated_pixel_data(tmp_path: Path) -> None:
    path = tmp_path / "img.pgm"
    path.write_bytes(b"P5\n4 3\n255\n" + b"\x00" * 5)
    with pytest.raises(PgmError):
        parse_pgm(path)


def test_drivable_mask_default_threshold_splits_254_from_205(tmp_path: Path) -> None:
    image = np.array([[254, 254], [205, 205]], dtype=np.uint8)
    mask = drivable_mask(parse_pgm(_write_pgm(tmp_path / "img.pgm", image)))
    np.testing.assert_array_equal(mask, np.array([[True, True], [False, False]]))
    assert DEFAULT_THRESHOLD == 250


def test_drivable_mask_threshold_override(tmp_path: Path) -> None:
    image = np.array([[254, 205], [100, 250]], dtype=np.uint8)
    path = _write_pgm(tmp_path / "img.pgm", image)
    parsed = parse_pgm(path)
    np.testing.assert_array_equal(
        drivable_mask(parsed, threshold=200),
        np.array([[True, True], [False, True]]),
    )
    np.testing.assert_array_equal(
        drivable_mask(parsed, threshold=254), np.array([[True, False], [False, False]])
    )
    assert not drivable_mask(parsed, threshold=255).any()


def test_drivable_mask_is_boolean_at_image_dimensions(tmp_path: Path) -> None:
    image = np.full((6, 7), 254, dtype=np.uint8)
    mask = drivable_mask(parse_pgm(_write_pgm(tmp_path / "img.pgm", image)))
    assert mask.shape == (6, 7)
    assert mask.dtype == bool
    assert mask.all()


def test_specks_are_dropped_only_largest_component_survives(tmp_path: Path) -> None:
    image = np.zeros((10, 10), dtype=np.uint8)
    image[2:6, 2:6] = 254  # 16 px blob
    image[8, 8] = 254  # 1 px anti-aliasing speck
    image[0, 0] = 254  # another 1 px speck
    mask = drivable_mask(parse_pgm(_write_pgm(tmp_path / "img.pgm", image)))
    assert mask.sum() == 16
    assert not mask[8, 8]
    assert not mask[0, 0]
    np.testing.assert_array_equal(mask[2:6, 2:6], np.ones((4, 4), dtype=bool))


def test_largest_component_wins_over_first_component(tmp_path: Path) -> None:
    image = np.zeros((10, 10), dtype=np.uint8)
    image[0:2, 0:2] = 254  # 4 px, labelled first
    image[5:9, 5:9] = 254  # 16 px
    mask = drivable_mask(parse_pgm(_write_pgm(tmp_path / "img.pgm", image)))
    assert mask.sum() == 16
    assert not mask[0, 0]
    np.testing.assert_array_equal(mask[5:9, 5:9], np.ones((4, 4), dtype=bool))


def test_all_wall_image_gives_empty_mask(tmp_path: Path) -> None:
    image = np.full((4, 5), 205, dtype=np.uint8)
    mask = drivable_mask(parse_pgm(_write_pgm(tmp_path / "img.pgm", image)))
    assert mask.shape == (4, 5)
    assert not mask.any()


@pytest.mark.parametrize(
    ("filename", "height", "width"),
    [
        ("icra-2025.pgm", 229, 525),
        ("race_f1tenth_icra_2023_short.pgm", 265, 498),
        ("right-interior-gimp.pgm", 555, 456),
    ],
)
def test_shipped_maps_parse_to_single_component(
    filename: str, height: int, width: int
) -> None:
    parsed = parse_pgm(MAPS / filename)
    assert parsed.shape == (height, width)
    assert (parsed == 254).sum() > 5000
    mask = drivable_mask(parsed)
    assert mask.shape == (height, width)
    _, count = label(mask)
    assert count == 1
    assert mask.sum() > 5000

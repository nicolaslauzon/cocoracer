import json
from pathlib import Path

import pytest

from cocoracer.config import ConfigError, TrackSpec, load_config

PARAMS = Path(__file__).resolve().parent.parent / "params" / "default.yaml"


def _write_params(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "params.yaml"
    path.write_text(body)
    return path


def test_default_config_loads() -> None:
    cfg = load_config(PARAMS)
    assert cfg.default_track == "stadium"
    assert set(cfg.tracks) == {"stadium", "montreal", "spa", "silverstone"}


def test_race_block_has_no_grid_spacing() -> None:
    cfg = load_config(PARAMS)
    assert not hasattr(cfg.race, "grid_spacing")


def test_legacy_grid_spacing_key_is_ignored(tmp_path: Path) -> None:
    path = _write_params(
        tmp_path,
        "race:\n"
        "  grid_spacing: 3.75\n"
        "tracks:\n"
        "  t1:\n"
        "    width: 1.0\n"
        "    resolution: 0.1\n"
        "    centerline:\n"
        "      - [0.0, 0.0]\n"
        "      - [1.0, 0.0]\n"
        "      - [1.0, 1.0]\n"
        "      - [0.0, 1.0]\n",
    )
    cfg = load_config(path)
    assert not hasattr(cfg.race, "grid_spacing")


def test_segment_track_has_no_centerline() -> None:
    stadium = load_config(PARAMS).tracks["stadium"]
    assert stadium.segments is not None
    assert stadium.centerline is None


def test_file_tracks_have_closed_centerlines() -> None:
    cfg = load_config(PARAMS)
    for name in ("montreal", "spa", "silverstone"):
        spec = cfg.tracks[name]
        assert spec.segments is None
        assert spec.centerline is not None
        assert len(spec.centerline) > 100
        assert spec.centerline[0] == spec.centerline[-1]


def test_file_reference_success(tmp_path: Path) -> None:
    (tmp_path / "t.json").write_text(
        json.dumps(
            {
                "width": 2.0,
                "resolution": 0.2,
                "centerline": [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]],
            }
        )
    )
    cfg = load_config(_write_params(tmp_path, "tracks:\n  t1:\n    file: t.json\n"))
    spec = cfg.tracks["t1"]
    assert isinstance(spec, TrackSpec)
    assert spec.width == 2.0
    assert spec.resolution == 0.2
    assert spec.centerline == [
        (0.0, 0.0),
        (2.0, 0.0),
        (2.0, 2.0),
        (0.0, 2.0),
        (0.0, 0.0),
    ]


def test_file_reference_missing(tmp_path: Path) -> None:
    path = _write_params(tmp_path, "tracks:\n  t1:\n    file: missing.json\n")
    with pytest.raises(ConfigError, match="not found"):
        load_config(path)


def test_file_reference_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{not json")
    path = _write_params(tmp_path, "tracks:\n  t1:\n    file: bad.json\n")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(path)


def test_file_reference_non_dict(tmp_path: Path) -> None:
    (tmp_path / "list.json").write_text("[1, 2]")
    path = _write_params(tmp_path, "tracks:\n  t1:\n    file: list.json\n")
    with pytest.raises(ConfigError, match="JSON object"):
        load_config(path)


def test_track_without_layout(tmp_path: Path) -> None:
    path = _write_params(
        tmp_path,
        "tracks:\n  t1:\n    width: 1.0\n    resolution: 0.1\n",
    )
    with pytest.raises(ConfigError, match="needs 'segments' or 'centerline'"):
        load_config(path)


def test_track_with_both_layouts(tmp_path: Path) -> None:
    path = _write_params(
        tmp_path,
        "tracks:\n"
        "  t1:\n"
        "    width: 1.0\n"
        "    resolution: 0.1\n"
        "    segments:\n"
        "      - { type: straight, length: 5.0 }\n"
        "    centerline:\n"
        "      - [0.0, 0.0]\n"
        "      - [1.0, 0.0]\n"
        "      - [1.0, 1.0]\n"
        "      - [0.0, 1.0]\n",
    )
    with pytest.raises(ConfigError, match="both"):
        load_config(path)


def test_centerline_bad_point(tmp_path: Path) -> None:
    path = _write_params(
        tmp_path,
        "tracks:\n"
        "  t1:\n"
        "    width: 1.0\n"
        "    resolution: 0.1\n"
        "    centerline:\n"
        "      - [0.0, 0.0]\n"
        "      - [1.0]\n"
        "      - [1.0, 1.0]\n"
        "      - [0.0, 1.0]\n",
    )
    with pytest.raises(ConfigError, match=r"centerline\[1\]"):
        load_config(path)


def test_centerline_too_short(tmp_path: Path) -> None:
    path = _write_params(
        tmp_path,
        "tracks:\n"
        "  t1:\n"
        "    width: 1.0\n"
        "    resolution: 0.1\n"
        "    centerline:\n"
        "      - [0.0, 0.0]\n"
        "      - [1.0, 0.0]\n",
    )
    with pytest.raises(ConfigError, match="at least 4"):
        load_config(path)


_TRACKS_BLOCK = (
    "tracks:\n"
    "  t1:\n"
    "    width: 1.0\n"
    "    resolution: 0.1\n"
    "    centerline:\n"
    "      - [0.0, 0.0]\n"
    "      - [1.0, 0.0]\n"
    "      - [1.0, 1.0]\n"
    "      - [0.0, 1.0]\n"
)


def _write_map(tmp_path: Path, stem: str = "map") -> Path:
    pgm = tmp_path / f"{stem}.pgm"
    pgm.write_bytes(b"P5\n2 2\n255\n" + b"\xff" * 4)
    (tmp_path / f"{stem}.csv").write_text(
        "0.0,0.0,0.5,0.5\n1.0,0.0,0.5,0.5\n1.0,1.0,0.5,0.5\n0.0,1.0,0.5,0.5\n"
    )
    (tmp_path / f"{stem}.yaml").write_text(
        "resolution: 0.05\norigin: [0.0, 0.0, 0.0]\n"
    )
    return pgm


def test_maps_section_defaults_apply(tmp_path: Path) -> None:
    _write_map(tmp_path)
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  scale: 0.9\n"
        "  threshold: 200\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: map.pgm\n"
        "      direction: cw\n"
        "      start: [1, 1]\n" + _TRACKS_BLOCK,
    )
    cfg = load_config(path)
    spec = cfg.tracks["m1"]
    assert spec.map is not None
    assert spec.map.image == tmp_path / "map.pgm"
    assert spec.map.scale == 0.9
    assert spec.map.threshold == 200
    assert spec.map.direction == "cw"
    assert spec.map.start == (1, 1)


def test_maps_section_module_defaults_apply(tmp_path: Path) -> None:
    _write_map(tmp_path)
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: map.pgm\n"
        "      direction: ccw\n"
        "      start: [1, 1]\n" + _TRACKS_BLOCK,
    )
    cfg = load_config(path)
    spec = cfg.tracks["m1"]
    assert spec.map is not None
    assert spec.map.scale == 0.6
    assert spec.map.threshold == 250


def test_maps_per_track_overrides_win(tmp_path: Path) -> None:
    _write_map(tmp_path)
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  scale: 0.9\n"
        "  threshold: 200\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: map.pgm\n"
        "      direction: cw\n"
        "      start: [1, 1]\n"
        "    m2:\n"
        "      map: map.pgm\n"
        "      scale: 1.2\n"
        "      threshold: 100\n"
        "      direction: ccw\n"
        "      start: [1, 2]\n" + _TRACKS_BLOCK,
    )
    cfg = load_config(path)
    m1 = cfg.tracks["m1"].map
    m2 = cfg.tracks["m2"].map
    assert m1 is not None and m2 is not None
    assert (m1.scale, m1.threshold) == (0.9, 200)
    assert (m2.scale, m2.threshold) == (1.2, 100)


def test_map_track_missing_direction_is_error(tmp_path: Path) -> None:
    _write_map(tmp_path)
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: map.pgm\n"
        "      start: [1, 1]\n" + _TRACKS_BLOCK,
    )
    with pytest.raises(ConfigError, match="direction"):
        load_config(path)


def test_map_track_missing_start_is_error(tmp_path: Path) -> None:
    _write_map(tmp_path)
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: map.pgm\n"
        "      direction: cw\n" + _TRACKS_BLOCK,
    )
    with pytest.raises(ConfigError, match="start"):
        load_config(path)


def test_map_track_bad_direction_is_error(tmp_path: Path) -> None:
    _write_map(tmp_path)
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: map.pgm\n"
        "      direction: cwcc\n"
        "      start: [1, 1]\n" + _TRACKS_BLOCK,
    )
    with pytest.raises(ConfigError, match="'cw' or 'ccw'"):
        load_config(path)


def test_map_track_bad_start_is_error(tmp_path: Path) -> None:
    _write_map(tmp_path)
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: map.pgm\n"
        "      direction: cw\n"
        "      start: [1]\n" + _TRACKS_BLOCK,
    )
    with pytest.raises(ConfigError, match="start"):
        load_config(path)


def test_map_track_image_not_found(tmp_path: Path) -> None:
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: missing.pgm\n"
        "      direction: cw\n"
        "      start: [1, 1]\n" + _TRACKS_BLOCK,
    )
    with pytest.raises(ConfigError, match="not found"):
        load_config(path)


def test_map_track_declared_twice_is_error(tmp_path: Path) -> None:
    _write_map(tmp_path)
    path = _write_params(
        tmp_path,
        "maps:\n"
        "  tracks:\n"
        "    m1:\n"
        "      map: map.pgm\n"
        "      direction: cw\n"
        "      start: [1, 1]\n" + _TRACKS_BLOCK.replace("t1", "m1"),
    )
    with pytest.raises(ConfigError, match="'tracks' and 'maps'"):
        load_config(path)


def test_default_params_have_no_map_tracks() -> None:
    cfg = load_config(PARAMS)
    assert all(spec.map is None for spec in cfg.tracks.values())

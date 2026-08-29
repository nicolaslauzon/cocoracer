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

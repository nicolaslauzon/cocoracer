"""Structural tests for the single-file web front end (pytest has no browser).

The page is vanilla JS, so these check what a browser would need: the file
exists, pulls nothing from the network, talks to the same WebSocket path the
server serves, and references every field name the protocol actually emits.
The expected names are extracted from the serializers, so a key renamed in
``protocol.py`` fails here until the page is updated to match.
"""

import json
from pathlib import Path

from cocoracer.config import Config
from cocoracer.engine import RaceSnapshot, VehicleSnapshot, VehicleStatus
from cocoracer.track import Track
from cocoracer.web.protocol import build_dynamic_message, build_static_message

INDEX = Path(__file__).resolve().parent.parent / "cocoracer" / "web" / "index.html"

# Fields the page receives but deliberately does not display.
_UNUSED_DYNAMIC_FIELDS = {"scan"}


def _index_html() -> str:
    return INDEX.read_text(encoding="utf-8")


def _static_field_names(stadium: Track, config: Config) -> set[str]:
    msg = json.loads(build_static_message(stadium, config))
    names = set(msg)
    names.update(msg["vehicle"])
    names.update(msg["start_line"])
    return names


def _dynamic_field_names(stadium: Track) -> set[str]:
    vehicle = VehicleSnapshot(
        name="v0",
        id=0,
        status=VehicleStatus.RACING,
        x=0.0,
        y=0.0,
        yaw=0.0,
        speed=0.0,
        steering=0.0,
        laps_completed=0,
        best_lap=None,
        last_lap=None,
        crashes=0,
        finish_time=None,
        dnf_reason=None,
    )
    snap = RaceSnapshot(time=0.0, track=stadium, vehicles=(vehicle,))
    msg = json.loads(build_dynamic_message(snap, "racing", 0.0, [None]))
    names = set(msg)
    names.update(msg["vehicles"][0])
    return names - _UNUSED_DYNAMIC_FIELDS


def test_index_html_exists() -> None:
    assert INDEX.is_file()


def test_index_html_is_self_contained() -> None:
    html = _index_html()
    for token in ("<script src", "http://", "https://", "fetch(", "<link"):
        assert token not in html, token


def test_index_html_uses_a_canvas() -> None:
    html = _index_html()
    assert "<canvas" in html
    assert 'getContext("2d")' in html


def test_index_html_targets_the_websocket_path() -> None:
    assert '"/ws"' in _index_html()


def test_index_html_covers_static_protocol_fields(
    stadium: Track, config: Config
) -> None:
    html = _index_html()
    missing = {n for n in _static_field_names(stadium, config) if n not in html}
    assert not missing


def test_index_html_covers_dynamic_protocol_fields(stadium: Track) -> None:
    html = _index_html()
    missing = {n for n in _dynamic_field_names(stadium) if n not in html}
    assert not missing


def test_index_html_draws_the_pixel_art_sprite() -> None:
    sprite = Path(__file__).resolve().parent.parent / "cocoracer" / "web" / "f1-car.png"
    assert sprite.is_file()
    assert sprite.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    html = _index_html()
    assert "f1-car.png" in html
    assert "drawImage" in html
    assert "fillRect" not in html.split("function drawCar")[1].split("}")[0]


def test_index_html_renders_the_map_image(stadium: Track) -> None:
    html = _index_html()
    assert "map_image" in html
    assert "drawMapImage" in html
    assert "map_image" in _static_field_names(stadium, _any_config())
    # The map is sized in world meters times the pixels-per-metre view
    # scale, and recolored to the dark theme rather than shown raw.
    assert "recolorMap" in html
    assert "worldW * view.scale" in html
    assert "worldH * view.scale" in html


def test_index_html_rotates_the_sprite_to_point_forward() -> None:
    html = _index_html()
    assert "rotate(Math.PI / 2)" in html


def _any_config() -> Config:
    from cocoracer.config import (
        RaceConfig,
        SensorConfig,
        SimConfig,
        TrackSpec,
        VehicleConfig,
    )

    return Config(
        sim=SimConfig(),
        vehicle=VehicleConfig(),
        sensor=SensorConfig(),
        race=RaceConfig(),
        tracks={"s": TrackSpec(name="s", width=1.0, resolution=0.1)},
        baselines={},
        default_track="s",
    )


def test_index_html_has_start_button() -> None:
    html = _index_html()
    assert "<button" in html
    assert 'id="start"' in html


def test_index_html_sends_the_start_message() -> None:
    html = _index_html()
    assert "ws.send" in html
    assert 'type: "start"' in html


def test_index_html_keeps_trails_client_side(stadium: Track) -> None:
    html = _index_html()
    assert "drawTrails" in html
    assert "trail" not in _dynamic_field_names(stadium)


def test_index_html_colors_every_vehicle_status() -> None:
    html = _index_html()
    for status in VehicleStatus:
        assert status.value in html, status.value
    # Identity colors while racing: a fixed bright palette by grid order.
    assert "PALETTE" in html
    assert "colorFor" in html
    assert 'STATUS_COLORS["racing"]' not in html

"""Structural tests for the single-file web front end (pytest has no browser).

The page is vanilla JS, so these check what a browser would need: the file
exists, pulls nothing from the network, talks to the same WebSocket path the
server serves, and references every field name the protocol actually emits.
The expected names are extracted from the serializers, so a key renamed in
``protocol.py`` fails here until the page is updated to match.
"""

import json
from pathlib import Path

from cocoracer.engine import RaceSnapshot, VehicleSnapshot, VehicleStatus
from cocoracer.track import Track
from cocoracer.web.protocol import build_dynamic_message, build_static_message

INDEX = Path(__file__).resolve().parent.parent / "cocoracer" / "web" / "index.html"

# Fields the page receives but deliberately does not display.
_UNUSED_DYNAMIC_FIELDS = {"scan"}


def _index_html() -> str:
    return INDEX.read_text(encoding="utf-8")


def _static_field_names(stadium: Track) -> set[str]:
    msg = json.loads(build_static_message(stadium))
    names = set(msg)
    names.update(msg["grid"])
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


def test_index_html_covers_static_protocol_fields(stadium: Track) -> None:
    html = _index_html()
    missing = {n for n in _static_field_names(stadium) if n not in html}
    assert not missing


def test_index_html_covers_dynamic_protocol_fields(stadium: Track) -> None:
    html = _index_html()
    missing = {n for n in _dynamic_field_names(stadium) if n not in html}
    assert not missing


def test_index_html_colors_every_vehicle_status() -> None:
    html = _index_html()
    for status in VehicleStatus:
        assert status.value in html, status.value

"""Tests for the cocoracer CLI."""

import json
import queue
import shutil
import socket
import threading
import time
from pathlib import Path

import numpy as np
import pytest
import websockets.sync.client

from cocoracer.cli import _drain_starts, main
from cocoracer.config import Config
from cocoracer.controller import Controller
from cocoracer.engine import RaceEngine
from cocoracer.track import Track

REPO_ROOT = Path(__file__).resolve().parent.parent
STUB = REPO_ROOT / "controllers" / "open_loop.py"
PARAMS = REPO_ROOT / "params" / "default.yaml"


class Sitter(Controller):
    """Sits on the grid: zero speed, zero steer."""

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        return 0.0, 0.0


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _time_trial_argv(*extra: str) -> list[str]:
    return [
        "--params",
        str(PARAMS),
        "time-trial",
        "--track",
        "stadium",
        "--controller",
        str(STUB),
        *extra,
    ]


def test_time_trial_stub_dnf_headless(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(_time_trial_argv("--no-web"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "results (stadium):" in out
    assert "DNF" in out
    assert "crashes: 5" in out
    assert "[max crashes]" in out
    assert "race time:" in out


def _temp_params(tmp_path: Path, time_limit: float) -> Path:
    # Track and map paths are relative to the param file, so mirror the
    # repo layout (params/ beside maps/ and tracks/) under a temp dir.
    (tmp_path / "params").mkdir()
    shutil.copytree(PARAMS.parent / "tracks", tmp_path / "params" / "tracks")
    shutil.copytree(REPO_ROOT / "maps", tmp_path / "maps")
    text = PARAMS.read_text().replace("time_limit: 600.0", f"time_limit: {time_limit}")
    assert text != PARAMS.read_text()
    path = tmp_path / "params" / "params.yaml"
    path.write_text(text)
    return path


@pytest.mark.parametrize(
    "track_name", ("right-interior", "icra-2023-short", "icra-2025")
)
def test_time_trial_ticks_cleanly_on_map_track(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, track_name: str
) -> None:
    argv = [
        "--params",
        str(_temp_params(tmp_path, 5.0)),
        "time-trial",
        "--track",
        track_name,
        "--controller",
        str(REPO_ROOT / "controllers" / "starter.py"),
        "--no-web",
    ]
    rc = main(argv)
    out = capsys.readouterr().out
    assert rc == 0
    assert f"results ({track_name}):" in out
    assert "race time:" in out


def _send_start(port: int, done: threading.Event) -> None:
    """Connect to the live view and release the field with a start message."""
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        try:
            with websockets.sync.client.connect(
                f"ws://127.0.0.1:{port}/ws", max_size=32 * 1024 * 1024
            ) as ws:
                ws.recv()  # the static message arrives first
                ws.send(json.dumps({"type": "start"}))
            done.set()
            return
        except OSError:
            time.sleep(0.05)


def test_time_trial_live_starts_web_view_and_runs(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # A short time limit ends the stub's race fast in wall-clock pace.
    short = _temp_params(tmp_path, 4.0)
    port = _free_port()
    argv = _time_trial_argv("--port", str(port))
    argv[argv.index("--params") + 1] = str(short)
    started = threading.Event()
    client = threading.Thread(target=_send_start, args=(port, started), daemon=True)
    client.start()
    rc = main(argv)
    out = capsys.readouterr().out
    assert rc == 0
    assert started.is_set()
    assert f"web view: http://127.0.0.1:{port}" in out
    assert "(web view not implemented yet; running headless)" not in out
    assert "results (stadium):" in out
    assert "DNF" in out
    assert "[timeout]" in out


def test_drain_starts_first_wins_duplicates_ignored(
    stadium: Track, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = RaceEngine(stadium, config, [Sitter()], ["sitter"], auto_start=False)
    calls: list[int] = [0]
    release = engine.start

    def counting_release() -> None:
        calls[0] += 1
        release()

    monkeypatch.setattr(engine, "start", counting_release)
    start_queue: queue.Queue[None] = queue.Queue()
    for _ in range(3):
        start_queue.put(None)
    _drain_starts(start_queue, engine)
    assert calls[0] == 1
    assert engine.phase == "racing"
    assert start_queue.empty()
    _drain_starts(start_queue, engine)
    assert calls[0] == 1


def test_time_trial_rejects_two_controllers() -> None:
    argv = _time_trial_argv("--no-web")
    argv[argv.index("--controller") + 1] = f"{STUB},{STUB}"
    with pytest.raises(SystemExit, match="exactly one controller"):
        main(argv)


def test_time_trial_missing_controller_file() -> None:
    argv = _time_trial_argv("--no-web")
    argv[argv.index("--controller") + 1] = str(REPO_ROOT / "nope.py")
    with pytest.raises(SystemExit, match="not found"):
        main(argv)


def _race_argv(controller: str, params: Path = PARAMS) -> list[str]:
    return [
        "--params",
        str(params),
        "race",
        "--track",
        "stadium",
        "--controller",
        controller,
        "--no-web",
    ]


def test_race_runs_two_controllers_headless_and_prints_results(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # A short time limit ends the race fast: both stubs crash into the
    # wall on every pass and neither finishes.
    short = _temp_params(tmp_path, 8.0)
    rc = main(_race_argv(f"{STUB},{STUB}", short))
    out = capsys.readouterr().out
    assert rc == 0
    assert "results (stadium):" in out
    assert "open_loop (1)" in out
    assert "open_loop (2)" in out
    assert "[timeout]" in out
    assert "race time:" in out


def test_race_rejects_single_controller() -> None:
    with pytest.raises(SystemExit, match="two or more controllers"):
        main(_race_argv(str(STUB)))


def test_race_missing_controller_file() -> None:
    argv = _race_argv(f"{STUB},{REPO_ROOT / 'nope.py'}")
    with pytest.raises(SystemExit, match="not found"):
        main(argv)


def test_top_level_help_documents_params_and_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "--params" in out
    assert "time-trial" in out
    assert "race" in out


def test_time_trial_help_documents_options(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main(["time-trial", "--help"])
    out = capsys.readouterr().out
    for flag in ("--track", "--controller", "--laps", "--no-web", "--port"):
        assert flag in out


def test_race_help_documents_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["race", "--help"])
    out = capsys.readouterr().out
    for flag in ("--track", "--controller", "--laps", "--no-web", "--port"):
        assert flag in out

"""Tests for the cocoracer CLI."""

import shutil
import socket
from pathlib import Path

import pytest

from cocoracer.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
STUB = REPO_ROOT / "controllers" / "open_loop.py"
PARAMS = REPO_ROOT / "params" / "default.yaml"


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


def test_time_trial_live_starts_web_view_and_runs(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    # A short time limit ends the stub's race fast in wall-clock pace.
    shutil.copytree(PARAMS.parent / "tracks", tmp_path / "tracks")
    short = tmp_path / "params.yaml"
    text = PARAMS.read_text().replace("time_limit: 300.0", "time_limit: 4.0")
    assert text != PARAMS.read_text()
    short.write_text(text)
    port = _free_port()
    argv = _time_trial_argv("--port", str(port))
    argv[argv.index("--params") + 1] = str(short)
    rc = main(argv)
    out = capsys.readouterr().out
    assert rc == 0
    assert f"web view: http://127.0.0.1:{port}" in out
    assert "(web view not implemented yet; running headless)" not in out
    assert "results (stadium):" in out
    assert "DNF" in out
    assert "[timeout]" in out


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
    shutil.copytree(PARAMS.parent / "tracks", tmp_path / "tracks")
    short = tmp_path / "params.yaml"
    text = PARAMS.read_text().replace("time_limit: 300.0", "time_limit: 8.0")
    assert text != PARAMS.read_text()
    short.write_text(text)
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

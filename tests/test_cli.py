"""Tests for the cocoracer CLI."""

from pathlib import Path

import pytest

from cocoracer.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
STUB = REPO_ROOT / "controllers" / "open_loop.py"
PARAMS = REPO_ROOT / "params" / "default.yaml"


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


def test_time_trial_without_no_web_prints_headless_note(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(_time_trial_argv())
    out = capsys.readouterr().out
    assert rc == 0
    assert "(web view not implemented yet; running headless)" in out


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


def test_race_prints_not_implemented(capsys: pytest.CaptureFixture[str]) -> None:
    argv = [
        "--params",
        str(PARAMS),
        "race",
        "--track",
        "stadium",
        "--controller",
        f"{STUB},{STUB}",
        "--no-web",
    ]
    rc = main(argv)
    out = capsys.readouterr().out
    assert rc == 0
    assert "not implemented yet" in out

"""Tests for the player controller file loader."""

from pathlib import Path

import pytest

from cocoracer.controller import Controller, ControllerError, load_controller

_GOOD = """
import math

from cocoracer.controller import Controller

class Pilot(Controller):
    def step(self, x, y, yaw, speed, steering_angle):
        return 1.0 + 0.1 * math.sin(x), 0.0
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    file = tmp_path / name
    file.write_text(body)
    return file


def test_loads_single_concrete_controller(tmp_path: Path) -> None:
    file = _write(tmp_path, "pilot.py", _GOOD)
    ctl = load_controller(file)
    assert type(ctl) is not Controller
    assert isinstance(ctl, Controller)
    speed, steer = ctl.step(0.0, 0.0, 0.0, 1.0, 0.0)
    assert speed == 1.0
    assert steer == 0.0


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ControllerError, match="not found"):
        load_controller(tmp_path / "nope.py")


def test_rejects_module_without_controller(tmp_path: Path) -> None:
    file = _write(tmp_path, "empty.py", "VALUE = 1\n")
    with pytest.raises(ControllerError, match="exactly one"):
        load_controller(file)


def test_rejects_module_with_two_controllers(tmp_path: Path) -> None:
    file = _write(
        tmp_path,
        "two.py",
        _GOOD
        + "class Second(Controller):\n    def step(self, x, y, yaw, speed, steering_angle):\n        return 0.0, 0.0\n",
    )
    with pytest.raises(ControllerError, match="exactly one"):
        load_controller(file)


def test_rejects_controller_needing_arguments(tmp_path: Path) -> None:
    file = _write(
        tmp_path,
        "args.py",
        """
from cocoracer.controller import Controller

class NeedsArgs(Controller):
    def __init__(self, k: float) -> None:
        self.k = k

    def step(self, x, y, yaw, speed, steering_angle):
        return self.k, 0.0
""",
    )
    with pytest.raises(ControllerError, match="no arguments"):
        load_controller(file)


def test_rejects_non_concrete_controller(tmp_path: Path) -> None:
    file = _write(
        tmp_path,
        "lazy.py",
        """
from cocoracer.controller import Controller

class Lazy(Controller):
    pass
""",
    )
    with pytest.raises(ControllerError, match="not concrete"):
        load_controller(file)


def test_rejects_module_that_fails_to_import(tmp_path: Path) -> None:
    file = _write(tmp_path, "broken.py", "import missing_module_xyz\n")
    with pytest.raises(ControllerError, match="error importing"):
        load_controller(file)

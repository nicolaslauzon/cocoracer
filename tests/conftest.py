from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

from cocoracer.config import Config, load_config
from cocoracer.track import Track, build_track

PARAMS = Path(__file__).resolve().parent.parent / "params" / "default.yaml"


@pytest.fixture(scope="session")
def config() -> Config:
    return load_config(PARAMS)


@pytest.fixture(scope="session")
def stadium(config: Config) -> Track:
    return build_track(config.tracks["stadium"])


@pytest.fixture(scope="session")
def f1_tracks(config: Config) -> dict[str, Track]:
    names = ("montreal", "spa", "silverstone")
    return {name: build_track(config.tracks[name]) for name in names}


@pytest.fixture
def synthetic_track_factory() -> Callable[[np.ndarray], Track]:
    """Builds a Track around a hand-made occupancy grid (0.1 m cells)."""

    def make(occupied: np.ndarray) -> Track:
        ny, nx = occupied.shape
        spline = CubicSpline([0.0, 1.0], [0.0, 1.0])
        corners = np.array(
            [
                [0.0, 0.0],
                [nx * 0.1, 0.0],
                [nx * 0.1, ny * 0.1],
                [0.0, ny * 0.1],
                [0.0, 0.0],
            ]
        )
        return Track(
            name="synthetic",
            width=1.0,
            resolution=0.1,
            track_length=10.0,
            centerline=np.zeros((2, 3)),
            left_wall=corners.copy(),
            right_wall=corners.copy(),
            spline_x=spline,
            spline_y=spline,
            grid_origin=(0.0, 0.0),
            grid_shape=(ny, nx),
            occupied=occupied,
            frenet_tree=cKDTree(np.zeros((1, 2))),
            frenet_s=np.zeros(1),
        )

    return make

from pathlib import Path

import pytest

from cocoracer.config import Config, load_config
from cocoracer.track import Track, build_track

PARAMS = Path(__file__).resolve().parent.parent / "params" / "default.yaml"


@pytest.fixture(scope="session")
def config() -> Config:
    return load_config(PARAMS)


@pytest.fixture(scope="session")
def stadium(config: Config) -> Track:
    return build_track(config.tracks["stadium"])

from dataclasses import dataclass
from flax import struct


@dataclass
class Pose:
    x_m: float
    y_m: float
    heading_rad: float


@struct.dataclass
class Param:
    """
    Default jittable params for dynamics
    """

    lf: float = 0.15875  # Distance from center of gravity to front axle
    lr: float = 0.17145  # Distance from center of gravity to rear axle
    s_min: float = -0.5  # Minimum steering angle constraint
    s_max: float = 0.5  # Maximum steering angle constraint
    sv_min: float = -3.2  # Minimum steering velocity constraint
    sv_max: float = 3.2  # Maximum steering velocity constraint
    a_max: float = 9.51  # Maximum longitudinal acceleration
    v_min: float = -5.0  # Minimum longitudinal velocity
    v_max: float = 20.0  # Maximum longitudinal velocity
    timestep: float = 0.025 / 4.0  # physical time steps of the dynamics model
    timestep_ratio: int = 4  # number of simulation steps per control step

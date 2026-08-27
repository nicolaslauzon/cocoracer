"""Batched JAX kinematic bicycle dynamics.

`Dynamics.step(states, commands)` is the public interface. `states` is an
(N, 5) array with columns x, y, yaw, speed, steering; `commands` is an
(N, 2) array with columns target speed, target steering; the result is an
(N, 5) array in the same column order as `states`.

Internally the kernel packs both into one (N, 7) array — x, y, yaw, speed,
steering, target speed, target steering — and integrates every vehicle for
one tick using RK4 substeps, with acceleration, speed, steering-angle,
and steering-rate constraints from the vehicle config.

Speed and steering follow their targets at the configured rates. That
part is integrated in closed form per substep (move-toward), because a
discontinuous rate-limit derivative would break RK4 stages that land on
the target. The position and heading then get a standard RK4 step using
the linear speed/steering profile inside the substep.
"""

from dataclasses import dataclass
from functools import partial

import jax
import jax.numpy as jnp
import numpy as np

from cocoracer.config import VehicleConfig

X, Y, YAW, SPEED, STEER, TARGET_SPEED, TARGET_STEER = range(7)

_WHEELBASE = 0
_MIN_SPEED = 1
_MAX_SPEED = 2
_MAX_ACCEL = 3
_MIN_STEER = 4
_MAX_STEER = 5
_MAX_STEER_RATE = 6
_MIN_STEER_RATE = 7
_SUBSTEP_DT = 8


@dataclass(frozen=True)
class DynamicsParams:
    wheelbase: float
    min_speed: float
    max_speed: float
    max_accel: float
    min_steer: float
    max_steer: float
    max_steer_rate: float
    min_steer_rate: float
    substep_dt: float

    @classmethod
    def from_config(
        cls, vehicle: VehicleConfig, tick_dt: float, substeps: int
    ) -> "DynamicsParams":
        return cls(
            wheelbase=vehicle.wheelbase,
            min_speed=vehicle.min_speed,
            max_speed=vehicle.max_speed,
            max_accel=vehicle.max_accel,
            min_steer=vehicle.min_steer,
            max_steer=vehicle.max_steer,
            max_steer_rate=vehicle.max_steer_rate,
            min_steer_rate=vehicle.min_steer_rate,
            substep_dt=tick_dt / substeps,
        )

    def as_array(self) -> np.ndarray:
        return np.array(
            [
                self.wheelbase,
                self.min_speed,
                self.max_speed,
                self.max_accel,
                self.min_steer,
                self.max_steer,
                self.max_steer_rate,
                self.min_steer_rate,
                self.substep_dt,
            ]
        )


def _substep(s: jnp.ndarray, p: jnp.ndarray) -> jnp.ndarray:
    dt = p[_SUBSTEP_DT]
    speed0, steer0 = s[:, SPEED], s[:, STEER]
    target_speed = jnp.clip(s[:, TARGET_SPEED], p[_MIN_SPEED], p[_MAX_SPEED])
    target_steer = jnp.clip(s[:, TARGET_STEER], p[_MIN_STEER], p[_MAX_STEER])
    speed1 = speed0 + jnp.clip(
        target_speed - speed0, -p[_MAX_ACCEL] * dt, p[_MAX_ACCEL] * dt
    )
    steer1 = steer0 + jnp.clip(
        target_steer - steer0, p[_MIN_STEER_RATE] * dt, p[_MAX_STEER_RATE] * dt
    )
    dv = (speed1 - speed0) / dt
    dd = (steer1 - steer0) / dt

    def kin(
        t: jnp.ndarray, x: jnp.ndarray, y: jnp.ndarray, yaw: jnp.ndarray
    ) -> jnp.ndarray:
        v = speed0 + dv * t
        steer = steer0 + dd * t
        return jnp.stack(
            [v * jnp.cos(yaw), v * jnp.sin(yaw), v * jnp.tan(steer) / p[_WHEELBASE]],
            axis=1,
        )

    x, y, yaw = s[:, X], s[:, Y], s[:, YAW]
    k1 = kin(0.0 * dt, x, y, yaw)
    k2 = kin(
        0.5 * dt,
        x + 0.5 * dt * k1[:, 0],
        y + 0.5 * dt * k1[:, 1],
        yaw + 0.5 * dt * k1[:, 2],
    )
    k3 = kin(
        0.5 * dt,
        x + 0.5 * dt * k2[:, 0],
        y + 0.5 * dt * k2[:, 1],
        yaw + 0.5 * dt * k2[:, 2],
    )
    k4 = kin(dt, x + dt * k3[:, 0], y + dt * k3[:, 1], yaw + dt * k3[:, 2])
    inc = (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    yaw1 = (yaw + inc[:, 2] + jnp.pi) % (2.0 * jnp.pi) - jnp.pi
    return jnp.stack(
        [
            x + inc[:, 0],
            y + inc[:, 1],
            yaw1,
            speed1,
            steer1,
            s[:, TARGET_SPEED],
            s[:, TARGET_STEER],
        ],
        axis=1,
    )


@partial(jax.jit, static_argnums=(3,))
def _integrate_tick(
    states: jnp.ndarray,
    commands: jnp.ndarray,
    params: jnp.ndarray,
    substeps: int,
) -> jnp.ndarray:
    s = jnp.concatenate([states, commands], axis=1)
    for _ in range(substeps):
        s = _substep(s, params)
    return s[:, :5]


class Dynamics:
    """Batched kinematic bicycle model; one jitted call per tick."""

    def __init__(self, params: DynamicsParams, substeps: int) -> None:
        self._params_arr = jnp.asarray(params.as_array())
        self._substeps = substeps

    def warmup(self, n_vehicles: int) -> None:
        """Pre-compile the jitted kernel for every fleet size 1..n_vehicles.

        Vehicles leave the batch when they finish or DNF, so every smaller
        shape must already be compiled or the mid-race tick would stall.
        """
        for n in range(1, n_vehicles + 1):
            dummy_states = jnp.zeros((n, 5))
            dummy_commands = jnp.zeros((n, 2))
            _integrate_tick(
                dummy_states, dummy_commands, self._params_arr, self._substeps
            )

    def step(self, states: np.ndarray, commands: np.ndarray) -> np.ndarray:
        """Integrate all vehicles by one tick."""
        result = _integrate_tick(
            jnp.asarray(states),
            jnp.asarray(commands),
            self._params_arr,
            self._substeps,
        )
        return np.asarray(result)

import jax
from copy import deepcopy
import matplotlib.pyplot as plt
from typing import Callable
import jax.numpy as jnp
import chex
from functools import partial
from custom_types import Param


@partial(jax.jit, static_argnums=[0, 2])
def integrate_rk4(f: Callable, x_and_u: chex.Array, params: Param) -> chex.Array:
    for _ in range(params.timestep_ratio):
        k1 = f(x_and_u, params)
        k2_state = x_and_u + params.timestep * (k1 / 2)
        k2 = f(k2_state, params)
        k3_state = x_and_u + params.timestep * (k2 / 2)
        k3 = f(k3_state, params)
        k4_state = x_and_u + params.timestep * k3
        k4 = f(k4_state, params)
        # dynamics integration
        x_and_u = x_and_u + params.timestep * (1 / 6) * (k1 + 2 * k2 + 2 * k3 + k4)
        x_and_u = x_and_u.at[4].set(
            jnp.arctan2(jnp.sin(x_and_u[4]), jnp.cos(x_and_u[4]))
        )
    return x_and_u


@partial(jax.jit, static_argnums=[2, 3, 4])
def accl_constraints(vel, a_long_d, a_max, v_min, v_max):
    """
    Apply velocity and acceleration bounds to desired acceleration.

    Parameters
    ----------
    vel : float
        Current vehicle speed.
    a_long_d : float
        Unconstrained desired longitudinal acceleration.
    a_max : float
        Maximum acceleration magnitude.
    v_min : float
        Minimum allowed velocity.
    v_max : float
        Maximum allowed velocity.

    Returns
    -------
    float
        Bounded longitudinal acceleration.
    """

    # if (vel <= v_min and a_long_d <= 0) or (vel >= v_max and a_long_d >= 0):
    #     a_long = 0.0
    # elif a_long_d <= -a_max:
    #     a_long = -a_max
    # else:
    #     a_long = a_long_d

    a_long = jnp.select(
        [
            jnp.logical_or(
                jnp.logical_and(vel <= v_min, a_long_d <= 0),
                jnp.logical_and(vel >= v_max, a_long_d >= 0),
            ),
            (a_long_d <= -a_max),
        ],
        [0.0, -a_max],
        a_long_d,
    )

    return a_long


@partial(jax.jit, static_argnums=[2, 3, 4, 5])
def steering_constraint(
    steering_angle, steering_velocity, s_min, s_max, sv_min, sv_max
):
    """
    Apply steering angle and steering-rate bounds.

    Parameters
    ----------
    steering_angle : float
        Current front-wheel steering angle.
    steering_velocity : float
        Unconstrained desired steering velocity.
    s_min : float
        Minimum steering angle.
    s_max : float
        Maximum steering angle.
    sv_min : float
        Minimum steering velocity.
    sv_max : float
        Maximum steering velocity.

    Returns
    -------
    float
        Bounded steering velocity.
    """

    # constraint steering velocity
    # if (steering_angle <= s_min and steering_velocity <= 0) or (
    #     steering_angle >= s_max and steering_velocity >= 0
    # ):
    #     steering_velocity = 0.0
    # elif steering_velocity <= sv_min:
    #     steering_velocity = sv_min
    # elif steering_velocity >= sv_max:
    #     steering_velocity = sv_max

    steering_velocity = jnp.select(
        [
            jnp.logical_or(
                jnp.logical_and(steering_angle <= s_min, steering_velocity <= 0),
                jnp.logical_and(steering_angle >= s_max, steering_velocity >= 0),
            ),
            (steering_velocity <= sv_min),
            (steering_velocity >= sv_max),
        ],
        [0.0, sv_min, sv_max],
        steering_velocity,
    )
    return steering_velocity


@partial(jax.jit, static_argnums=[1])
def vehicle_dynamics_ks(x_and_u: chex.Array, params: Param) -> chex.Array:
    """
    Evaluate the kinematic single-track model.

    The implementation follows section 5 of the CommonRoad vehicle models
    reference.

    Parameters
    ----------
    x_and_u : chex.Array, shape (7,)
        State and control vector
        ``[x, y, delta, v, psi, steering_angle_cmd, speed_cmd]``.
    Returns
    -------
    chex.Array, shape (7,)
        Right-hand side of the kinematic differential equations with two dummy
        control dimensions appended.
    """
    DELTA = x_and_u[2]
    V = x_and_u[3]
    PSI = x_and_u[4]
    # wheelbase
    lwb = params.lf + params.lr

    # control type
    STEER_VEL = (x_and_u[5] - DELTA) / params.timestep
    ACCL = (x_and_u[6] - V) / params.timestep

    # Controls w/ constraints
    STEER_VEL = steering_constraint(
        DELTA, STEER_VEL, params.s_min, params.s_max, params.sv_min, params.sv_max
    )
    ACCL = accl_constraints(V, ACCL, params.a_max, params.v_min, params.v_max)

    # system dynamics
    f = jnp.array(
        [
            V * jnp.cos(PSI),  # X_DOT
            V * jnp.sin(PSI),  # Y_DOT
            STEER_VEL,  # DELTA_DOT
            ACCL,  # V_DOT
            (V / lwb) * jnp.tan(DELTA),  # PSI_DOT
            0.0,  # dummy dim
            0.0,  # dummy dim
        ]
    )
    return f

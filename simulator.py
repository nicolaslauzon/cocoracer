from custom_types import Pose, Param
import matplotlib.pyplot as plt
import time
import numpy as np
from frenet_converter import FrenetConverter
import jax
import chex
from vehicule_models import vehicle_dynamics_ks, integrate_rk4
import jax.numpy as jnp
from functools import partial
import threading


class Simulator:
    def __init__(self, centerline: list[Pose]):
        self.centerline: list[Pose] = centerline
        self.frenet_converter: FrenetConverter = FrenetConverter(centerline)
        self.params = Param()

        # State vector layout: [x, y, delta, v, psi, steering_angle_cmd, speed_cmd]
        self.x_and_u = jnp.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        self.lock = threading.Lock()
        self.is_running = False

    @partial(jax.jit, static_argnums=[0])
    def step_sim(self, x_and_u: chex.Array) -> chex.Array:
        """
        Parameters
        ----------
        x_and_u : chex.Array, shape (7,) -> [x, y, delta, v, psi, steering_angle_cmd, speed_cmd]
        """
        new_x_and_u = integrate_rk4(vehicle_dynamics_ks, x_and_u, self.params)
        return new_x_and_u

    def set_control_cmd(self, steering_angle_cmd: float, speed_cmd: float):
        with self.lock:
            self.x_and_u = self.x_and_u.at[5:].set([steering_angle_cmd, speed_cmd])

    def get_state(self) -> np.ndarray:
        with self.lock:
            return np.array(self.x_and_u)

    def run_sim(self):
        self.is_running = True

        dt = 1.0 / 40.0  # 0.025 seconds
        next_time = time.perf_counter()

        print("Simulation loop started at 40Hz...")

        while self.is_running:
            with self.lock:
                current_state = self.x_and_u

            next_state = self.step_sim(current_state)

            with self.lock:
                self.x_and_u = next_state.at[5:].set(self.x_and_u[5:])

            next_time += dt
            sleep_time = next_time - time.perf_counter()

            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_time = time.perf_counter()

    def stop(self):
        self.is_running = False


if __name__ == "__main__":
    # Mocking a trivial straight centerline for instantiation requirements
    from custom_types import Pose

    dummy_centerline = [Pose(i * 0.1, 0.0, 0.0) for i in range(100)]

    # 1. Instantiate the simulator
    sim = Simulator(dummy_centerline)

    # 2. Spin up the background thread for execution loop
    sim_thread = threading.Thread(target=sim.run_sim, daemon=True)
    sim_thread.start()

    # Give JAX an instant to compile on its first step pass
    time.sleep(0.2)

    # 3. Simulate asynchronous environment interactions over time
    xs, ys = [], []
    print("Sending driving commands...")

    # Set initial run command: Speed = 2.0 m/s, Steering = 0.05 rad
    sim.set_control_cmd(steering_angle_cmd=0.05, speed_cmd=2.0)

    for step in range(40 * 5):  # Monitor tracking data for 5 seconds
        state = sim.get_state()
        xs.append(state[0])
        ys.append(state[1])

        # At the 2-second mark, sharp turn right
        if step == 40 * 2:
            print("Changing command dynamically via callback: Hard right turn!")
            sim.set_control_cmd(steering_angle_cmd=-0.2, speed_cmd=4.0)

        time.sleep(1.0 / 40.0)

    # Clean shutdown
    sim.stop()
    sim_thread.join()

    # Plot results
    plt.figure(figsize=(6, 6))
    plt.plot(xs, ys, label="Vehicle Path", color="blue")
    plt.axis("equal")
    plt.grid(True)
    plt.xlabel("X Position [m]")
    plt.ylabel("Y Position [m]")
    plt.legend()
    plt.show()

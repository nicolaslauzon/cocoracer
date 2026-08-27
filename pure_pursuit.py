import math
from simulator import Simulator
from map_gen import level_3, display_racetrack, generate_map
import threading
import time
import numpy as np
import matplotlib.pyplot as plt


class PurePursuitController:
    def __init__(
        self, waypoints_xy: np.ndarray, wheelbase=0.32, max_steer=0.5, a=0.3, b=1.0
    ):
        self.wp_xy = np.asarray(waypoints_xy, dtype=np.float64)
        self.L_b = wheelbase
        self.max_steer = max_steer
        self.a = a  # Lookahead speed slope factor
        self.b = b  # Lookahead constant offset
        self.target_speed = 1.0  # Target constant speed constraint

    def compute_steering(
        self, x: float, y: float, yaw: float, current_speed: float
    ) -> float:
        L_f = np.clip(current_speed * self.a + self.b, 0.4, 4.0)

        dists = np.hypot(self.wp_xy[:, 0] - x, self.wp_xy[:, 1] - y)
        valid_indices = np.where(dists >= L_f)[0]

        target_idx = valid_indices[np.argmin(dists[valid_indices])]

        goal_g = self.wp_xy[target_idx]

        dx, dy = goal_g[0] - x, goal_g[1] - y
        cos_y, sin_y = math.cos(yaw), math.sin(yaw)

        y_local = -dx * sin_y + dy * cos_y

        if abs(L_f) > 1e-5:
            steering_angle = math.atan((2.0 * y_local * self.L_b) / (L_f**2))
        else:
            steering_angle = 0.0

        return float(np.clip(steering_angle, -self.max_steer, self.max_steer))


def run_controller_loop(
    sim: Simulator, controller: PurePursuitController, duration: float, history: list
):
    """The clean standalone control thread ticking at 40Hz."""
    dt = 1.0 / 40.0
    next_time = time.perf_counter()
    end_time = next_time + duration

    print("Controller loop active...")
    while time.perf_counter() < end_time and sim.is_running:
        # 1. Direct memory fetch of current state
        state = sim.get_state()
        car_x, car_y, _, current_speed, car_yaw = (
            state[0],
            state[1],
            state[2],
            state[3],
            state[4],
        )

        # Log path to the shared history list for real-time visualization
        history.append((car_x, car_y))

        # 2. Compute steering command
        steer_cmd = controller.compute_steering(car_x, car_y, car_yaw, current_speed)

        # 3. Direct write back to vehicle control command parameters
        sim.set_control_cmd(
            steering_angle_cmd=steer_cmd, speed_cmd=controller.target_speed
        )

        # 4. Accurate rate execution management
        next_time += dt
        sleep_time = next_time - time.perf_counter()
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            next_time = time.perf_counter()


if __name__ == "__main__":
    # 1. Generate and sanitize track
    track_centerline = level_3()
    map = generate_map(track_centerline)
    display_racetrack(track_centerline, map)

    xy = np.array([[pose.x_m, pose.y_m] for pose in track_centerline])

    diffs = np.diff(xy, axis=0)
    dists = np.hypot(diffs[:, 0], diffs[:, 1])

    keep_mask = np.ones(len(track_centerline), dtype=bool)
    keep_mask[1:] = dists > 1e-4

    cleaned_centerline = [
        pose for i, pose in enumerate(track_centerline) if keep_mask[i]
    ]

    # 2. Start Simulator Thread
    sim = Simulator(cleaned_centerline)
    sim_thread = threading.Thread(target=sim.run_sim, daemon=True)
    sim_thread.start()

    # 3. Initialize Controller
    controller = PurePursuitController(waypoints_xy=xy, wheelbase=0.32)

    # Thread-safe shared container for vehicle position tracking
    vehicle_history = []
    sim_duration = 60.0

    # 4. Start Controller Loop in its OWN background thread
    control_thread = threading.Thread(
        target=run_controller_loop,
        args=(sim, controller, sim_duration, vehicle_history),
        daemon=True,
    )
    control_thread.start()

    # ==========================================
    # REAL-TIME VISUALIZATION (Main Thread Only)
    # ==========================================
    plt.ion()  # Turn on Matplotlib interactive mode
    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot static track centerline
    ax.plot(xy[:, 0], xy[:, 1], "k--", label="Global Centerline Track")

    # Create empty plot elements for dynamic updates
    (path_line,) = ax.plot([], [], "r-", label="Simulated Vehicle Path")
    (car_dot,) = ax.plot([], [], "go", markersize=8, label="Current Position")

    ax.axis("equal")
    ax.grid(True)
    ax.legend(loc="upper right")
    ax.set_title("Pure Pursuit Tracking - Real-time Diagnostics")

    # Keep visualization looping while the control thread is alive
    while control_thread.is_alive():
        if len(vehicle_history) > 0:
            # Extract current history snapshot
            current_path = np.array(vehicle_history)
            x_data = current_path[:, 0]
            y_data = current_path[:, 1]

            # Update data arrays for the lines without re-drawing the whole figure
            path_line.set_data(x_data, y_data)
            car_dot.set_data([x_data[-1]], [y_data[-1]])

            # Dynamically handle axis limits if the car wanders out of bounds
            ax.relim()
            ax.autoscale_view()

            # Flush GUI events to refresh screen canvas
            fig.canvas.draw()
            fig.canvas.flush_events()

        time.sleep(0.05)  # Refresh UI at ~20 FPS to keep CPU load low

    # Clean shut down of simulator
    print("Simulation complete. Cleaning up...")
    sim.is_running = False
    sim_thread.join()
    control_thread.join()

    # Leave the plot open after the simulation run finishes
    plt.ioff()
    plt.show()

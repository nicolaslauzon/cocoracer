import sys
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from pynput import keyboard
from vehicule_models import Env
import jax
import jax.numpy as jnp

# Global variables to track the user's live commands
# These are modified by the keyboard listener and read by the simulation loop
target_steering = 0.0
target_speed = 0.0


def on_press(key):
    """Callback function that updates commands when keys are pressed."""
    global target_steering, target_speed
    try:
        if key.char == "w":
            target_speed = min(
                target_speed + 0.5, 15.0
            )  # Increase speed, cap at 15 m/s
        elif key.char == "s":
            target_speed = max(target_speed - 0.5, -3.0)  # Decrease speed / reverse
        elif key.char == "a":
            target_steering = min(
                target_steering + 0.05, 0.4
            )  # Steer left, cap at ~23 deg
        elif key.char == "d":
            target_steering = max(target_steering - 0.05, -0.4)  # Steer right
    except AttributeError:
        # Handle special keys (like arrow keys or escape) if pressed
        if key == keyboard.Key.esc:
            print("\nExiting Teleop...")
            sys.exit(0)


def on_release(key):
    """Optional: Center steering when turning keys are released."""
    global target_steering
    try:
        if key.char in ["a", "d"]:
            target_steering = 0.0  # Snap wheels back to center
    except AttributeError:
        pass


if __name__ == "__main__":
    env = Env()

    # Initial state: [x, y, delta, v, psi, steering_cmd, speed_cmd]
    # We explicitly start with 0.0 control commands
    x_and_u = jnp.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    # History lists to hold the trajectory coordinates for plotting
    xs, ys = [0.0], [0.0]

    # 1. Start the keyboard listener in a background thread
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # 2. Set up the Matplotlib interactive plot
    fig, ax = plt.subplots(figsize=(7, 7))
    (line,) = ax.plot([], [], "b-", lw=2, label="Vehicle Path")
    (current_pos,) = ax.plot([], [], "ro", markersize=6, label="Current Position")

    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.set_xlabel("X Position (meters)")
    ax.set_ylabel("Y Position (meters)")
    ax.set_title("WASD Robot Teleoperation Control (Close window or press ESC to exit)")
    ax.grid(True)
    ax.legend(loc="upper left")

    # Text overlay to show current teleop telemetry on screen
    telemetry_text = ax.text(
        0.02, 0.05, "", transform=ax.transAxes, bbox=dict(facecolor="white", alpha=0.7)
    )

    print("==========================================")
    print("  TELEOP CONTROLS ACTIVE (100Hz Control)")
    print("  W / S : Increase / Decrease Target Speed")
    print("  A / D : Steer Left / Right")
    print("  ESC   : Quit Application")
    print("==========================================")

    # 3. Define the core update loop for the animation
    def update(frame):
        global x_and_u, target_steering, target_speed

        # Inject the live global keyboard inputs into the control command slots ([5] and [6])
        x_and_u = x_and_u.at[5].set(target_steering)
        x_and_u = x_and_u.at[6].set(target_speed)

        # Step the JAX model 10ms forward into the future
        x_and_u = env.step_env(x_and_u)

        # Extract current physical coordinates
        curr_x = float(x_and_u[0])
        curr_y = float(x_and_u[1])
        curr_v = float(x_and_u[3])
        curr_delta = float(x_and_u[2])

        # Append to history arrays
        xs.append(curr_x)
        ys.append(curr_y)

        # Update plotting elements
        line.set_data(xs, ys)
        current_pos.set_data([curr_x], [curr_y])

        # Dynamically auto-scale the camera bounds so the car never drives off-screen
        margin = 5.0
        ax.set_xlim(min(xs) - margin, max(xs) + margin)
        ax.set_ylim(min(ys) - margin, max(ys) + margin)

        # Update text HUD
        telemetry_text.set_text(
            f"Cmd Speed: {target_speed:.1f} m/s | Act Speed: {curr_v:.1f} m/s\n"
            f"Cmd Steer: {target_steering:.2f} rad | Act Steer: {curr_delta:.2f} rad"
        )

        return line, current_pos, telemetry_text

    # 4. Bind the update function to Matplotlib's loop
    # interval=10 means this loop triggers every 10 milliseconds (100Hz)
    ani = FuncAnimation(fig, update, interval=10, blit=False, cache_frame_data=False)
    plt.show()

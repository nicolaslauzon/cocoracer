import numpy as np
import matplotlib.pyplot as plt
from custom_types import Pose

STEP_BETWEEN_POSE_M = 1.0
STEP_BETWEEN_POSE_DEG = 15.0
MAP_RESOLUTION_M = 0.1
TRACK_WIDTH_M = 0.5


def make_turn(radius_m: float, angle_deg: float, centerline: list[Pose]) -> list[Pose]:
    last_pose = centerline[-1]

    steps_rad = np.sign(angle_deg) * np.arange(
        0.0,
        np.deg2rad(np.abs(angle_deg)) + np.deg2rad(STEP_BETWEEN_POSE_DEG),
        np.deg2rad(STEP_BETWEEN_POSE_DEG),
    )

    circle_center_x_m = last_pose.x_m + np.sign(angle_deg) * radius_m * np.cos(
        last_pose.heading_rad + np.pi / 2
    )
    circle_center_y_m = last_pose.y_m + np.sign(angle_deg) * radius_m * np.sin(
        last_pose.heading_rad + np.pi / 2
    )

    for step_rad in steps_rad:
        x_m = circle_center_x_m - np.sign(angle_deg) * radius_m * np.cos(
            last_pose.heading_rad + step_rad + np.pi / 2
        )
        y_m = circle_center_y_m - np.sign(angle_deg) * radius_m * np.sin(
            last_pose.heading_rad + step_rad + np.pi / 2
        )
        heading_rad = last_pose.heading_rad + step_rad

        centerline.append(Pose(x_m, y_m, heading_rad))

    return centerline


def make_straight_line(lenght_m: float, centerline: list[Pose]) -> list[Pose]:
    last_pose = centerline[-1]

    steps = np.arange(0.0, lenght_m, STEP_BETWEEN_POSE_M)

    for step in steps:
        x_m = last_pose.x_m + np.cos(last_pose.heading_rad) * step
        y_m = last_pose.y_m + np.sin(last_pose.heading_rad) * step

        centerline.append(Pose(x_m, y_m, last_pose.heading_rad))

    return centerline


def generate_map(centerline: list[Pose]) -> np.ndarray:
    centerline_xs = np.array([pose.x_m for pose in centerline])
    centerline_ys = np.array([pose.y_m for pose in centerline])

    min_x = np.min(centerline_xs) - TRACK_WIDTH_M
    max_x = np.max(centerline_xs) + TRACK_WIDTH_M
    min_y = np.min(centerline_ys) - TRACK_WIDTH_M
    max_y = np.max(centerline_ys) + TRACK_WIDTH_M

    x_coords = np.arange(min_x, max_x + MAP_RESOLUTION_M, MAP_RESOLUTION_M)
    y_coords = np.arange(min_y, max_y + MAP_RESOLUTION_M, MAP_RESOLUTION_M)

    grid_x, grid_y = np.meshgrid(x_coords, y_coords, indexing="xy")

    occupancy_map = np.zeros(grid_x.shape, dtype=np.uint8)

    dx = grid_x[:, :, np.newaxis] - centerline_xs
    dy = grid_y[:, :, np.newaxis] - centerline_ys

    distances_to_centerline = np.sqrt(dx**2 + dy**2)
    min_distances = np.min(distances_to_centerline, axis=2)

    occupancy_map[min_distances > TRACK_WIDTH_M] = 1

    return occupancy_map


def display_racetrack(centerline: list[Pose], occupancy_map: np.ndarray):
    centerline_xs = [pose.x_m for pose in centerline]
    centerline_ys = [pose.y_m for pose in centerline]

    min_x = np.min(centerline_xs) - TRACK_WIDTH_M
    max_x = np.max(centerline_xs) + TRACK_WIDTH_M
    min_y = np.min(centerline_ys) - TRACK_WIDTH_M
    max_y = np.max(centerline_ys) + TRACK_WIDTH_M

    plt.figure(figsize=(8, 8))
    plt.imshow(
        occupancy_map,
        cmap="binary",
        origin="lower",
        extent=[min_x, max_x, min_y, max_y],
    )
    plt.plot(
        centerline_xs, centerline_ys, color="red", linewidth=1.5, label="Centerline"
    )
    plt.axis("equal")
    plt.xlabel("x [m]")
    plt.ylabel("y [m]")
    plt.legend()
    plt.show()


def level_1():
    initial_pose = Pose(0.0, 0.0, 0.0)
    centerline: list[Pose] = []
    centerline.append(initial_pose)

    centerline = make_straight_line(10.0, centerline)
    return centerline


def level_2():
    initial_pose = Pose(0.0, 0.0, 0.0)
    centerline: list[Pose] = []
    centerline.append(initial_pose)

    centerline = make_straight_line(4.0, centerline)
    centerline = make_turn(2.0, 180.0, centerline)
    centerline = make_straight_line(4.0, centerline)
    centerline = make_turn(2.0, 180.0, centerline)
    return centerline


def level_3():
    initial_pose = Pose(0.0, 0.0, 0.0)
    centerline: list[Pose] = []
    centerline.append(initial_pose)

    centerline = make_straight_line(4.0, centerline)
    centerline = make_turn(2.0, 45.0, centerline)
    centerline = make_turn(2.0, -45.0, centerline)
    centerline = make_turn(3.0, 225.0, centerline)
    centerline = make_turn(2.0, -90.0, centerline)
    centerline = make_straight_line(6.0, centerline)
    centerline = make_turn(1.0, 225.0, centerline)
    centerline = make_turn(1.0, -45.0, centerline)
    centerline = make_straight_line(1.0, centerline)

    return centerline


if __name__ == "__main__":
    centerline = level_3()
    map = generate_map(centerline)

    display_racetrack(centerline, map)

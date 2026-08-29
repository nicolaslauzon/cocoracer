# Slow tests (>20s)

| Test | Cost | Components |
|------|------|------------|
| test_wall_follow.py::test_wall_follow_finishes_three_laps_clean | 149s | engine.py, vehicle.py, track.py, controllers/wall_follow.py |
| test_perf.py::test_eight_vehicle_tick_cost_stays_within_budget | 76s | engine.py, vehicle.py, dynamics.py, sensor.py, controllers/pure_pursuit.py |
| test_traffic.py::test_cli_race_runs_four_controllers_headless | 63s | cli.py, engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/pure_pursuit.py |
| test_starter.py::test_starter_finishes_three_laps_clean | 57s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/starter.py |
| test_disparity_extender.py::test_disparity_extender_finishes_three_laps_clean | 54s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/disparity_extender.py |
| test_pure_pursuit.py::test_pure_pursuit_finishes_three_laps_clean | 45s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/pure_pursuit.py |
| test_engine.py::test_race_ranks_two_finishers_by_finish_time | 26s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py |
| test_web_protocol.py::test_live_tick_loop_matches_headless_run_race | 24s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py |

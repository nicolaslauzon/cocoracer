# Test map

Each test lists the components it exercises and its approximate wall-clock
cost. Agents use this to decide which tests to run for a given change.

When adding a new test, measure its timing and add it to the appropriate
section:

```bash
pytest tests/test_foo.py::test_new_thing --durations=0 -v
```

## Legend

- **Layer**: unit | integration | e2e
- **Cost**: approximate wall-clock time (regenerated from `--durations=0`)
- **Components**: source files the test validates (directly or transitively)
- **Slow**: marked `@pytest.mark.slow` — full-race E2E tests

## Summary

| Category | Tests | Total time |
|----------|-------|------------|
| Unit (< 0.1s each) | ~145 | ~2s |
| Integration (0.1-6s) | 22 | ~30s |
| E2E slow (> 6s) | 18 | ~9.5min |
| **Total** | **210** | **~10min** |

## Fastest → slowest

The tests below are sorted by wall-clock cost. The top ~167 tests finish
in under 30 seconds combined. The bottom 18 (marked **slow**) take ~9.5
minutes.

---

### test_config.py — config parsing (11 tests, <0.2s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_default_config_loads | unit | <0.01s | config.py, params/ |
| test_segment_track_has_no_centerline | unit | <0.01s | config.py |
| test_file_tracks_have_closed_centerlines | unit | <0.01s | config.py |
| test_file_reference_success | unit | <0.01s | config.py |
| test_file_reference_missing | unit | <0.01s | config.py |
| test_file_reference_invalid_json | unit | <0.01s | config.py |
| test_file_reference_non_dict | unit | <0.01s | config.py |
| test_track_without_layout | unit | <0.01s | config.py |
| test_track_with_both_layouts | unit | <0.01s | config.py |
| test_centerline_bad_point | unit | <0.01s | config.py |
| test_centerline_too_short | unit | <0.01s | config.py |

### test_controller.py — controller loading (8 tests, <0.1s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_loads_single_concrete_controller | unit | <0.01s | controller.py |
| test_missing_file_raises | unit | <0.01s | controller.py |
| test_rejects_module_without_controller | unit | <0.01s | controller.py |
| test_rejects_module_with_two_controllers | unit | <0.01s | controller.py |
| test_rejects_controller_needing_arguments | unit | <0.01s | controller.py |
| test_rejects_non_concrete_controller | unit | <0.01s | controller.py |
| test_rejects_old_signature_controller | unit | <0.01s | controller.py |
| test_rejects_module_that_fails_to_import | unit | <0.01s | controller.py |

### test_race_state.py — race state machine (6 tests, <0.1s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_crash_cycle_is_twenty_pause_then_sixty_ghost | unit | <0.01s | race_state.py |
| test_advance_is_a_noop_outside_pause_and_ghost | unit | <0.01s | race_state.py |
| test_crash_dnfs_at_crash_limit | unit | <0.01s | race_state.py |
| test_timeout_dnfs_with_timeout_reason | unit | <0.01s | race_state.py |
| test_record_lap_updates_best_and_last_and_finishes_at_target | unit | <0.01s | race_state.py |
| test_may_step_is_racing_or_ghost_and_is_racing_is_racing_only | unit | <0.01s | race_state.py |

### test_lap_tracker.py — lap counting (3 tests, <0.1s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_monotone_s_sequence_books_lap_with_lap_time | unit | <0.01s | lap_tracker.py |
| test_oscillation_across_start_line_without_checkpoint_books_no_lap | unit | <0.01s | lap_tracker.py |
| test_resync_after_crash_reset_books_no_spurious_lap | unit | <0.01s | lap_tracker.py |

### test_pgm.py — PGM image parsing (11 tests, <0.1s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_parse_p5_returns_image_at_image_dimensions | unit | <0.01s | pgm.py |
| test_parse_p5_skips_comment_lines_between_header_fields | unit | <0.01s | pgm.py |
| test_parse_rejects_non_p5_magic | unit | <0.01s | pgm.py |
| test_parse_rejects_truncated_pixel_data | unit | <0.01s | pgm.py |
| test_drivable_mask_default_threshold_splits_254_from_205 | unit | <0.01s | pgm.py |
| test_drivable_mask_threshold_override | unit | <0.01s | pgm.py |
| test_drivable_mask_is_boolean_at_image_dimensions | unit | <0.01s | pgm.py |
| test_specks_are_dropped_only_largest_component_survives | unit | <0.01s | pgm.py |
| test_largest_component_wins_over_first_component | unit | <0.01s | pgm.py |
| test_all_wall_image_gives_empty_mask | unit | <0.01s | pgm.py |
| test_shipped_maps_parse_to_single_component | unit | <0.01s | pgm.py |

### test_trackimport.py — GeoJSON track import (14 tests, <0.2s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_project_local_scales_degrees_to_meters | unit | <0.01s | trackimport.py |
| test_ring_length_closed_square | unit | <0.01s | trackimport.py |
| test_chaikin_closes_and_smooths | unit | <0.01s | trackimport.py |
| test_resample_uniform_spacing | unit | <0.01s | trackimport.py |
| test_min_corner_radius_dense_circle | unit | <0.01s | trackimport.py |
| test_min_corner_radius_sharp_corner | unit | <0.01s | trackimport.py |
| test_near_self_intersection_simple_ring | unit | <0.01s | trackimport.py |
| test_near_self_intersection_crossing_ring | unit | <0.01s | trackimport.py |
| test_rotate_start_lands_mid_longest_straight | unit | <0.01s | trackimport.py |
| test_rotate_start_requires_straight | unit | <0.01s | trackimport.py |
| test_import_track_rejects_non_linestring | unit | <0.01s | trackimport.py |
| test_import_track_rejects_open_ring | unit | <0.01s | trackimport.py |
| test_import_track_matches_committed_file | unit | 0.01s | trackimport.py |
| test_import_track_length_matches_official | unit | 0.01s | trackimport.py |

### test_track.py — track geometry (33 tests, ~10s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_stadium_closes | unit | <0.01s | track.py |
| test_stadium_centerline_uniform_spacing | unit | <0.01s | track.py |
| test_frenet_roundtrip_centerline | unit | <0.01s | track.py |
| test_frenet_roundtrip_lateral | unit | <0.01s | track.py |
| test_stadium_grid_matches_wall_band | unit | 0.17s | track.py |
| test_stadium_grid_cells_are_0_3_m | unit | <0.01s | track.py |
| test_stadium_walls_closed_and_offset_from_centerline | unit | <0.01s | track.py |
| test_stadium_reported_width_is_configured | unit | <0.01s | track.py |
| test_closure_rejects_bad_turn_sum | unit | <0.01s | track.py |
| test_closure_rejects_open_endpoint | unit | <0.01s | track.py |
| test_f1_track_closes | unit | 0.02s | track.py |
| test_f1_track_length_matches_official | unit | <0.01s | track.py |
| test_f1_track_starts_on_straight | unit | <0.01s | track.py |
| test_f1_track_frenet_roundtrip | unit | <0.01s | track.py |
| test_f1_track_frenet_roundtrip_lateral | unit | <0.01s | track.py |
| test_f1_track_grid_matches_wall_band | unit | 0.70s | track.py |
| test_f1_track_reported_width_is_configured | unit | <0.01s | track.py |
| test_beam_distances_read_known_wall | unit | <0.01s | track.py |
| test_beam_distances_first_obstacle_wins | unit | <0.01s | track.py |
| test_beam_distances_no_hit_reads_inf | unit | <0.01s | track.py |
| test_beam_distances_hit_only_the_wall_that_is_there | unit | <0.01s | track.py |
| test_beam_distances_multiple_vehicles_in_one_call | unit | <0.01s | track.py |
| test_centerline_builds_closed_ring | unit | 0.01s | track.py |
| test_centerline_track_walls_closed_and_width_configured | unit | 0.01s | track.py |
| test_explicit_walls_and_grid_pass_through | unit | <0.01s | track.py |
| test_explicit_walls_require_explicit_grid | unit | <0.01s | track.py |
| test_explicit_walls_must_close | unit | <0.01s | track.py |
| test_centerline_rejects_open_ring | unit | <0.01s | track.py |
| test_centerline_rejects_too_few_points | unit | <0.01s | track.py |
| test_build_track_without_layout | unit | <0.01s | track.py |
| test_rotate_start_lands_mid_longest_straight | unit | <0.01s | track.py |
| test_rotate_start_requires_straight | unit | <0.01s | track.py |
| test_rotate_start_threshold_is_parameterized | unit | <0.01s | track.py |

### test_web_protocol.py — web protocol serialization (8 tests, ~24s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_static_message_shape | unit | <0.01s | web/protocol.py, track.py |
| test_static_message_walls_downsampled_to_one_metre | unit | <0.01s | web/protocol.py, track.py |
| test_dynamic_message_shape | unit | <0.01s | web/protocol.py |
| test_dynamic_message_represents_all_statuses | unit | <0.01s | web/protocol.py |
| test_dynamic_message_null_for_no_hit_and_missing_scan | unit | <0.01s | web/protocol.py |
| test_dynamic_message_carries_waiting_phase | integration | <0.01s | web/protocol.py, engine.py |
| test_serializers_are_pure | unit | 0.01s | web/protocol.py |
| test_live_tick_loop_matches_headless_run_race | **slow** | 23.53s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py |

### test_vehicle.py — vehicle model (6 tests, <1s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_vehicle_defaults_to_still_at_origin | unit | <0.01s | vehicle.py |
| test_vehicle_records_fields | unit | <0.01s | vehicle.py |
| test_anchor_then_record_books_a_lap_timed_from_the_anchor | integration | <0.01s | vehicle.py, lap_tracker.py, track.py |
| test_record_does_not_feed_a_non_racing_vehicle | integration | <0.01s | vehicle.py, lap_tracker.py, track.py |
| test_crash_zeroes_motion_and_resets_to_centerline | integration | <0.01s | vehicle.py, track.py |
| test_crash_at_crash_limit_dnfs_and_skips_the_reset | integration | <0.01s | vehicle.py, track.py |

### test_collision.py — collision detection (9 tests, <0.1s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_racing_car_in_wall_is_reported | unit | <0.01s | collision.py |
| test_ghost_and_paused_in_wall_are_not_reported | unit | <0.01s | collision.py |
| test_racing_pair_below_distance_is_reported_in_fleet_order | unit | <0.01s | collision.py |
| test_racing_pair_at_or_above_distance_is_not_reported | unit | <0.01s | collision.py |
| test_overlapping_ghost_does_not_crash_the_racer | unit | <0.01s | collision.py |
| test_overlapping_paused_does_not_crash_the_racer | unit | <0.01s | collision.py |
| test_wall_hits_come_before_pair_hits | unit | <0.01s | collision.py |
| test_wall_hits_drop_out_of_the_pair_pass | unit | <0.01s | collision.py |
| test_a_vehicle_takes_at_most_one_crash_per_tick | unit | <0.01s | collision.py |

### test_sensor.py — laser scan (10 tests, <0.1s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_fleet_scan_reads_wall | unit | <0.01s | sensor.py, track.py |
| test_fleet_scan_row_per_vehicle_in_fleet_order | unit | <0.01s | sensor.py |
| test_fleet_scan_no_hit_beam_reads_inf | unit | <0.01s | sensor.py |
| test_first_hit_wins_when_vehicle_is_nearer | unit | <0.01s | sensor.py |
| test_first_hit_wins_when_wall_is_nearer | unit | <0.01s | sensor.py |
| test_scan_reads_wall_at_half_track_width | unit | 0.01s | sensor.py, track.py |
| test_racing_vehicle_appears_in_scan_at_correct_distance | unit | 0.01s | sensor.py |
| test_vehicle_never_sees_itself | unit | 0.01s | sensor.py |
| test_ghost_vehicle_is_absent_from_scan | unit | 0.01s | sensor.py |
| test_paused_vehicle_is_absent_from_scan | unit | 0.01s | sensor.py |

### test_engine.py — race engine (25 tests, ~130s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_snapshot_is_a_pure_read | unit | 0.03s | engine.py |
| test_engine_rejects_unknown_mode | unit | <0.01s | engine.py |
| test_engine_without_auto_start_is_waiting | unit | <0.01s | engine.py |
| test_auto_start_default_skips_waiting | unit | <0.01s | engine.py |
| test_race_mode_starts_on_staggered_grid | unit | <0.01s | engine.py, track.py |
| test_start_begins_countdown_in_race_mode | integration | 0.01s | engine.py |
| test_start_releases_immediately_in_time_trial | integration | 0.02s | engine.py |
| test_countdown_holds_vehicles_still_and_silent | integration | 0.02s | engine.py |
| test_ticks_while_waiting_advance_nothing | integration | <0.01s | engine.py |
| test_straight_car_stays_on_straight | integration | 1.22s | engine.py, vehicle.py, track.py |
| test_tick_cost_with_eight_vehicles_stays_under_budget | integration | 1.55s | engine.py, vehicle.py, dynamics.py, sensor.py |
| test_crash_resets_to_centerline_then_pause_and_ghost | integration | 4.34s | engine.py, vehicle.py, race_state.py, track.py |
| test_ghost_keeps_driving_during_ghost_phase | integration | 4.50s | engine.py, vehicle.py, race_state.py |
| test_ghost_passes_through_wall_without_crashing | integration | 4.14s | engine.py, vehicle.py, race_state.py, track.py |
| test_oscillation_across_start_line_books_no_lap | integration | 5.38s | engine.py, vehicle.py, lap_tracker.py, track.py |
| test_scan_arrives_every_tick_while_steppable | integration | 5.63s | engine.py, vehicle.py, sensor.py |
| test_snapshot_reports_racing_and_crashed_vehicles | integration | 4.14s | engine.py, vehicle.py, race_state.py |
| test_vehicle_collision_resets_both_to_pause_and_ghost | integration | 0.77s | engine.py, vehicle.py, race_state.py, collision.py |
| test_timeout_dnfs_inactive_car | **slow** | 0.54s | engine.py, vehicle.py, race_state.py |
| test_run_releases_a_waiting_engine | **slow** | 0.53s | engine.py, vehicle.py, race_state.py |
| test_max_crashes_dnfs | **slow** | 4.78s | engine.py, vehicle.py, race_state.py |
| test_open_loop_stub_crashes_out | **slow** | 8.30s | engine.py, vehicle.py, race_state.py, controller.py |
| test_scripted_driver_completes_a_lap | **slow** | 11.38s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py |
| test_lap_timing_starts_at_countdown_end | **slow** | 11.36s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py |
| test_race_ends_on_timeout_with_dnfs_ranked_last | **slow** | 13.45s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py |
| test_race_ranks_two_finishers_by_finish_time | **slow** | 26.31s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py |

### test_pure_pursuit.py — pure pursuit baseline (4 tests, ~45s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_track_info_carries_centerline | unit | <0.01s | controller.py, track.py |
| test_loader_injects_baselines | unit | <0.01s | controller.py, controllers/pure_pursuit.py |
| test_baselines_controller_rejects_missing_baselines | unit | <0.01s | controller.py, controllers/pure_pursuit.py |
| test_pure_pursuit_finishes_three_laps_clean | **slow** | 44.95s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/pure_pursuit.py |

### test_wall_follow.py — wall follow baseline (5 tests, ~150s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_loader_injects_baselines | unit | <0.01s | controller.py, controllers/wall_follow.py |
| test_rejects_missing_baselines | unit | <0.01s | controller.py, controllers/wall_follow.py |
| test_missing_parameter_key_is_rejected | unit | <0.01s | controller.py, controllers/wall_follow.py |
| test_steers_toward_nearest_wall | unit | <0.01s | controller.py, controllers/wall_follow.py |
| test_wall_follow_finishes_three_laps_clean | **slow** | 149.36s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/wall_follow.py |

### test_disparity_extender.py — disparity extender baseline (4 tests, ~54s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_loader_injects_baselines | unit | <0.01s | controller.py, controllers/disparity_extender.py |
| test_rejects_missing_baselines | unit | <0.01s | controller.py, controllers/disparity_extender.py |
| test_missing_parameter_key_is_rejected | unit | <0.01s | controller.py, controllers/disparity_extender.py |
| test_disparity_extender_finishes_three_laps_clean | **slow** | 53.79s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/disparity_extender.py |

### test_starter.py — starter baseline (3 tests, ~57s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_starter_loads_without_baselines | unit | <0.01s | controller.py, controllers/starter.py |
| test_starter_finishes_three_laps_clean | **slow** | 56.51s | engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/starter.py |

### test_web_frontend.py — web frontend HTML (11 tests, <0.1s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_index_html_exists | unit | <0.01s | web/index.html |
| test_index_html_is_self_contained | unit | <0.01s | web/index.html |
| test_index_html_uses_a_canvas | unit | <0.01s | web/index.html |
| test_index_html_targets_the_websocket_path | unit | <0.01s | web/index.html |
| test_index_html_covers_static_protocol_fields | unit | <0.01s | web/index.html, web/protocol.py |
| test_index_html_covers_dynamic_protocol_fields | unit | <0.01s | web/index.html, web/protocol.py |
| test_index_html_draws_car_bodies_as_rectangles | unit | <0.01s | web/index.html |
| test_index_html_has_start_button | unit | <0.01s | web/index.html |
| test_index_html_sends_the_start_message | unit | <0.01s | web/index.html |
| test_index_html_keeps_trails_client_side | unit | <0.01s | web/index.html |
| test_index_html_colors_every_vehicle_status | unit | <0.01s | web/index.html |

### test_web_server.py — web server (3 tests, ~0.5s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_start_message_enqueues_a_release | unit | <0.01s | web/server.py |
| test_non_start_and_garbage_messages_do_not_enqueue | unit | <0.01s | web/server.py |
| test_live_run_waits_for_start_message | integration | 0.51s | web/server.py, engine.py |

### test_cli.py — CLI entry point (8 tests, ~16s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_top_level_help_documents_params_and_commands | unit | <0.01s | cli.py |
| test_time_trial_help_documents_options | unit | <0.01s | cli.py |
| test_race_help_documents_options | unit | <0.01s | cli.py |
| test_drain_starts_first_wins_duplicates_ignored | unit | 0.15s | cli.py, engine.py |
| test_time_trial_rejects_two_controllers | unit | 0.14s | cli.py |
| test_time_trial_missing_controller_file | unit | 0.15s | cli.py |
| test_race_rejects_single_controller | unit | 0.19s | cli.py |
| test_race_missing_controller_file | unit | 0.16s | cli.py |
| test_time_trial_stub_dnf_headless | **slow** | 8.34s | cli.py, engine.py, vehicle.py, race_state.py, controller.py |
| test_time_trial_live_starts_web_view_and_runs | **slow** | 4.41s | cli.py, engine.py, web/server.py |
| test_race_runs_two_controllers_headless_and_prints_results | **slow** | 2.82s | cli.py, engine.py, vehicle.py, race_state.py |

### test_traffic.py — multi-vehicle scenarios (4 tests, ~64s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_collision_in_traffic_resets_to_centerline | integration | 0.02s | engine.py, vehicle.py, collision.py, track.py |
| test_ghost_cannot_be_recollided_in_traffic | integration | 0.86s | engine.py, vehicle.py, race_state.py, collision.py, track.py |
| test_racing_visible_in_scans_ghosts_absent | integration | 0.03s | engine.py, vehicle.py, sensor.py, track.py |
| test_cli_race_runs_four_controllers_headless | **slow** | 62.70s | cli.py, engine.py, vehicle.py, race_state.py, lap_tracker.py, track.py, controllers/pure_pursuit.py, controllers/open_loop.py |

### test_perf.py — performance budget (1 test, ~76s)

| Test | Layer | Cost | Components |
|------|-------|------|------------|
| test_eight_vehicle_tick_cost_stays_within_budget | **slow** | 76.47s | engine.py, vehicle.py, dynamics.py, sensor.py, race_state.py, lap_tracker.py, track.py, controllers/pure_pursuit.py |

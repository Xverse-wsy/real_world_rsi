LIBERO TCP convention corrected.
Old observation was 107 mm behind the physical gripper0_grip_site.
Controller offset now uses the MJCF hand-to-eef distance, 97 mm rather than 100 mm.
All three LIBERO control variants share the corrected offset.
API docs specify robot-base coordinates and internal finger-length compensation.
Actual MuJoCo motion tests: two vertical poses and one tilted pose with approach.
After correction: physical target errors 3.689, 2.118, 1.157 mm;
reported position equals physical grip site in all three cases.
No paid OpenAI rollout performed after this correction.
Before/after data: .setup/tcp_motion_before.json and .setup/tcp_motion_after.json.

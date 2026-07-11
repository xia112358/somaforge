# Diagnostic Contact-Aware Force Bake

This MuJoCo tool is diagnostic-only. The production pipeline is:

```text
canonical no-force spherehand motion
-> contact-aware kinematic edit
-> baseline-policy rollout in Isaac Lab 3/Newton
-> pickle-free WBT 8-part policy reference
```

Generate a diagnostic MuJoCo comparison only:

```bash
python -m motion_edit.contact_force.cli \
  --motion /path/to/canonical_motion.npz \
  --output-motion /path/to/canonical_motion.contact_force_8part.npz \
  --mujoco-model /home/xiaz/somaforge/src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.xml \
  --solve-mode forward \
  --check-policy-ref
```

The formal edited-motion entry is `motion-edit generate-ref`; it never invokes
this diagnostic bake. WBT rejects this tool's output because its provenance is
`training_eligible=false`.

Every output must contain:

```text
joint_pos, joint_vel
body_pos_w, body_quat_w, body_lin_vel_w, body_ang_vel_w
joint_names, body_names
contact_force_part_w [T, 8, 3]
contact_force_part_mask [T, 8]
contact_force_part_position_w [T, 8, 3]
contact_force_part_order = [LHEE,LTOE,RHEE,RTOE,LH,RH,LK,RK]
robot_asset_json
contact_force_provenance_json
```

`motion_edit_force_metadata` records used, unknown, and invalid sample counts.
Non-finite samples are rejected and never written into the policy reference.
Production references require `source_backend=isaaclab3_newton_mjwarp` and the
Newton solver configuration fingerprint.

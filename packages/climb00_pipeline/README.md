# Climb00 compatibility package

Implementations now live in [`generator`](../generator/README.md),
[`contact_solver`](../contact_solver/README.md), and `somaforge_core`.
Old imports and `python -m climb00_pipeline.<module>` remain supported.
New code should use the canonical packages; WBT remains in `src/holosoma`.

## Direct-infiller training baseline

The one-pass contact/avoidance experiment now uses the versioned
[direct_infiller_v1 training recipe](../../docs/climb00_direct_infiller_baseline.md)
and [configuration](../../configs/climb00/direct_infiller_v1.json).
The baseline defines training and evaluation, not a selected checkpoint.
It has no runtime post-refiner or projection. This is an experiment baseline;
it does not replace or claim implementation of the separate runtime API below.

## Package runtime contract

The following historical three-layer contract is implemented by the packages above:

1. A privileged offline generator creates full sparse-body teacher trajectories.
2. A selector predicts one complete next seven-body 63D keyframe from the realized boundary and terrain. Positions and rotation-6D values use the current torso-yaw frame.
3. An infiller connects the current and predicted keyframes. It cannot choose or alter endpoints.

The runtime API returns only the seven-body keypoint trajectory. This does not
permit sparse collision proxies: an infiller backend must first produce a private
canonical G1 floating-root + 29-DOF trajectory. `G1MechanicalProjector` runs
Newton FK and collision queries on the authoritative sphere-hand URDF, checks
joint limits, audits self/environment collisions at frames and swept subframes,
and only then exposes the projected keypoints.

`TeacherDataset` reads the generated `teacher_*.npz` trajectories and their aligned
`teacher_events.npz`. The legacy 207 edited motions are provenance for teacher generation;
they are not the runtime selector/infiller training corpus.

`TeacherDataset.full_body_segment()` deliberately rejects the current sparse-only
1024-teacher cache. A teacher used for mechanical infiller training must additionally
contain canonical `joint_pos[T,36]` and `joint_names[29]`; sparse keypoints cannot be
silently treated as full-body supervision.

Runtime outputs and experiment artifacts remain under the repository `tmp/` directory.

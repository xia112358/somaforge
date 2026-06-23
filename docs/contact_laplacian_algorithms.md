# Contact Laplacian Editing Algorithms

This document describes the two Laplacian-style algorithms that should coexist
in `motion_edit` contact-anchor augmentation:

1. task-space contact-handle LTE over semantic keypoints;
2. fullbody interaction-mesh / q-space Laplacian refinement.

The goal is not to choose one algorithm and delete the other. The intended
direction is to let both affect the edit solution at different levels of the
same contact-edit pipeline.

## Problem

Contact-anchor editing starts from a simple user operation:

```text
move this bound contact anchor 10 cm along its original surface
```

The edit is stored as a `ContactAnchorEditRecord` inside a
`ContactEditPlan`. That record is only an intent:

- anchor id;
- body;
- old and new contact position;
- tangent delta on the same surface;
- affected frames;
- surface id/object id;
- clamp/reject provenance.

It should not directly mutate the source motion. Generation is a separate
step.

The current failure mode is caused by under-constrained generation. If the user
moves one foot anchor, task-space LTE can propagate that displacement through
the semantic body graph into torso and hands. If a hand is also in contact but
is not explicitly constrained, it can bend or drift even though the user did not
edit that contact.

The correct principle is:

```text
edited contact anchors move to their targets;
unedited contact anchors stay fixed unless explicitly edited.
```

## Algorithm A: Task-Space Contact Handle LTE

### Role

Task-space LTE is the fast first-stage trajectory editor. It operates on a
small semantic keypoint set, not directly on robot joint angles.

Current implementation source:

```text
/home/xiaz/lte/contact_handle_lte.py
```

Current semantic keypoints:

```text
root
torso
left_hand
right_hand
left_foot
right_foot
```

In `motion_edit`, these semantic keypoints are derived from `body_pos_w` using
known body-name aliases such as wrist links and ankle/contact links.

### Inputs

- source motion npz;
- `ContactGraph`;
- `ContactEditPlan`;
- semantic keypoint trajectories `X_demo[name][frame, xyz]`;
- edited contact anchor handles;
- fixed contact anchor handles for unedited contacts.

### Variables

The optimization solves for edited semantic keypoint trajectories:

```text
X_edit[t, keypoint, xyz]
```

The existing solver uses an offset form:

```text
X_edit = X_demo + offset
```

### Objective Terms

#### Temporal Smooth Offset

Preserve smooth temporal motion by penalizing the Laplacian of offsets:

```text
|| L_time offset ||^2
```

This prevents a contact edit from creating abrupt frame-to-frame jumps.

#### Body-Relative Edges

Preserve semantic body structure using edges such as:

```text
root -> torso
torso -> left_hand
torso -> right_hand
root -> left_foot
root -> right_foot
```

In offset form this means nearby semantic body parts prefer similar offsets:

```text
offset[parent] - offset[child] ~= 0
```

This is useful for whole-body coherence, but it is also why a foot edit can
pull hands if hand contacts are not pinned.

#### Edited Contact Handles

For every nonzero `ContactAnchorEditRecord`, add a high-weight handle:

```text
X_edit[body, affected_frames] ~= X_demo[body, affected_frames] + delta_world
```

The body must be one of:

```text
left_hand
right_hand
left_foot
right_foot
```

or a resolvable semantic alias.

#### Fixed Contact Handles

For every unedited contact anchor, add a high-weight fixed handle:

```text
X_edit[body, contact_frames] ~= X_demo[body, contact_frames]
```

This is the missing constraint that prevents unedited hand/foot contacts from
being dragged by another edit.

Important detail: fixed handles should generally target the original semantic
keypoint trajectory, not the anchor representative point. The anchor
`world_position` may be a representative contact point on the surface, while the
semantic keypoint may be wrist/ankle/contact-link position. Pinning to the
original keypoint trajectory avoids creating an artificial snap.

### Output

Task-space LTE returns edited semantic keypoints. `motion_edit` then maps their
offsets back to dense `body_pos_w` and optionally invokes a fullbody IK/backend
to produce a generated motion npz.

### Strengths

- fast;
- deterministic;
- independent of MuJoCo/CVX setup;
- good for interactive preview and batch generation;
- directly compatible with `ContactEditPlan`.

### Weaknesses

- not a physics solver;
- no joint limits by itself;
- no non-penetration by itself;
- only sees a small semantic skeleton;
- can produce artifacts if contact pins are incomplete.

### Immediate Fix Needed

Add fixed contact handles for all unedited contact anchors. The generation
metadata should record:

- number of moving contact handles;
- number of fixed contact handles;
- bodies and frame intervals pinned;
- zero-delta edits ignored or treated as fixed contacts.

This should be the next short-term stability fix.

## Algorithm B: Fullbody Interaction Mesh / q-Space Laplacian

### Role

The fullbody interaction-mesh method refines a robot motion in joint space. It
is closer to OmniRetarget/Holosoma retargeting than the task-space LTE layer.

Relevant implementation source:

```text
/home/xiaz/holosoma_isaaclab3_newton/src/holosoma_retargeting/holosoma_retargeting/src/interaction_mesh_retargeter.py
```

That code is not a direct drop-in replacement for `motion_edit` generation. It
depends on robot models, MuJoCo Jacobians, CVXPY, object geometry, and per-frame
QP solves. But it contains the right fullbody constraints.

### Inputs

- robot q trajectory or nominal q;
- source/demo body or human keypoints;
- object/terrain points;
- edited task-space keypoints or contact targets;
- contact anchors and contact states;
- surface bindings;
- robot/object geometry.

### Variables

The solver optimizes robot configuration increments:

```text
dq
```

and auxiliary Laplacian variables:

```text
lap_var
```

per frame.

### Interaction Mesh Laplacian

Holosoma builds an interaction mesh from robot/human match points and object
points:

```text
vertices = [robot_or_human_points, object_points]
```

It computes adjacency/tetrahedra and target Laplacian coordinates:

```text
target_lap = L_source vertices_source
```

At solve time, it linearizes robot point motion through Jacobians and penalizes:

```text
|| lap_var - target_lap ||^2
```

with the relationship:

```text
J_L dq - lap_var = -lap0
```

This preserves spatial relationships between robot links and terrain/object
points while allowing the robot configuration to change.

### Contact / Sticking Constraints

The Holosoma solver also supports hard or near-hard constraints:

- foot sticking XY constraints against previous frame;
- foot lock Z constraints over configured windows;
- non-penetration constraints;
- self-collision constraints;
- joint limits;
- trust-region constraints;
- q smoothness and nominal tracking.

For contact-anchor editing, the analogous constraints should be:

```text
edited anchor body reaches edited target on same surface
unedited contact bodies stay fixed on their contact surfaces
normal displacement is not allowed
surface_id/object_id is preserved
joint limits are respected
penetration is avoided when geometry is available
```

### Output

The output is a full robot motion, usually q or qpos. In `motion_edit`, that
would eventually become a generated `MotionVersion` with:

- generated motion npz;
- edited ContactGraph;
- canonical segmentation;
- token catalog built from canonical segments.

### Strengths

- fullbody consistency;
- joint-limit aware;
- contact/sticking constraints can be hard constraints;
- can use terrain/object geometry;
- reduces artifacts after task-space editing.

### Weaknesses

- heavier dependencies;
- slower;
- needs robot model and geometry;
- harder to unit test;
- not ideal as the first interactive preview path.

## How The Two Algorithms Should Coexist

The two algorithms operate at different abstraction levels:

```text
ContactEditPlan
  -> task-space contact-handle LTE
  -> fullbody interaction-mesh / q-space Laplacian refinement
  -> generated MotionVersion
```

They can also be viewed as one combined objective:

```text
min
  w_move_contact   * edited contact anchor target error
+ w_fixed_contact  * unedited contact anchor drift
+ w_temporal       * temporal Laplacian smoothness
+ w_body_rel       * semantic body-relative Laplacian
+ w_mesh_lap       * interaction mesh Laplacian error
+ w_q_prior        * q / pose prior
+ w_q_smooth       * q smoothness

subject to
  same-surface contact constraints
  no normal-direction contact displacement
  preserved surface_id/object_id
  contact sticking for pinned contacts
  joint limits
  optional non-penetration
```

In practice, implement this progressively.

## Recommended motion_edit Roadmap

### Stage 1: Stabilize Existing Task-Space LTE

Add fixed handles for unedited contacts.

This directly addresses the current artifact where a hand contact bends after
only a foot anchor was edited.

Expected behavior:

- moving `left_foot` should not move `left_hand` during left-hand contact
  windows unless the left-hand anchor is also edited;
- moving one anchor creates exactly one moving handle plus many fixed contact
  handles;
- body-relative Laplacian still contributes, but cannot overpower fixed
  contact pins.

### Stage 2: Add Fullbody Contact-Laplacian Backend

Add a backend mode such as:

```text
--mode fullbody_contact_laplacian
```

or:

```text
--refine-backend interaction_mesh_qp
```

This backend should use the task-space LTE output as a reference and refine it
with q-space/contact constraints.

### Stage 3: Unify Solver Interface

Create a backend-neutral interface:

```text
ContactEditPlan
ContactGraph
source MotionVersion
solver config
  -> generated motion npz
  -> generated ContactGraph
  -> generation report
```

Backends can include:

- `taskspace_lte`;
- `taskspace_lte_with_fixed_contacts`;
- `fullbody_contact_laplacian`;
- future physics/IK refiners.

## Key Invariant

Contact anchor dragging remains a planning operation. It creates or updates a
`ContactEditPlan`; it does not generate motion automatically.

Motion generation remains explicit:

```text
motion-edit generate-lte-augmentation --plan ...
```

The generated motion must be a new motion version. The source motion, source
contact layer, and canonical segmentation must not be mutated by default.


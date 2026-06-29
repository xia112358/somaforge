"""Configuration types for viser visualization."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ViserConfig:
    """Configuration for viser player visualization.

    This follows the pattern from holosoma's config_types.
    Uses a flat structure with default values.
    """

    qpos_npz: str = "OmniRetarget_Dataset/data/holosoma_motions_50hz/climb_00_z_scale_1.0.npz"
    """Path to .npz file with qpos data."""

    robot_urdf: str = "OmniRetarget_Dataset/models/g1/g1_29dof.urdf"
    """Path to robot URDF file."""

    object_urdf: str | None = None
    """Path to object URDF file (optional)."""

    contact_force_npz: str | None = None
    """Optional override for contact-force .npz; defaults to auto-matching by motion name."""

    contact_force_scale: float = 0.003
    """Scale factor from Newtons to displayed contact-force vector length."""

    fps: int = 30
    """Frames per second for playback."""

    assume_object_in_qpos: bool = False
    """Whether object pose is included in qpos array."""

    loop: bool = False
    """Whether to loop playback."""

    show_meshes: bool = True
    """Whether to show mesh visualizations."""

    grid_width: float = 8.0
    """Grid width for visualization."""

    grid_height: float = 8.0
    """Grid height for visualization."""

    visual_fps_multiplier: int = 2
    """Visual FPS multiplier for interpolation."""

    segment_export_path: str | None = None
    """Path written by the segment exporter; defaults to data/motion_viewer/segments/{motion}.segments.jsonl."""

    clip_output_dir: str | None = None
    """Directory for saved clip .npz files; defaults to data/motion_viewer/clips/{motion}."""

    timeline_wrapper: bool = True
    """Use the local wrapper page with a full-width bottom cutter timeline."""

    timeline_port: int = 8090
    """Port for the local timeline wrapper page."""

    open_browser: bool = False
    """Open the timeline wrapper URL in a browser after startup."""

    min_fps: int = 1
    """Minimum FPS setting."""

    max_fps: int = 240
    """Maximum FPS setting."""

    min_interp_mult: int = 1
    """Minimum interpolation multiplier."""

    max_interp_mult: int = 8
    """Maximum interpolation multiplier."""

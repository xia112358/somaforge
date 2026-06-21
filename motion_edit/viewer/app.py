from __future__ import annotations

import os
import subprocess
from pathlib import Path

from motion_edit.adapters.omniretarget import detect_omniretarget_paths
from motion_edit.export import export_cutter_segments
from motion_edit.layers import read_layer
from motion_edit.paths import EXPORTS_ROOT, LAYERS_ROOT


def _default_repo_root() -> Path | None:
    candidates = [Path.cwd(), Path("/home/xiaz/holosoma_isaaclab3_newton")]
    for path in candidates:
        if (path / "src/holosoma_retargeting/holosoma_retargeting/viser_player.py").exists():
            return path
    return None


def _resolve_layer(layer: str | None) -> Path | None:
    if not layer:
        return None
    path = Path(layer).expanduser()
    if path.exists():
        return path.resolve()
    return (LAYERS_ROOT / layer).resolve()


def _export_layer_for_motion(layer_root: Path, motion_id: str) -> Path:
    if layer_root.is_file():
        return layer_root
    layer_file = layer_root / f"{motion_id}.jsonl"
    if not layer_file.exists():
        raise FileNotFoundError(f"layer file not found for {motion_id}: {layer_file}")
    segments = read_layer(layer_file, default_source=layer_root.name, default_status="candidate")
    out_dir = EXPORTS_ROOT / "cutter_segments" / "view"
    written = export_cutter_segments(out_dir, segments)
    return written[0]


def launch_viewer(
    motion: str | Path,
    *,
    repo_root: str | Path | None = None,
    layer: str | None = None,
    conda_env: str = "hsretargeting",
    timeline_port: int = 8094,
    fps: int = 50,
    with_terrain: bool = False,
) -> subprocess.Popen:
    repo = Path(repo_root).expanduser().resolve() if repo_root else _default_repo_root()
    if repo is None:
        raise FileNotFoundError("could not find holosoma repo with viser_player.py; pass --repo-root")
    paths = detect_omniretarget_paths(motion, repo_root=repo)
    viewer = repo / "src/holosoma_retargeting/holosoma_retargeting/viser_player.py"
    robot_urdf = repo / "OmniRetarget_Dataset/models/g1/g1_29dof_spherehand.urdf"
    segment_path = None
    layer_root = _resolve_layer(layer)
    if layer_root is not None:
        segment_path = _export_layer_for_motion(layer_root, paths.motion_path.stem)

    cmd = [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        conda_env,
        "env",
        f"PYTHONPATH={repo / 'src/holosoma_retargeting'}",
        "python",
        str(viewer),
        "--qpos-npz",
        str(paths.motion_path),
        "--robot-urdf",
        str(robot_urdf),
        "--timeline-port",
        str(timeline_port),
        "--fps",
        str(fps),
        "--loop",
        "--no-open-browser",
    ]
    if segment_path is not None:
        cmd.extend(["--segment-export-path", str(segment_path)])
    if paths.contact_force_npz is not None:
        cmd.extend(["--contact-force-npz", str(paths.contact_force_npz)])
    if with_terrain and paths.terrain_urdf is not None:
        cmd.extend(["--object-urdf", str(paths.terrain_urdf)])
    env = os.environ.copy()
    return subprocess.Popen(cmd, cwd=str(repo), env=env)

"""Kinematic MuJoCo models derived from the authoritative robot URDF.

This adapter is for retargeting optimization and FK, not Newton contact truth.
"""
from pathlib import Path

from somaforge_core.robot_assets import canonical_g1_urdf_path, canonical_g1_source_metadata


def _urdf_spec(path):
    import mujoco
    path = Path(path).resolve()
    spec = mujoco.MjSpec.from_file(str(path))
    spec.compiler.fusestatic = False  # Keep fixed collision/body landmarks for FK.
    spec.compiler.meshdir = str(path.parent)
    for mesh in spec.meshes:
        mesh.file = str(path.parent / mesh.file)
    return spec


def load_retarget_model(robot_path, object_path=None, *, object_name="ground", robot_type="g1"):
    import mujoco
    from somaforge_core.motion_schema import G1_29DOF_JOINT_ORDER
    robot_path = Path(robot_path).resolve()
    if robot_type == "g1":
        if robot_path != canonical_g1_urdf_path().resolve():
            raise ValueError("Retargeting requires the canonical G1 URDF from robot_assets")
        canonical_g1_source_metadata()
    elif robot_type != "t1":
        raise ValueError(f"Unsupported retarget robot: {robot_type}")
    spec = _urdf_spec(robot_path)
    roots = list(spec.worldbody.bodies)
    if len(roots) != 1:
        raise ValueError("Expected one canonical robot root")
    roots[0].add_freejoint(name="floating_base")
    spec.worldbody.add_geom(name="ground", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, .1])
    if object_name != "ground":
        if object_path is None:
            raise ValueError("Retargeting scene requires its object URDF")
        child = _urdf_spec(object_path)
        for index, geom in enumerate(child.geoms):
            geom.name = f"{object_name}_{index}"
        if object_name != "multi_boxes":
            roots = list(child.worldbody.bodies)
            if len(roots) != 1:
                raise ValueError("Dynamic object must have one root")
            roots[0].add_freejoint(name="object_freejoint")
        spec.attach(child, frame=spec.worldbody.add_frame())
    model = spec.compile()
    names = tuple(model.joint(i).name for i in range(model.njnt)
                  if model.jnt_type[i] == mujoco.mjtJoint.mjJNT_HINGE)
    if robot_type == "g1" and names != G1_29DOF_JOINT_ORDER:
        raise ValueError("Retarget model changed the canonical joint order")
    return model

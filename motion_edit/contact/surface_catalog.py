from __future__ import annotations

from motion_edit.contact.schema import ContactSurfaceRecord


def parse_box_descriptor(descriptor: str) -> tuple[str, list[float], list[float]]:
    try:
        object_id, center_text, size_text = descriptor.split(":")
    except ValueError as exc:
        raise ValueError("box descriptor must be object_id:cx,cy,cz:sx,sy,sz") from exc
    center = [float(item) for item in center_text.split(",")]
    size = [float(item) for item in size_text.split(",")]
    if len(center) != 3 or len(size) != 3:
        raise ValueError("box descriptor center and size must have three components")
    if any(item <= 0.0 for item in size):
        raise ValueError("box size components must be positive")
    return object_id, center, size


def box_surfaces(
    *,
    motion_id: str,
    object_id: str,
    center: list[float],
    size: list[float],
    include_sides: bool = True,
    source: str = "box_surface_catalog",
) -> list[ContactSurfaceRecord]:
    cx, cy, cz = center
    sx, sy, sz = size
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    surfaces = [
        ContactSurfaceRecord(
            motion_id=motion_id,
            surface_id=f"{object_id}_top",
            object_id=object_id,
            surface_type="box_face",
            origin=[cx, cy, cz + hz],
            normal=[0.0, 0.0, 1.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
            bounds={"u": [-hx, hx], "v": [-hy, hy]},
            source=source,
        )
    ]
    if include_sides:
        surfaces.extend(
            [
                ContactSurfaceRecord(
                    motion_id=motion_id,
                    surface_id=f"{object_id}_pos_x",
                    object_id=object_id,
                    surface_type="box_face",
                    origin=[cx + hx, cy, cz],
                    normal=[1.0, 0.0, 0.0],
                    tangent_u=[0.0, 1.0, 0.0],
                    tangent_v=[0.0, 0.0, 1.0],
                    bounds={"u": [-hy, hy], "v": [-hz, hz]},
                    source=source,
                ),
                ContactSurfaceRecord(
                    motion_id=motion_id,
                    surface_id=f"{object_id}_neg_x",
                    object_id=object_id,
                    surface_type="box_face",
                    origin=[cx - hx, cy, cz],
                    normal=[-1.0, 0.0, 0.0],
                    tangent_u=[0.0, 1.0, 0.0],
                    tangent_v=[0.0, 0.0, 1.0],
                    bounds={"u": [-hy, hy], "v": [-hz, hz]},
                    source=source,
                ),
                ContactSurfaceRecord(
                    motion_id=motion_id,
                    surface_id=f"{object_id}_pos_y",
                    object_id=object_id,
                    surface_type="box_face",
                    origin=[cx, cy + hy, cz],
                    normal=[0.0, 1.0, 0.0],
                    tangent_u=[1.0, 0.0, 0.0],
                    tangent_v=[0.0, 0.0, 1.0],
                    bounds={"u": [-hx, hx], "v": [-hz, hz]},
                    source=source,
                ),
                ContactSurfaceRecord(
                    motion_id=motion_id,
                    surface_id=f"{object_id}_neg_y",
                    object_id=object_id,
                    surface_type="box_face",
                    origin=[cx, cy - hy, cz],
                    normal=[0.0, -1.0, 0.0],
                    tangent_u=[1.0, 0.0, 0.0],
                    tangent_v=[0.0, 0.0, 1.0],
                    bounds={"u": [-hx, hx], "v": [-hz, hz]},
                    source=source,
                ),
            ]
        )
    return surfaces


def surfaces_from_terrain_metadata(*_args, **_kwargs) -> list[ContactSurfaceRecord]:
    raise NotImplementedError("terrain metadata surface loading is not implemented yet")


def surfaces_from_urdf_collision_boxes(*_args, **_kwargs) -> list[ContactSurfaceRecord]:
    raise NotImplementedError("URDF collision box surface loading is not implemented yet")


def surfaces_from_obj_mesh_faces(*_args, **_kwargs) -> list[ContactSurfaceRecord]:
    raise NotImplementedError("OBJ mesh face surface loading is not implemented yet")


def surfaces_from_heightfield_patches(*_args, **_kwargs) -> list[ContactSurfaceRecord]:
    raise NotImplementedError("heightfield surface patch loading is not implemented yet")

from __future__ import annotations

import hashlib
import json
import os
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path
from typing import Any

G1_SPHEREHAND_ASSET_ID = "g1_29dof_spherehand_v1"
G1_SPHEREHAND_SHA256 = "6d79140d335157ad026d24b79be6fbb161c997c01c3ffc37bcca282dc2240696"
G1_SPHEREHAND_XML_SHA256 = "17549f99cc230aa8e8d29a5bcc30cc3075ad34cbc1f9860dacbbe840ac092313"
G1_SPHEREHAND_BUNDLE_SHA256 = "d798925cd916e994a47c70ee30ea5f537f000a825c1c66aa914bbe434f60c199"
G1_SPHEREHAND_URDF_RELATIVE = Path(
    "src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.urdf"
)
G1_SPHEREHAND_XML_RELATIVE = Path(
    "src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.xml"
)


def somaforge_root() -> Path:
    configured = os.environ.get("SOMAFORGE_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
        if not _is_somaforge_root(root):
            raise FileNotFoundError(f"SOMAFORGE_ROOT is not a SomaForge checkout: {root}")
        return root

    for parent in Path(__file__).resolve().parents:
        if _is_somaforge_root(parent):
            return parent
    raise FileNotFoundError("could not locate the SomaForge checkout; set SOMAFORGE_ROOT")


def canonical_g1_urdf_path() -> Path:
    return somaforge_root() / G1_SPHEREHAND_URDF_RELATIVE


def canonical_g1_xml_path() -> Path:
    return somaforge_root() / G1_SPHEREHAND_XML_RELATIVE


def canonical_g1_asset_metadata() -> dict[str, str]:
    urdf = canonical_g1_urdf_path()
    xml = canonical_g1_xml_path()
    if not urdf.is_file():
        raise FileNotFoundError(f"canonical G1 sphere-hand URDF is missing: {urdf}")
    if not xml.is_file():
        raise FileNotFoundError(f"canonical G1 sphere-hand XML is missing: {xml}")
    actual_sha256 = _sha256(urdf)
    if actual_sha256 != G1_SPHEREHAND_SHA256:
        raise ValueError(
            "canonical G1 sphere-hand URDF fingerprint mismatch: "
            f"expected {G1_SPHEREHAND_SHA256}, got {actual_sha256} at {urdf}"
        )
    actual_xml_sha256 = _sha256(xml)
    if actual_xml_sha256 != G1_SPHEREHAND_XML_SHA256:
        raise ValueError(
            "canonical G1 sphere-hand XML fingerprint mismatch: "
            f"expected {G1_SPHEREHAND_XML_SHA256}, got {actual_xml_sha256} at {xml}"
        )
    actual_bundle_sha256 = _urdf_bundle_sha256(urdf)
    if G1_SPHEREHAND_BUNDLE_SHA256 and actual_bundle_sha256 != G1_SPHEREHAND_BUNDLE_SHA256:
        raise ValueError(
            "canonical G1 sphere-hand asset bundle fingerprint mismatch: "
            f"expected {G1_SPHEREHAND_BUNDLE_SHA256}, got {actual_bundle_sha256}"
        )
    return {
        "asset_id": G1_SPHEREHAND_ASSET_ID,
        "urdf_path": str(urdf),
        "urdf_sha256": actual_sha256,
        "xml_path": str(xml),
        "xml_sha256": actual_xml_sha256,
        "asset_bundle_sha256": actual_bundle_sha256,
    }


def validate_g1_asset_metadata(metadata: Mapping[str, Any] | None, *, context: str) -> None:
    expected = canonical_g1_asset_metadata()
    if metadata is None:
        raise ValueError(
            f"{context} has no robot asset fingerprint and is treated as legacy wrong-URDF data; regenerate it"
        )
    actual_id = str(metadata.get("asset_id") or "")
    actual_sha256 = str(metadata.get("urdf_sha256") or "")
    actual_xml_sha256 = str(metadata.get("xml_sha256") or "")
    actual_bundle_sha256 = str(metadata.get("asset_bundle_sha256") or "")
    if (
        actual_id != expected["asset_id"]
        or actual_sha256 != expected["urdf_sha256"]
        or actual_xml_sha256 != expected["xml_sha256"]
        or actual_bundle_sha256 != expected["asset_bundle_sha256"]
    ):
        raise ValueError(
            f"{context} uses an incompatible robot asset "
            f"(asset_id={actual_id!r}, urdf_sha256={actual_sha256!r}, "
            f"xml_sha256={actual_xml_sha256!r}); expected {expected['asset_id']} / "
            f"{expected['urdf_sha256']} / {expected['xml_sha256']} / "
            f"{expected['asset_bundle_sha256']}"
        )


def encode_robot_asset_json(metadata: Mapping[str, Any] | None = None) -> str:
    return json.dumps(dict(metadata or canonical_g1_asset_metadata()), sort_keys=True)


def decode_robot_asset_json(value: Any, *, context: str) -> dict[str, Any]:
    if value is None:
        validate_g1_asset_metadata(None, context=context)
    raw = value.item() if hasattr(value, "item") else value
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        metadata = json.loads(str(raw))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} has invalid robot_asset_json") from exc
    if not isinstance(metadata, dict):
        raise ValueError(f"{context} robot_asset_json must decode to an object")
    validate_g1_asset_metadata(metadata, context=context)
    return metadata


def validate_canonical_g1_xml(path: str | Path) -> dict[str, str]:
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"MuJoCo model is missing: {candidate}")
    actual = _sha256(candidate)
    if actual != G1_SPHEREHAND_XML_SHA256:
        raise ValueError(
            "MuJoCo model uses the wrong G1 asset: expected XML SHA256 "
            f"{G1_SPHEREHAND_XML_SHA256}, got {actual} at {candidate}"
        )
    return canonical_g1_asset_metadata()


def validate_canonical_g1_urdf(path: str | Path) -> dict[str, str]:
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"G1 URDF is missing: {candidate}")
    actual = _sha256(candidate)
    if actual != G1_SPHEREHAND_SHA256:
        raise ValueError(
            f"G1 tool uses the wrong URDF: expected SHA256 {G1_SPHEREHAND_SHA256}, "
            f"got {actual} at {candidate}"
        )
    bundle = _urdf_bundle_sha256(candidate)
    if bundle != G1_SPHEREHAND_BUNDLE_SHA256:
        raise ValueError(
            f"G1 tool uses an incompatible mesh bundle: expected {G1_SPHEREHAND_BUNDLE_SHA256}, "
            f"got {bundle} at {candidate.parent}"
        )
    return canonical_g1_asset_metadata()


def validate_g1_robot_config(robot_config: Any) -> dict[str, str] | None:
    asset = robot_config.asset
    robot_type = str(asset.robot_type)
    urdf_file = str(asset.urdf_file)
    if not (robot_type.startswith("g1_") or urdf_file.startswith("g1/")):
        return None
    expected_urdf = "g1/g1_29dof_spherehand.urdf"
    expected_xml = "g1/g1_29dof_spherehand.xml"
    if urdf_file != expected_urdf or str(asset.xml_file) != expected_xml:
        raise ValueError(
            "G1 runs must use the canonical sphere-hand asset pair; "
            f"got urdf={urdf_file!r}, xml={asset.xml_file!r}"
        )
    return canonical_g1_asset_metadata()


def _is_somaforge_root(path: Path) -> bool:
    return (
        (path / "src/holosoma/holosoma").is_dir()
        and (path / "packages/motion_edit").is_dir()
        and (path / "packages/gmvq").is_dir()
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _urdf_bundle_sha256(urdf: Path) -> str:
    asset_root = urdf.parent.resolve()
    mesh_paths: set[Path] = set()
    for mesh in ET.parse(urdf).getroot().iter("mesh"):
        filename = mesh.get("filename")
        if not filename:
            continue
        resolved = (asset_root / filename).resolve()
        if not resolved.is_relative_to(asset_root):
            raise ValueError(f"URDF mesh escapes the canonical asset root: {filename}")
        if not resolved.is_file():
            raise FileNotFoundError(f"URDF mesh is missing: {resolved}")
        mesh_paths.add(resolved)

    digest = hashlib.sha256()
    for path in [urdf.resolve(), *sorted(mesh_paths)]:
        relative = path.relative_to(asset_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()

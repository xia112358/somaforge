#!/usr/bin/env python3
"""Prepare clean policy-ref sources for motion_edit contact augmentation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gmvq_ref.canonicalize_policy_ref import canonicalize  # noqa: E402
from scripts.gmvq_ref.filter_policy_ref_body_template import filter_ref  # noqa: E402


def _read_json(path: Path) -> Any:
    return json.loads(path.expanduser().read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_manifest_path(manifest_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (manifest_path.parent / path).resolve()


def _motion_id_from_path(path: Path) -> str:
    return path.stem


def build_clean_sources(
    *,
    motion_manifest: Path,
    body_template: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    manifest = _read_json(motion_manifest)
    motion_files = manifest.get("motion_files")
    if not isinstance(motion_files, list):
        raise ValueError(f"motion manifest must contain motion_files list: {motion_manifest}")

    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for item in motion_files:
        if not isinstance(item, dict) or "motion_file" not in item:
            raise ValueError(f"invalid motion_files entry: {item!r}")
        source = _resolve_manifest_path(motion_manifest, str(item["motion_file"]))
        motion_id = _motion_id_from_path(source)
        tmp_ref = output_dir / f"{motion_id}.policy_ref_v1.tmp_fullbody.npz"
        clean_ref = output_dir / f"{motion_id}.clean32.policy_ref_v1.npz"

        canonicalize(source, tmp_ref)
        filter_ref(argparse.Namespace(input=tmp_ref, template=body_template, output=clean_ref))
        tmp_ref.unlink(missing_ok=True)

        records.append(
            {
                "motion_id": motion_id,
                "source_motion_path": str(source),
                "clean_source_path": str(clean_ref),
                "terrain_id": item.get("terrain_id"),
                "weight": item.get("weight", 1.0),
            }
        )
        print(f"clean source {len(records)}/{len(motion_files)}: {clean_ref}", flush=True)
    return records


def rebase_cut_summary(*, cut_summary: Path, records: list[dict[str, Any]], output_path: Path) -> list[dict[str, Any]]:
    items = _read_json(cut_summary)
    if not isinstance(items, list):
        raise ValueError(f"cut summary must be a list: {cut_summary}")
    by_motion_id = {str(record["motion_id"]): record for record in records}

    output: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"invalid cut summary item: {item!r}")
        motion_id = str(item.get("motion_id", ""))
        record = by_motion_id.get(motion_id)
        if record is None:
            raise KeyError(f"cut summary motion_id not found in clean sources: {motion_id}")
        updated = dict(item)
        updated["original_motion_path_before_clean_source_rebase"] = updated.get("motion_path")
        updated["motion_path"] = record["clean_source_path"]
        output.append(updated)

    _write_json(output_path, output)
    return output


def parse_args() -> argparse.Namespace:
    base = Path("/home/xiaz/holosoma_isaaclab3_newton")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--motion-manifest",
        type=Path,
        default=base / "configs/motion_matched/climb29_z1_unmasked_manifest.json",
    )
    parser.add_argument(
        "--cut-summary",
        type=Path,
        default=Path("/home/xiaz/motion_edit/data/workbench/raw_contact_29_cut_summary.json"),
    )
    parser.add_argument(
        "--body-template",
        type=Path,
        default=base / "tmp/gmvq_play/clean_policy_ref_v1/climb_00_z_scale_1.0.clean32.policy_ref_v1.npz",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=base / "tmp/gmvq_play/clean_source_aug_full/clean32_sources",
    )
    parser.add_argument(
        "--output-cut-summary",
        type=Path,
        default=base / "tmp/gmvq_play/clean_source_aug_full/raw_contact_29_cut_summary_clean32_source.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = build_clean_sources(
        motion_manifest=args.motion_manifest.expanduser(),
        body_template=args.body_template.expanduser(),
        output_dir=args.output_dir.expanduser(),
    )
    source_manifest = {
        "schema": "clean_policy_ref_aug_source_manifest_v1",
        "motion_manifest": str(args.motion_manifest.expanduser()),
        "body_template": str(args.body_template.expanduser()),
        "clean_source_count": len(records),
        "records": records,
    }
    _write_json(args.output_dir.expanduser() / "manifest.json", source_manifest)
    rebased = rebase_cut_summary(
        cut_summary=args.cut_summary.expanduser(),
        records=records,
        output_path=args.output_cut_summary.expanduser(),
    )
    print(
        json.dumps(
            {
                "clean_source_count": len(records),
                "rebased_cut_summary_count": len(rebased),
                "clean_source_manifest": str(args.output_dir.expanduser() / "manifest.json"),
                "rebased_cut_summary": str(args.output_cut_summary.expanduser()),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

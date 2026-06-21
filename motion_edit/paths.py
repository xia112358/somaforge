from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PACKAGE_ROOT / "data"
LAYERS_ROOT = DATA_ROOT / "layers"
EXPORTS_ROOT = DATA_ROOT / "exports"
CATALOGS_ROOT = DATA_ROOT / "catalogs"
BACKUPS_ROOT = DATA_ROOT / "backups"
WORKBENCH_ROOT = DATA_ROOT / "workbench"


def ensure_data_dirs() -> None:
    for path in [
        CATALOGS_ROOT,
        LAYERS_ROOT / "manual",
        LAYERS_ROOT / "candidates",
        LAYERS_ROOT / "accepted",
        LAYERS_ROOT / "rejected",
        LAYERS_ROOT / "contact",
        EXPORTS_ROOT / "cutter_segments",
        EXPORTS_ROOT / "manifests",
        WORKBENCH_ROOT / "sessions",
        BACKUPS_ROOT,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def layer_dir(status: str, name: str | None = None) -> Path:
    if status == "candidate":
        base = LAYERS_ROOT / "candidates"
    else:
        base = LAYERS_ROOT / status
    return base / name if name else base

#!/usr/bin/env python3
from __future__ import annotations

import json

from somaforge_core import AssetManifest
from somaforge_core.robot_assets import canonical_g1_asset_metadata


def main() -> None:
    print(json.dumps(canonical_g1_asset_metadata(), indent=2, sort_keys=True))
    manifest = AssetManifest.load()
    errors = manifest.validate(require_exists=True)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"asset manifest: {len(manifest.ids())} entries validated")


if __name__ == "__main__":
    main()

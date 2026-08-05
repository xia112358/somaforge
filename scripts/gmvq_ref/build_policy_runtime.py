#!/usr/bin/env python3
"""Package the accepted GMVQ reference models for direct policy execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gmvq.policy_reference import build_policy_reference_bundle, save_policy_reference_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gmvq-checkpoint", type=Path, required=True)
    parser.add_argument("--code-selector", type=Path, required=True)
    parser.add_argument("--theta-selector", type=Path, required=True)
    parser.add_argument("--start-decoder", type=Path, required=True)
    parser.add_argument("--selector-dataset", type=Path, required=True)
    parser.add_argument("--current-frame-future", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle = build_policy_reference_bundle(
        gmvq_checkpoint=args.gmvq_checkpoint,
        code_selector=args.code_selector,
        theta_selector=args.theta_selector,
        start_decoder=args.start_decoder,
        selector_dataset=args.selector_dataset,
        current_frame_future=args.current_frame_future,
    )
    output = save_policy_reference_bundle(bundle, args.output)
    print(
        json.dumps(
            {
                "schema": bundle["schema"],
                "output": str(output),
                "stop_code": int(bundle["stop_code"]),
                "scan_points": int(bundle["local_grid"].shape[0]),
                "source_sha256": bundle["source_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

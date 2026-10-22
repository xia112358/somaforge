from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest


class ParsedArguments(Exception):
    def __init__(self, arguments):
        self.arguments = arguments


def _parse_entrypoint(entrypoint, options, monkeypatch):
    if entrypoint == "motion_edit.cli":
        from motion_edit.cli import build_parser

        return build_parser().parse_args(["generate-ref", "--plan", "unused.json", *options])
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(entrypoint, root / "scripts" / f"{entrypoint}.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    required = (["--plan-manifest", "unused.json", "--output-dir", "unused", "--work-dir", "unused"]
                if entrypoint.endswith("batch") else ["--plan", "unused.json", "--output", "unused.npz"])
    parse_args = argparse.ArgumentParser.parse_args

    def capture(parser, *args, **kwargs):
        raise ParsedArguments(parse_args(parser, [*required, *options]))

    with monkeypatch.context() as patch:
        patch.setattr(argparse.ArgumentParser, "parse_args", capture)
        with pytest.raises(ParsedArguments) as captured:
            module.main()
    return captured.value.arguments


@pytest.mark.parametrize("entrypoint", [
    "motion_edit.cli", "generate_contact_aware_pyroki_preview",
    "generate_contact_aware_edited_motion", "generate_contact_aware_batch",
])
@pytest.mark.parametrize("profile", ["legacy", "main", "ik"])
def test_generation_entrypoints_default_to_selected_profile_and_keep_explicit_name(
    tmp_path, monkeypatch, entrypoint, profile,
):
    root = Path(__file__).resolve().parents[3]
    catalog = tmp_path / "profiles.json"
    catalog.write_text(json.dumps({"schema": "somaforge_environment_profiles_v1", "profiles": {
        "ik": {"prefix": "runtime/environments/conda/selected-ik"},
    }}))
    monkeypatch.setenv("SOMAFORGE_ROOT", str(root))
    monkeypatch.setenv("SOMAFORGE_ENV_PROFILE", profile)
    monkeypatch.setenv("SOMAFORGE_ENV_CATALOG", str(catalog))
    expected = "env_somaforge" if profile == "legacy" else str(root / "runtime/environments/conda/selected-ik")
    assert _parse_entrypoint(entrypoint, [], monkeypatch).ik_conda_env == expected
    assert _parse_entrypoint(entrypoint, ["--ik-conda-env", "env_somaforge"], monkeypatch).ik_conda_env == "env_somaforge"

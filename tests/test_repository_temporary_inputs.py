"""Repository boundaries distinguish temporary outputs from required inputs."""
import ast
import pytest
from scripts.check_repository import temporary_input_errors


@pytest.mark.parametrize('source', [
    "sys.path.insert(0, ROOT / 'tmp')",
    "spec_from_file_location('helper', ROOT / 'tmp' / 'helper.py')",
    "data = torch.load('tmp/weights.pt')",
    "source = Path('tmp/source.json'); data = source.read_text()",
    "MANIFEST = 'tmp/dataset.json'",
    "cache = ROOT / 'tmp' / 'compiled'",
])
def test_required_temporary_inputs_are_rejected(source):
    assert temporary_input_errors('fixture.py', ast.parse(source))


@pytest.mark.parametrize('source', [
    "output = ROOT / 'tmp' / 'diagnostic.json'; output.write_text(report)",
    "cache = ROOT / 'runtime/current/cache' / 'compiled'",
    "source = Path('runtime/current/motions/source.json'); data = source.read_text()",
])
def test_temporary_outputs_and_formal_inputs_are_allowed(source):
    assert not temporary_input_errors('fixture.py', ast.parse(source))

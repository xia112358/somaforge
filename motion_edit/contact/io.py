from __future__ import annotations

from pathlib import Path
from typing import Iterable

from motion_edit.contact.schema import ContactAnchorRecord, ContactEventRecord, ContactPatchRecord, ContactTransitionRecord
from motion_edit.io import read_jsonl, write_jsonl

ContactRecord = ContactEventRecord | ContactAnchorRecord | ContactPatchRecord | ContactTransitionRecord


def write_contact_jsonl(path: str | Path, records: Iterable[ContactRecord]) -> None:
    write_jsonl(Path(path).expanduser(), (record.to_dict() for record in records))


def read_contact_jsonl(path: str | Path) -> list[dict]:
    return read_jsonl(Path(path).expanduser())


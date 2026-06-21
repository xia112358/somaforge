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


def read_contact_events(path: str | Path) -> list[ContactEventRecord]:
    return [ContactEventRecord(**record) for record in read_contact_jsonl(path)]


def read_contact_anchors(path: str | Path) -> list[ContactAnchorRecord]:
    return [ContactAnchorRecord(**record) for record in read_contact_jsonl(path)]


def read_contact_patches(path: str | Path) -> list[ContactPatchRecord]:
    return [ContactPatchRecord(**record) for record in read_contact_jsonl(path)]


def read_contact_transitions(path: str | Path) -> list[ContactTransitionRecord]:
    return [ContactTransitionRecord(**record) for record in read_contact_jsonl(path)]

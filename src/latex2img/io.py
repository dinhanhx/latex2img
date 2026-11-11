"""Input readers (arg/stdin/txt/jsonl) and the manifest writer."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO


@dataclass
class InputItem:
    id: str | None
    latex: str
    source: str
    overrides: dict[str, Any] = field(default_factory=dict)


def read_inputs(path: Path) -> list[InputItem]:
    """.txt: one equation per line (blank/# skipped), id = zero-padded line number. .jsonl: objects with latex."""
    items: list[InputItem] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if path.suffix.lower() == ".jsonl":
        seen: set[str] = set()
        for n, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{n}: invalid JSON: {e}") from e
            if not isinstance(obj, dict) or not isinstance(obj.get("latex"), str):
                raise ValueError(f"{path}:{n}: expected an object with a string 'latex'")
            item_id = obj.pop("id", None)
            if item_id is not None:
                item_id = str(item_id)
                if item_id in seen:
                    raise ValueError(f"{path}:{n}: duplicate id {item_id!r}")
                seen.add(item_id)
            latex = obj.pop("latex")
            items.append(InputItem(item_id, latex, f"{path.name}:{n}", obj))
    else:
        width = max(6, len(str(len(lines))))
        for n, line in enumerate(lines, 1):
            if line.strip() and not line.lstrip().startswith("#"):
                items.append(InputItem(str(n).zfill(width), line.strip(), f"{path.name}:{n}"))
    return items


def read_single(arg: str) -> str:
    return sys.stdin.read() if arg == "-" else arg


class ManifestWriter:
    """Writes manifest JSONL to a temp file renamed into place on close, or streams to stdout for '-'."""

    def __init__(self, target: str | Path) -> None:
        self.stdout = str(target) == "-"
        if self.stdout:
            self._fh: TextIO = sys.stdout
        else:
            self.path = Path(target)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._tmp = self.path.with_name(self.path.name + ".tmp")
            self._fh = self._tmp.open("w", encoding="utf-8")

    def write(self, row: dict[str, Any]) -> None:
        self._fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        if not self.stdout:
            self._fh.close()
            self._tmp.replace(self.path)

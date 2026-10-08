"""
JSON file storage backend for deadlines.

Mirrors the pattern of JsonStorage but for Deadline objects,
stored in a separate data/deadlines.json file.
"""

import json
import os
import tempfile
from typing import List

from app.models.deadline import Deadline


DEFAULT_DEADLINES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "deadlines.json"
)


class DeadlineStorage:
    """Persists deadline data to a local JSON file."""

    def __init__(self, file_path: str | None = None) -> None:
        self._file_path: str = file_path or DEFAULT_DEADLINES_FILE

    def save(self, deadlines: List[Deadline]) -> bool:
        target_dir = os.path.dirname(self._file_path)
        if not target_dir:
            target_dir = "."
        tmp_path = None
        try:
            os.makedirs(target_dir, exist_ok=True)
            data = [d.to_dict() for d in deadlines]
            fd, tmp_path = tempfile.mkstemp(
                dir=target_dir, suffix=".tmp", prefix=".deadlines_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=4, ensure_ascii=False)
                    fh.flush()
                    os.fsync(fh.fileno())
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
            os.replace(tmp_path, self._file_path)
            tmp_path = None
            return True
        except Exception as exc:
            print(f"  [DeadlineStorage Error] Could not save: {exc}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return False

    def load(self) -> List[Deadline]:
        if not os.path.exists(self._file_path):
            return []
        try:
            with open(self._file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return [Deadline.from_dict(entry) for entry in data]
        except (IOError, json.JSONDecodeError, KeyError, ValueError) as exc:
            print(f"  [DeadlineStorage Error] Could not load: {exc}")
            return []

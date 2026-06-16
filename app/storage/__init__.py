"""Storage package — persistence backends."""

from app.storage.base_storage import BaseStorage
from app.storage.json_storage import JsonStorage

__all__ = ["BaseStorage", "JsonStorage"]

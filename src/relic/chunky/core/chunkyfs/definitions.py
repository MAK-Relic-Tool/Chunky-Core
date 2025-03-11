from __future__ import annotations

from abc import ABC

from fs.base import FS
from fs.info import Info

ESSENCE_NAMESPACE = "essence"


class ChunkyFS(FS, ABC):
    def getessence(self, path: str) -> Info:
        return self.getinfo(path, [ESSENCE_NAMESPACE])

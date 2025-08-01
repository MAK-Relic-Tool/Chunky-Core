from __future__ import annotations

import itertools
from abc import ABC

from fs.base import FS
from fs.info import Info
from fs.path import join as fs_join
from relic.chunky.core.definitions import ChunkFourCC

ESSENCE_NAMESPACE = "essence"


class ChunkyFS(FS, ABC):
    def getessence(self, path: str) -> Info:
        return self.getinfo(path, [ESSENCE_NAMESPACE])

    def rglob_cc(self, *cc:ChunkFourCC|str) -> Iterator[str]:
        codes = [str(_) for _ in cc] # coerce cc to string
        for (path, dirs, files) in self.walk(namespaces=["essence"]):
            for info in itertools.chain(dirs, files):
                if info.get("essence", "4cc") in codes:
                    yield fs_join(path, info.name)

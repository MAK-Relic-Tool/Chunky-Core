import unittest
from dataclasses import dataclass

import fs
from fs.test import FSTestCases

from relic.chunky.core.chunkyfs import ChunkyFS
from relic.chunky.core.serialization import ChunkyFSSerializer, ChunkHeader


class TestChunkyFS(FSTestCases, unittest.TestCase):
    def make_fs(self):
        return ChunkyFS()


class TestOpener:
    def test_open_fs(self):
        with fs.open_fs("chunky://", create=True) as _:
            pass

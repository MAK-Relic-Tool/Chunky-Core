import unittest

import fs
from fs.test import FSTestCases

from relic.chunky.core.filesystem import ChunkyFS


class TestChunkyFS(FSTestCases, unittest.TestCase):
    def make_fs(self):
        return ChunkyFS()


class TestOpener:
    def test_open_fs(self):
        with fs.open_fs("chunky://", create=True) as _:
            pass

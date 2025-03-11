"""
Provides functions for implementing Chunky Plugins
"""

from relic.chunky.core.chunkyfs.definitions import ChunkyFS
from relic.chunky.core.chunkyfs.opener import (
    ChunkyFsOpener,
    ChunkyFsOpenerPlugin,
    registry,
    open_chunky,
)

__all__ = [
    "ChunkyFS",
    "ChunkyFsOpenerPlugin",
    "ChunkyFsOpener",
    "registry",
    "open_chunky",
]

"""
Definition for types that are common to Relic Chunky Files
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import total_ordering
from typing import Any

from relic.core.serialization import MagicWord


class ChunkType(str, Enum):
    FOLDER = "FOLD"
    DATA = "DATA"


@total_ordering
class ChunkFourCC:
    def __init__(self, code: str) -> None:
        if len(code) != 4:
            raise TypeError("`code` must be a four character long string!")
        self.code = code

    def __str__(self) -> str:
        return self.code

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ChunkFourCC):
            return self.code == other.code
        return str(self) == str(other)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, ChunkFourCC):
            return self.code < other.code
        return str(self) < str(other)


    def __hash__(self) -> int:
        return self.code.__hash__()


@dataclass
class Version:
    """A `Chunky Version`"""

    major: int  # The Major Version
    minor: int = 1  # The Minor Version, this is typically `1`

    def __str__(self) -> str:
        return f"Version {self.major}.{self.minor}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Version):
            return self.major == other.major and self.minor == other.minor
        return super().__eq__(other)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Version):
            return self.major < other.major or (
                self.major == other.major and self.minor < other.minor
            )
        raise TypeError(f"Other is not an  instance of `{self.__class__}`!")

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Version):
            return self.major > other.major or (
                self.major == other.major and self.minor > other.minor
            )
        raise TypeError(f"Other is not an  instance of `{self.__class__}`!")

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Version):
            return self.major < other.major or (
                self.major == other.major and self.minor <= other.minor
            )
        raise TypeError(f"Other is not an  instance of `{self.__class__}`!")

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Version):
            return self.major > other.major or (
                self.major == other.major and self.minor >= other.minor
            )
        raise TypeError(f"Other is not an  instance of `{self.__class__}`!")

    def __hash__(self) -> int:
        return f"{self.major}.{self.minor}".__hash__()


# We include \r\n\x1a\0 because it signals a properly formatted file
MAGIC_WORD = MagicWord(b"Relic Chunky\r\n\x1a\0", "Chunky Magic")


__all__ = ["ChunkType", "ChunkFourCC", "MAGIC_WORD", "Version"]

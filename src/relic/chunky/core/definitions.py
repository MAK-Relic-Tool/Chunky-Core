from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, ClassVar, Any

from relic.core.errors import MismatchError
from serialization_tools.magic import MagicWordIO
from serialization_tools.structx import Struct


class ChunkType(str, Enum):
    Folder = "FOLD"
    Data = "DATA"


class ChunkFourCC:
    def __init__(self, code: str) -> None:
        if len(code) != 4:
            raise TypeError("`code` must be a four character long string!")
        self.code = code

    def __str__(self) -> str:
        return self.code

    def __eq__(self, other:Any) -> bool:
        eq:bool = self.code == other.code
        return eq


@dataclass
class Version:
    """
    A `Chunky Version`
    """

    """ The Major Version """
    major: int
    """ The Minor Version, this is typically `1` """
    minor: int = 1

    LAYOUT: ClassVar[Struct] = Struct("<2I")

    def __str__(self) -> str:
        return f"Version {self.major}.{self.minor}"

    def __eq__(self, other:Any) -> bool:
        if isinstance(other, Version):
            return self.major == other.major and self.minor == other.minor
        return super().__eq__(other)

    def __hash__(self) -> int:
        # Realistically; Version will always be <256
        # But we could manually set it to something much bigger by accident; and that may cause collisions
        TERM_SIZE_IN_BYTES:int = (self.LAYOUT.size // 2)
        return self.major << (TERM_SIZE_IN_BYTES*8) + self.minor

    @classmethod
    def unpack(cls, stream: BinaryIO) -> Version:
        layout: Struct = cls.LAYOUT
        args = layout.unpack_stream(stream)
        return cls(*args)

    def pack(self, stream: BinaryIO) -> int:
        layout: Struct = self.LAYOUT
        args = (self.major, self.minor)
        written:int = layout.pack_stream(stream, *args)
        return written


MagicWord = MagicWordIO(
    Struct("< 16s"), b"Relic Chunky\r\n\x1a\0"
)  # We include \r\n\x1a\0 because it signals a properly formatted file


def _validate_magic_word(self: MagicWordIO, stream: BinaryIO, advance: bool) -> None:
    magic = self.read_magic_word(stream, advance)
    if magic != self.word:
        raise MismatchError("MagicWord", magic, self.word)


@dataclass
class _ChunkLazyInfo:
    jump_to: int
    size: int
    stream: BinaryIO

    def read(self) -> bytes:
        jump_back = self.stream.tell()
        self.stream.seek(self.jump_to)
        buffer = self.stream.read(self.size)
        if len(buffer) != self.size:
            raise MismatchError("Buffer Read Size",len(buffer),self.size)
        self.stream.seek(jump_back)
        return buffer


__all__ = [
    "ChunkFourCC",
    "Version",
    "MagicWord",
    "ChunkType"
]

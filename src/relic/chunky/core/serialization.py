from __future__ import annotations

from typing import BinaryIO

from serialization_tools.structx import Struct

from relic.chunky.core.definitions import ChunkType, ChunkFourCC
from relic.chunky.core.errors import ChunkTypeError
from relic.chunky.core.protocols import StreamSerializer


class ChunkTypeSerializer(StreamSerializer[ChunkType]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> ChunkType:
        buffer: bytes
        (buffer,) = self.layout.unpack_stream(stream)
        try:
            value: str = buffer.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ChunkTypeError(buffer) from exc
        else:
            try:
                return ChunkType(value)
            except ValueError as exc:
                raise ChunkTypeError(value) from exc

    def pack(self, stream: BinaryIO, packable: ChunkType) -> int:
        written:int = self.layout.pack_stream(stream, packable.value)
        return written


class ChunkFourCCSerializer(StreamSerializer[ChunkFourCC]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> ChunkFourCC:
        buffer: bytes
        (buffer,) = self.layout.unpack_stream(stream)
        value: str = buffer.decode("ascii")
        return ChunkFourCC(value)

    def pack(self, stream: BinaryIO, packable: ChunkFourCC) -> int:
        written:int = self.layout.pack_stream(stream, packable.code)
        return written


chunk_type_serializer = ChunkTypeSerializer(Struct("<4s"))
chunk_cc_serializer = ChunkFourCCSerializer(Struct("<4s"))

__all__ = [
    "chunk_cc_serializer",
    "chunk_type_serializer",
    "ChunkTypeSerializer",
    "ChunkFourCCSerializer"
]
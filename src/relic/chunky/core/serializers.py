from __future__ import annotations

from typing import BinaryIO

from serialization_tools.structx import Struct

from relic.chunky.core.definitions import ChunkType, ChunkFourCC, Platform
from relic.chunky.core.errors import (
    ChunkTypeError,
    PlatformNotSupported,
    UnknownPlatformError,
)
from relic.chunky.core.protocols import StreamSerializer


class ChunkTypeSerializer(StreamSerializer[ChunkType]):
    def __init__(self, layout: Struct, encoding: str = "ascii"):
        self.layout = layout
        self.encoding = encoding

    def unpack(self, stream: BinaryIO) -> ChunkType:
        buffer: bytes = self.layout.unpack_stream(stream)[0]
        try:
            value: str = buffer.decode(self.encoding)
        except UnicodeDecodeError:
            raise ChunkTypeError(buffer)
        else:
            try:
                return ChunkType(value)
            except ValueError:
                raise ChunkTypeError(value)

    def pack(self, stream: BinaryIO, packable: ChunkType) -> int:
        value: str = packable.value
        buffer: bytes = value.encode(self.encoding)
        return self.layout.pack_stream(stream, buffer)


class ChunkFourCCSerializer(StreamSerializer[ChunkFourCC]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> ChunkFourCC:
        buffer: bytes
        (buffer,) = self.layout.unpack_stream(stream)
        value: str = buffer.decode("ascii")
        return ChunkFourCC(value)

    def pack(self, stream: BinaryIO, packable: ChunkFourCC) -> int:
        return self.layout.pack_stream(stream, packable.code)


class PlatformSerializer(StreamSerializer[Platform]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO):
        layout: Struct = self.layout
        value: int = layout.unpack_stream(stream)[0]
        try:
            return Platform(value)
        except ValueError:
            raise UnknownPlatformError(value)

    def pack(self, stream: BinaryIO, value: Platform):
        layout: Struct = self.layout
        return layout.pack_stream(stream, value.value)


chunk_type_serializer = ChunkTypeSerializer(Struct("<4s"))
chunk_cc_serializer = ChunkFourCCSerializer(Struct("<4s"))
platform_serializer = PlatformSerializer(Struct("<I"))

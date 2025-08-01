from __future__ import annotations

from typing import (
    BinaryIO,
    Optional,
    Protocol,
)

from relic.core.errors import MismatchError

from relic.chunky.core.definitions import (
    ChunkType,
    ChunkFourCC,
    Version,
)
from relic.chunky.core.errors import ChunkTypeError
from relic.chunky.core.protocols import StaticStreamSerializer


class VersionSerializer(StaticStreamSerializer[Version]):  # pylint: disable = W0223
    _SIZE = 8

    @staticmethod
    def _read_int32(stream: BinaryIO) -> int:
        SIZE = 4
        buffer = stream.read(SIZE)
        if len(buffer) != SIZE:
            raise MismatchError("Buffer Size Mismatch", len(buffer), SIZE)
        value = int.from_bytes(buffer, "little", signed=False)
        return value

    @staticmethod
    def _write_int32(stream: BinaryIO, value: int) -> int:
        SIZE = 4
        buffer = value.to_bytes(SIZE, "little", signed=False)
        if len(buffer) != SIZE:  # Redundant, right?
            raise MismatchError("Buffer Size Mismatch", len(buffer), SIZE)
        written = stream.write(buffer)
        return written

    @classmethod
    def read(cls, stream: BinaryIO) -> Version:
        major = cls._read_int32(stream)
        minor = cls._read_int32(stream)
        return Version(major, minor)

    @classmethod
    def write(cls, stream: BinaryIO, value: Version) -> int:
        written = cls._write_int32(stream, value.major)
        written += cls._write_int32(stream, value.minor)
        return written


class ChunkTypeSerializer(StaticStreamSerializer[ChunkType]):
    _SIZE = 4

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ChunkType:
        buffer: bytes = stream.read(cls._SIZE)
        try:
            value: str = buffer.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ChunkTypeError(buffer) from exc

        try:
            return ChunkType(value)
        except ValueError as exc:
            raise ChunkTypeError(value) from exc

    @classmethod
    def pack(cls, stream: BinaryIO, packable: ChunkType) -> int:
        encoded: bytes = packable.value.encode("ascii")
        if cls._SIZE != len(encoded):
            raise MismatchError("Buffer size mismatch", len(encoded), cls._SIZE)
        written: int = stream.write(encoded)
        return written


class ChunkFourCCSerializer(StaticStreamSerializer[ChunkFourCC]):
    _SIZE = 4

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ChunkFourCC:
        buffer: bytes = stream.read(cls._SIZE)
        value: str = buffer.decode("ascii")
        return ChunkFourCC(value)

    @classmethod
    def pack(cls, stream: BinaryIO, packable: ChunkFourCC) -> int:
        encoded = packable.code.encode("ascii")
        if cls._SIZE != len(encoded):
            raise MismatchError("Buffer size mismatch", len(encoded), cls._SIZE)
        written: int = stream.write(encoded)
        return written


class ChunkHeader(Protocol):  # pylint: disable = R0903
    name: str
    type: ChunkType
    cc: ChunkFourCC
    size: int


def default_slugify_parts(name: str, ext: str, n: Optional[int] = None) -> str:
    # Any chunk which references the parent EssenceFS
    # typically names themselves the full path to the referenced asset
    # unfortunately; that's a BAD name in the ChunkyFS
    # so we need to convert it to a safe ChunkyFS name
    safe_name = name.replace("/", "-").replace("\\", "-")
    if len(safe_name) > 0 and safe_name[-1] == ".":
        safe_name = safe_name[:-1]
    if len(ext) > 0 and ext[0] == ".":
        ext = ext[1:]

    if n is None:
        return f"{safe_name}.{ext}"
    return f"{safe_name} {n}.{ext}"


__all__ = [
    "ChunkTypeSerializer",
    "ChunkFourCCSerializer",
    "ChunkHeader",
    "default_slugify_parts",
]

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    BinaryIO,
    Generic,
    Dict,
    TypeVar,
    Callable,
    Optional,
    Protocol,
    Iterable,
)

from fs.base import FS
from fs.errors import FileExists, DirectoryExists
from serialization_tools.structx import Struct
from relic.core.errors import MismatchError
from relic.chunky.core.definitions import (
    ChunkType,
    ChunkFourCC,
    Version,
    MagicWord,
    _validate_magic_word,
)
from relic.chunky.core.errors import ChunkTypeError, VersionMismatchError
from relic.chunky.core.filesystem import ChunkyFSHandler, ChunkyFS
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
        encoded: bytes = packable.value.encode("ascii")
        written: int = self.layout.pack_stream(stream, encoded)
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
        encoded = packable.code.encode("ascii")
        written: int = self.layout.pack_stream(stream, encoded)
        return written


chunk_type_serializer = ChunkTypeSerializer(Struct("<4s"))
chunk_cc_serializer = ChunkFourCCSerializer(Struct("<4s"))


class MinimalChunkHeader(Protocol):
    name: str
    type: ChunkType
    cc: ChunkFourCC
    size: int


TChunkHeader = TypeVar("TChunkHeader", bound=MinimalChunkHeader)
TChunkyHeader = TypeVar("TChunkyHeader")

_ESSENCE = "essence"


def default_slugify_parts(name: str, ext: str, n: Optional[int] = None) -> str:
    # Any chunk which references the EssenceFS typically names themselves the full path to the references asset
    #   unfortunately; that's a BAD name in the ChunkyFS; so we need to convert it to a safe ChunkyFS name
    safe_name = name.replace("/", "-").replace("\\", "-")

    if safe_name[-1] == ".":
        safe_name = safe_name[:-1]
    if ext[0] == ".":
        ext = ext[1:]

    if n is None:
        return f"{safe_name}.{ext}"
    return f"{safe_name} {n}.{ext}"


@dataclass
class ChunkCollectionHandler(Generic[TChunkHeader]):
    header_serializer: StreamSerializer[TChunkHeader]
    header2meta: Callable[[TChunkHeader], Dict[str, object]]
    meta2header: Callable[[Dict[str, object]], TChunkHeader]
    slugify: Callable[[str, str, Optional[int]], str] = default_slugify_parts

    @staticmethod
    def _get_essence(fs: FS, path: str) -> Dict[str, object]:
        info = fs.getinfo(path, [_ESSENCE])
        return info.raw[_ESSENCE]  # type: ignore

    @staticmethod
    def _set_essence(fs: FS, path: str, essence: Dict[str, object]) -> None:
        mapped = {_ESSENCE: essence}
        fs.setinfo(path, mapped)

    @staticmethod
    def _duplicate_n_generator(starting_n: int = 2) -> Iterable[Optional[int]]:
        yield None
        n = starting_n
        while True:
            yield n
            n += 1

    def _pack_data(self, fs: FS, path: str, stream: BinaryIO) -> int:
        info = self._get_essence(fs, path)
        header = self.meta2header(info)

        with fs.open(path, "rb") as handle:
            data = handle.read()

        header.type = ChunkType.Data
        header.size = len(data)

        written = 0
        written += self.header_serializer.pack(stream, header)
        written += stream.write(data)
        return written

    def _unpack_data(self, fs: FS, stream: BinaryIO, header: TChunkHeader) -> None:
        metadata = self.header2meta(header)
        data = stream.read(header.size)
        for n in self._duplicate_n_generator(2):
            path = self.slugify(header.name, header.cc.code, n)
            try:
                with fs.open(path, "xwb") as handle:
                    handle.write(data)
            except FileExists:
                continue  # Try another 'n' value
            else:
                self._set_essence(fs, path, metadata)
                break

    def _pack_folder(self, fs: FS, stream: BinaryIO) -> int:
        info = self._get_essence(fs, "/")
        header = self.meta2header(info)

        header.type = ChunkType.Folder
        header.size = 0

        write_back = stream.tell()

        written = 0
        written += self.header_serializer.pack(stream, header)
        header.size = self.pack_chunk_collection(fs, stream)
        written += header.size

        # WRITE BACK, don't include in written bytes
        now = stream.tell()
        stream.seek(write_back)
        self.header_serializer.pack(stream, header)
        stream.seek(now)

        return written

    def _unpack_folder(self, fs: FS, stream: BinaryIO, header: TChunkHeader) -> None:
        # Folders shouldn't need to be slugged, but why risk it?
        metadata = self.header2meta(header)
        start, size = stream.tell(), header.size
        for n in self._duplicate_n_generator(2):
            path = self.slugify(header.name, header.cc.code, n)
            try:
                dir_fs = fs.makedir(path)
            except DirectoryExists:
                continue
            else:
                self._set_essence(dir_fs, "/", metadata)
                self.unpack_chunk_collection(dir_fs, stream, start, start + size)
                break

    def unpack_chunk(self, fs: FS, stream: BinaryIO) -> None:
        header = self.header_serializer.unpack(stream)
        if header.type == ChunkType.Data:
            return self._unpack_data(fs, stream, header)
        if header.type == ChunkType.Folder:
            return self._unpack_folder(fs, stream, header)
        raise NotImplementedError(header.type)

    def pack_chunk(self, parent_fs: FS, path: str, stream: BinaryIO) -> int:
        info = parent_fs.getinfo(path)
        if info.is_dir:
            sub_fs = parent_fs.opendir(path)
            return self._pack_folder(sub_fs, stream)
        return self._pack_data(parent_fs, path, stream)

    def unpack_chunk_collection(
        self, fs: FS, stream: BinaryIO, start: int, end: int
    ) -> None:
        stream.seek(start)
        # folders: List[FolderChunk] = []
        # data_chunks: List[RawDataChunk] = []
        while stream.tell() < end:
            self.unpack_chunk(fs, stream)
        if stream.tell() != end:
            # Either change msg name from `Chunk Size` to terminal or somethnig
            #   OR convert terminal positions to 'size' values (by subtracting start).
            raise MismatchError("Chunk Size", stream.tell() - start, end - start)

    def pack_chunk_collection(self, fs: FS, stream: BinaryIO) -> int:
        written = 0
        for path in fs.listdir("/"):
            written += self.pack_chunk(fs, path, stream)
        return written


#
# class NoneHeaderSerializer(StreamSerializer[None]):
#     def unpack(self, stream: BinaryIO) -> None:
#         return None
#
#     def pack(self, stream: BinaryIO, packable: None) -> int:
#         return 0
#
# def _NONE_header2meta(header: None) -> Dict[str, object]:
#     return {}
#
# def _NONE_meta2header(meta: Dict[str, object]) -> None:
#     return None


@dataclass
class ChunkyFSSerializer(ChunkyFSHandler, Generic[TChunkyHeader, TChunkHeader]):
    version: Version
    chunk_serializer: ChunkCollectionHandler[TChunkHeader]

    header_serializer: StreamSerializer[TChunkyHeader]
    header2meta: Callable[[TChunkyHeader], Dict[str, object]]
    meta2header: Callable[[Dict[str, object]], TChunkyHeader]

    def read(self, stream: BinaryIO) -> ChunkyFS:
        _validate_magic_word(MagicWord, stream, True)

        version = Version.unpack(stream)
        if version != self.version:
            raise VersionMismatchError(version, self.version)
        header = self.header_serializer.unpack(stream)
        meta = self.header2meta(header)
        meta["version"] = {
            "major": version.major,
            "minor": version.minor,
        }  # manually inject version into metadata

        fs = ChunkyFS()
        fs.setmeta(meta, _ESSENCE)

        # Start of sub-chunks
        start = stream.tell()
        # jump to end
        stream.seek(0, 2)
        # end of sub-chunks
        end = stream.tell()
        # Read all chunks into the FS, from start byte to end byte
        self.chunk_serializer.unpack_chunk_collection(fs, stream, start, end)
        # return created fs
        return fs

    def write(self, stream: BinaryIO, fs: ChunkyFS) -> int:
        written: int = MagicWord.write_magic_word(stream)
        # TODO, some warning for chunky meta not matching serializer version?
        #   It will definitely fail if all chunks dont get updated metadata for missing fields, so maybe irrelevant?
        written += self.version.pack(stream)
        # Write the header
        meta = fs.getmeta(_ESSENCE)
        header = self.meta2header(meta)  # type: ignore
        written = self.header_serializer.pack(stream, header)
        # Write chunks from the FS into the stream
        written += self.chunk_serializer.pack_chunk_collection(fs, stream)
        return written


__all__ = [
    "chunk_cc_serializer",
    "chunk_type_serializer",
    "ChunkTypeSerializer",
    "ChunkFourCCSerializer",
    "MinimalChunkHeader",
    "TChunkHeader",
    "TChunkyHeader",
    "default_slugify_parts",
    "ChunkCollectionHandler",
    "ChunkyFSSerializer",
]

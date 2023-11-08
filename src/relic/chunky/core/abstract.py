from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from typing import TypeVar, BinaryIO, Optional, Literal, List, Generic, Type

from relic.chunky.core import protocols as p
from relic.chunky.core.definitions import (
    ChunkType,
    Version,
    ChunkFourCCPath,
    ChunkFourCC,
)
from relic.chunky.core.protocols import TCMetadata, ChunkWalk

TCFolder = TypeVar("TCFolder", bound=p.FolderChunk)
TCData = TypeVar("TCData", bound=p.DataChunk)
TChunky = TypeVar("TChunky", bound=p.Chunky)
TChunkyMetadata = TypeVar("TChunkyMetadata")


def _resolve_parent_id(
    cc: ChunkFourCC, parent: Optional[p.ChunkNode]
) -> ChunkFourCCPath:
    if parent is not None and isinstance(parent, p.IdentifiableChunk):
        return parent.fourCC_path / cc
    else:
        return ChunkFourCCPath(cc)


class FolderChunk(Generic[TCMetadata], p.FolderChunk[TCMetadata]):
    def walk(self) -> ChunkWalk:
        yield self, self.folders, self.data_chunks
        for folder in self.folders:
            for _ in folder.walk():
                yield _

    def __init__(
        self,
        chunk_id: ChunkFourCC,
        metadata: TCMetadata,
        folders: Optional[List[TCFolder]] = None,
        data_chunks: Optional[List[TCData]] = None,
        parent: Optional[FolderChunk] = None,
    ):
        self._fourcc = chunk_id
        self.metadata = metadata
        self.folders = folders if folders is not None else []
        self.data_chunks = data_chunks if data_chunks is not None else []
        self.parent = parent

    @property
    def fourCC_path(self) -> ChunkFourCCPath:
        return _resolve_parent_id(self._fourcc, self.parent)

    @property
    def fourCC(self) -> ChunkFourCC:
        return self._fourcc

    @property
    def type(self) -> Literal[ChunkType.Folder]:  # type: ignore
        return ChunkType.Folder


@dataclass
class _ChunkLazyInfo:
    jump_to: int
    size: int
    stream: BinaryIO

    def read(self) -> bytes:
        jump_back = self.stream.tell()
        self.stream.seek(self.jump_to)
        buffer = self.stream.read(self.size)  # TODO error on buffer size mismatch
        self.stream.seek(jump_back)
        return buffer


@dataclass
class DataChunk(p.DataChunk[TCMetadata]):
    _id: ChunkFourCC
    metadata: TCMetadata
    parent: Optional[p.FolderChunk]

    @property
    def type(self) -> Literal[ChunkType.Data]:  # type: ignore
        return ChunkType.Data

    @property
    def fourCC_path(self) -> ChunkFourCCPath:
        return _resolve_parent_id(self._id, self.parent)

    @property
    def fourCC(self) -> ChunkFourCC:
        return self._id


@dataclass
class RawDataChunk(Generic[TCMetadata], p.DataChunk[TCMetadata]):
    _id: ChunkFourCC
    metadata: TCMetadata
    _data: Optional[bytes] = None
    parent: Optional[FolderChunk] = None
    _lazy_info: Optional[_ChunkLazyInfo] = None

    @property
    def type(self) -> Literal[ChunkType.Data]:  # type: ignore
        return ChunkType.Data

    @property
    def data(self) -> bytes:
        if self._data is None:
            if self._lazy_info is None:
                raise TypeError("Data was not loaded!")
            else:
                self._data = self._lazy_info.read()
                self._lazy_info = None
        return self._data

    @data.setter
    def data(self, value: bytes) -> None:
        self._data = value

    @contextmanager
    def open(self, read_only: bool = True):
        data = self.data
        with BytesIO(data) as stream:
            yield stream
            if not read_only:
                stream.seek(0)
                self.data = stream.read()

    @property
    def fourCC_path(self) -> ChunkFourCCPath:
        return _resolve_parent_id(self._id, self.parent)

    @property
    def fourCC(self) -> ChunkFourCC:
        return self._id


@dataclass
class Chunky(
    Generic[TChunkyMetadata, TCFolder, TCData],
    p.Chunky[TChunkyMetadata, TCFolder, TCData],
):
    metadata: TChunkyMetadata
    folders: List[TCFolder]
    data_chunks: List[TCData]

    def walk(self) -> ChunkWalk:
        yield self, self.folders, self.data_chunks
        for folder in self.folders:
            for _ in folder.walk():
                yield _


@dataclass
class API(
    Generic[TChunky, TCFolder, TCData, TChunkyMetadata, TCMetadata],
    p.API[TChunky, TCFolder, TCData, TChunkyMetadata, TCMetadata],
):
    version: Version
    Chunky: Type[TChunky]
    FolderChunk: Type[TCFolder]
    DataChunk: Type[TCData]
    ChunkyMetadata: Type[TChunkyMetadata]
    ChunkMetadata: Type[TCMetadata]
    _serializer: APISerializer[TChunky]

    def read(self, stream: BinaryIO, lazy: bool = False) -> TChunky:
        return self._serializer.read(stream, lazy)

    def write(self, stream: BinaryIO, chunky: TChunky) -> int:
        return self._serializer.write(stream, chunky)


class APISerializer(Generic[TChunky]):
    def read(self, stream: BinaryIO, lazy: bool = False) -> TChunky:
        raise NotImplementedError

    def write(self, stream: BinaryIO, chunky: TChunky) -> int:
        raise NotImplementedError

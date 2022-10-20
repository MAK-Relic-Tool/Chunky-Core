from dataclasses import dataclass
from io import BytesIO
from typing import Dict, BinaryIO

from serialization_tools.structx import Struct

from relic.chunky.core.definitions import Version, ChunkType, ChunkFourCC
from relic.chunky.core.filesystem import ChunkyFS
from relic.chunky.core.protocols import StreamSerializer, T
from relic.chunky.core.serialization import (
    MinimalChunkHeader,
    ChunkyFSSerializer,
    ChunkCollectionHandler,
    chunk_type_serializer,
    chunk_cc_serializer,
)


@dataclass
class ChunkTestHeader(MinimalChunkHeader):
    name: str
    cc: ChunkFourCC
    type: ChunkType
    size: int


class ChunkTestHeaderSerializer(StreamSerializer[ChunkTestHeader]):
    def __init__(self):
        self.NUM = Struct("<I")
        self.type_serializer = chunk_type_serializer
        self.cc_Serializer = chunk_cc_serializer

    def unpack(self, stream: BinaryIO) -> T:
        name_size = self.NUM.unpack_stream(stream)[0]
        name = stream.read(name_size).decode("ascii")
        type = self.type_serializer.unpack(stream)
        cc = self.cc_Serializer.unpack(stream)
        size = self.NUM.unpack_stream(stream)[0]
        return ChunkTestHeader(name, cc, type, size)

    def pack(self, stream: BinaryIO, packable: ChunkTestHeader) -> int:
        written = self.NUM.pack_stream(stream, len(packable.name))
        written += stream.write(packable.name.encode("ascii"))
        written += self.type_serializer.pack(stream, packable.type)
        written += self.cc_Serializer.pack(stream, packable.cc)
        written += self.NUM.pack_stream(stream, packable.size)
        return written


def chunkTestHeader2Meta(header: ChunkTestHeader) -> Dict[str, object]:
    return {
        "name": header.name,
        "4cc": header.cc,
    }


def meta2ChunkTestHeader(meta: Dict[str, object]) -> ChunkTestHeader:
    return ChunkTestHeader(name=meta["name"], cc=meta["4cc"], type=None, size=None)  # type: ignore


class NoneHeaderSerializer(StreamSerializer[None]):
    def unpack(self, stream: BinaryIO) -> T:
        return None

    def pack(self, stream: BinaryIO, packable: T) -> int:
        return 0


def noneHeader2Meta(_) -> Dict:
    return {}


def noneMeta2Header(_) -> None:
    return None


serializer = ChunkyFSSerializer(
    version=Version(0xDE, 0xAD),
    chunk_serializer=ChunkCollectionHandler(
        ChunkTestHeaderSerializer(), chunkTestHeader2Meta, meta2ChunkTestHeader
    ),
    header_serializer=NoneHeaderSerializer(),
    header2meta=noneHeader2Meta,
    meta2header=noneMeta2Header,
)


class TestSerializer:
    def test_repeated_chunk_name(self):
        src_fs = ChunkyFS()
        N = 3
        NAME = "The Same File"
        for n in range(N):
            src_fs.openbin(str(n), "x")
            src_fs.setinfo(
                str(n),
                {
                    "essence": chunkTestHeader2Meta(
                        ChunkTestHeader(NAME, ChunkFourCC("TEST"), ChunkType.Data, 0)
                    )
                },
            )
        with BytesIO() as chunky_blob:
            serializer.write(chunky_blob, src_fs)
            chunky_blob.seek(0)
            dst_fs = serializer.read(chunky_blob)
            files = dst_fs.listdir(
                "/"
            )  # Also dirs, but we didnt make any, so it should only be files
            assert len(files) == N
            for file in files:
                meta = dst_fs.getinfo(file, "essence").raw["essence"]
                assert meta["name"] == NAME

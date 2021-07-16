from dataclasses import dataclass
from io import BytesIO

from relic.chunk_formats.whm.shared import num_layout
from relic.chunky import DataChunk


@dataclass
class SshrChunk:
    name: str

    @classmethod
    def create(cls, chunk: DataChunk) -> 'SshrChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(num_layout.size)
            num = num_layout.unpack(buffer)[0]
            name = stream.read(num).decode("ascii")
            return SshrChunk(name)
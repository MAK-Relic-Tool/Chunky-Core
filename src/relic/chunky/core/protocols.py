from __future__ import annotations

from typing import (
    runtime_checkable,
    TypeVar,
    Protocol,
    BinaryIO,
)

T = TypeVar("T")


@runtime_checkable
class StreamSerializer(Protocol[T]):
    def unpack(self, stream: BinaryIO) -> T:
        raise NotImplementedError

    def pack(self, stream: BinaryIO, packable: T) -> int:
        raise NotImplementedError

__all__ =  ["T", "StreamSerializer"]
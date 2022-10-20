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
        raise NotImplementedError(
            f"{self.__class__.__module__}.{self.__class__.__qualname__}.unpack"
        )

    def pack(self, stream: BinaryIO, packable: T) -> int:
        raise NotImplementedError(
            f"{self.__class__.__module__}.{self.__class__.__qualname__}.pack"
        )


__all__ = ["T", "StreamSerializer"]

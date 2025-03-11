from __future__ import annotations

from typing import (
    runtime_checkable,
    TypeVar,
    Protocol,
    BinaryIO,
    Union,
)

T = TypeVar("T")


@runtime_checkable
class InstancedStreamSerializer(Protocol[T]):
    def unpack(self, stream: BinaryIO) -> T:
        raise NotImplementedError(
            f"{self.__class__.__module__}.{self.__class__.__qualname__}.unpack"
        )

    def pack(self, stream: BinaryIO, packable: T) -> int:
        raise NotImplementedError(
            f"{self.__class__.__module__}.{self.__class__.__qualname__}.pack"
        )


@runtime_checkable
class StaticStreamSerializer(Protocol[T]):
    @classmethod
    def unpack(cls, stream: BinaryIO) -> T:
        raise NotImplementedError(f"{cls.__module__}.{cls.__qualname__}.unpack")

    @classmethod
    def pack(cls, stream: BinaryIO, packable: T) -> int:
        raise NotImplementedError(f"{cls.__module__}.{cls.__qualname__}.pack")


StreamSerializer = Union[InstancedStreamSerializer[T], StaticStreamSerializer[T]]

__all__ = [
    "T",
    "InstancedStreamSerializer",
    "StaticStreamSerializer",
    "StreamSerializer",
]

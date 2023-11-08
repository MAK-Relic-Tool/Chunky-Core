from typing import Union, List, Optional, Generic, TypeVar

from relic.chunky.core.definitions import ChunkType, Version, Platform
from relic.core.errors import MismatchError


class ChunkError(Exception):
    pass


class ChunkTypeError(ChunkError):
    def __init__(self, chunk_type: Union[bytes, str] = None, *args):
        super().__init__(*args)
        self.chunk_type = chunk_type

    def __str__(self):
        msg = f"ChunkType must be {repr(ChunkType.Folder.value)} or {repr(ChunkType.Data.value)}"
        if not self.chunk_type:
            return msg + "!"
        else:
            return msg + f"; got {repr(self.chunk_type)}!"


class ChunkNameError(ChunkError):
    def __init__(self, name: Union[bytes, str] = None, *args):
        super().__init__(*args)
        self.name = name

    def __str__(self):
        msg = f"Chunk name was not parsable ascii text"
        if not self.name:
            return msg + "!"
        else:
            return msg + f"; got {repr(self.name)}!"


T = TypeVar("T")


class NotSupportedError(Exception, Generic[T]):
    def __init__(self, received: T, allowed: List[T]):
        super().__init__()
        self.received = received
        self.allowed = allowed

    def __str__(self) -> str:
        return (
            f"`{self.received}` is not supported. Supported values: `{self.allowed}`."
        )


class VersionMismatchError(MismatchError):
    def __init__(self, received: Version = None, expected: Version = None):
        super().__init__("Version", received, expected)


class VersionNotSupported(NotSupportedError):
    def __init__(self, received: Version, allowed: List[Version]):
        super().__init__(received, allowed)


class PlatformMismatchError(MismatchError):
    def __init__(self, received: Platform = None, expected: Platform = None):
        super().__init__("Platform", received, expected)


class PlatformNotSupported(NotSupportedError):
    def __init__(self, received: Platform, allowed: List[Platform] = None):
        super().__init__(received, allowed)


class UnknownPlatformError(NotSupportedError):
    def __init__(self, received: int):
        allowed: List[int] = [p.value for p in Platform]
        super().__init__(received, allowed)

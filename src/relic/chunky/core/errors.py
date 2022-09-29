from typing import Union, List, Optional

from relic.chunky.core.definitions import ChunkType, Version
from relic.core.errors import MismatchError, RelicToolError


class ChunkError(RelicToolError):
    pass


class ChunkTypeError(ChunkError):
    def __init__(self, chunk_type: Optional[Union[bytes, str]] = None, *args:object) -> None:
        super().__init__(*args)
        self.chunk_type = chunk_type

    def __str__(self) -> str:
        msg = f"ChunkType must be {repr(ChunkType.Folder.value)} or {repr(ChunkType.Data.value)}"
        if not self.chunk_type:
            return msg + "!"
        return msg + f"; got {repr(self.chunk_type)}!"


class ChunkNameError(ChunkError):
    def __init__(self, name: Optional[Union[bytes, str]] = None, *args:object) -> None:
        super().__init__(*args)
        self.name = name

    def __str__(self) -> str:
        msg = "Chunk name was not parsable ascii text"
        if not self.name:
            return msg + "!"
        return msg + f"; got {repr(self.name)}!"


class VersionMismatchError(MismatchError[Version]):
    def __init__(self, received: Optional[Version] = None, expected: Optional[Version] = None):
        super().__init__("Version", received, expected)


class VersionNotSupportedError(RelicToolError):
    """
    An unknown version was provided.
    """

    def __init__(self, received: Version, allowed: List[Version]):
        super().__init__()
        self.received = received
        self.allowed = allowed

    def __str__(self) -> str:
        def str_ver(version: Version) -> str:  # dont use str(version); too verbose
            return f"{version.major}.{version.minor}"

        allowed_str = [str_ver(_) for _ in self.allowed]
        return f"Version `{str_ver(self.received)}` is not supported. Versions supported: `{allowed_str}`"


__all__ = [
    "ChunkError",
    "ChunkTypeError",
    "ChunkNameError",
    "VersionMismatchError",
    "VersionNotSupportedError"
]

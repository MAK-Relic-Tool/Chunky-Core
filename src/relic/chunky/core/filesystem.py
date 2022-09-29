from __future__ import annotations

import abc
import os
from os.path import expanduser
from typing import (
    Optional,
    Dict,
    Any,
    BinaryIO,
    Text,
    Collection,
    Mapping,
    Protocol,
    TypeVar,
    Generic,
    runtime_checkable,
)

import fs.opener.errors
import pkg_resources
from fs import ResourceType
from fs.base import FS
from fs.info import Info
from fs.memoryfs import MemoryFS, _DirEntry, _MemoryFile
from fs.opener import Opener, registry as fs_registry
from fs.opener.parse import ParseResult

from relic.chunky.core.definitions import Version, MagicWord, _validate_magic_word
from relic.chunky.core.errors import VersionNotSupportedError

ESSENCE_NAMESPACE = "essence"

TKey = TypeVar("TKey")
TValue = TypeVar("TValue")


class EntrypointRegistry(Generic[TKey, TValue]):
    def __init__(self, entry_point_path: str, autoload: bool = False):
        self._entry_point_path = entry_point_path
        self._mapping: Dict[TKey, TValue] = {}
        self._autoload = autoload

    def register(self, key: TKey, value: TValue) -> None:
        self._mapping[key] = value

    @abc.abstractmethod
    def auto_register(self, value: TValue) -> None:
        raise NotImplementedError

    def get(self, key: TKey, default: Optional[TValue] = None) -> Optional[TValue]:
        if key in self._mapping:
            return self._mapping[key]

        if self._autoload:
            try:
                entry_point = next(
                    pkg_resources.iter_entry_points(
                        self._entry_point_path, self._key2entry_point_path(key)
                    )
                )
            except StopIteration:
                entry_point = None
            if entry_point is None:
                return default
            self._auto_register_entrypoint(entry_point)
            if key not in self._mapping:
                raise NotImplementedError  # TODO specify autoload failed to load in a usable value
            return self._mapping[key]
        return default

    @abc.abstractmethod
    def _key2entry_point_path(self, key: TKey) -> str:
        raise NotImplementedError

    def _auto_register_entrypoint(self, entry_point: Any) -> None:
        try:
            entry_point_result = entry_point.load()
        except:  # Wrap in exception
            raise
        return self._register_entrypoint(entry_point_result)

    @abc.abstractmethod
    def _register_entrypoint(self, entry_point_result: Any) -> None:
        raise NotImplementedError


@runtime_checkable
class ChunkyFSHandler(Protocol):
    version: Version

    def read(self, stream: BinaryIO) -> ChunkyFS:
        raise NotImplementedError

    def write(self, stream: BinaryIO, essence_fs: ChunkyFS) -> int:
        raise NotImplementedError


class ChunkyFSFactory(EntrypointRegistry[Version, ChunkyFSHandler]):
    def _key2entry_point_path(self, key: Version) -> str:
        return f"v{key.major}.{key.minor}"

    def _register_entrypoint(self, entry_point_result: Any) -> None:
        if isinstance(entry_point_result, ChunkyFSHandler):
            self.auto_register(entry_point_result)
        elif isinstance(entry_point_result, (list, tuple, Collection)):
            version, handler = entry_point_result
            if not isinstance(handler, ChunkyFSHandler):
                handler = handler()
            self.register(version, handler)
        else:
            # Callable; register nested result
            self._register_entrypoint(entry_point_result())

    def auto_register(self, value: ChunkyFSHandler) -> None:
        self.register(value.version, value)

    def __init__(self, autoload: bool = True) -> None:
        super().__init__("relic.chunky.handler", autoload)

    @staticmethod
    def _read_magic_and_version(sga_stream: BinaryIO) -> Version:
        # sga_stream.seek(0)
        jump_back = sga_stream.tell()
        _validate_magic_word(MagicWord, sga_stream, advance=True)
        version = Version.unpack(sga_stream)
        sga_stream.seek(jump_back)
        return version

    def _get_handler(self, version: Version) -> ChunkyFSHandler:
        handler = self.get(version)
        if handler is None:
            # This may raise a 'false positive' if a Null handler is registered
            raise VersionNotSupportedError(version, list(self._mapping.keys()))
        return handler

    def _get_handler_from_stream(
            self, sga_stream: BinaryIO, version: Optional[Version] = None
    ) -> ChunkyFSHandler:
        if version is None:
            version = self._read_magic_and_version(sga_stream)
        return self._get_handler(version)

    def _get_handler_from_fs(
            self, sga_fs: ChunkyFS, version: Optional[Version] = None
    ) -> ChunkyFSHandler:
        if version is None:
            sga_version: Dict[str, int] = sga_fs.getmeta("essence").get("version")  # type: ignore
            version = Version(sga_version["major"], sga_version["minor"])
        return self._get_handler(version)

    def read(
            self, sga_stream: BinaryIO, version: Optional[Version] = None
    ) -> ChunkyFS:
        handler = self._get_handler_from_stream(sga_stream, version)
        return handler.read(sga_stream)

    def write(
            self, sga_stream: BinaryIO, sga_fs: ChunkyFS, version: Optional[Version] = None
    ) -> int:
        handler = self._get_handler_from_fs(sga_fs, version)
        return handler.write(sga_stream, sga_fs)


registry = ChunkyFSFactory(True)


# @fs_registry.install
# Can't use decorator; it breaks subclassing for entrypoints
class ChunkyFSOpener(Opener):
    def __init__(self, factory: Optional[ChunkyFSFactory] = None):
        if factory is None:
            factory = registry
        self.factory = factory

    protocols = ["chunky"]

    def open_fs(
            self,
            fs_url: str,
            parse_result: ParseResult,
            writeable: bool,
            create: bool,
            cwd: str,
    ) -> FS:
        # All ChunkyFS should be writable; so we can ignore that

        # Resolve Path
        if fs_url == "chunky://":
            if create:
                return ChunkyFS()
            raise fs.opener.errors.OpenerError("No path was given and opener not marked for 'create'!"            )

        _path = os.path.abspath(os.path.join(cwd, expanduser(parse_result.resource)))
        path = os.path.normpath(_path)

        # Create will always create a new ChunkyFS if needed
        try:
            with open(path, "rb") as chunky_file:
                return self.factory.read(chunky_file)
        except FileNotFoundError:
            if create:
                return ChunkyFS()
            raise


fs_registry.install(ChunkyFSOpener)


class _ChunkyFile(_MemoryFile):
    ...  # I plan on allowing lazy file loading from the archive; I'll likely need to implement this to do that


class _ChunkyDirEntry(_DirEntry):
    def __init__(self, resource_type: ResourceType, name: Text):
        super().__init__(resource_type, name)
        self.essence: Dict[str, object] = {}

    def to_info(self, namespaces=None):
        # type: (Optional[Collection[Text]]) -> Info
        info = super().to_info(namespaces)
        if (
                namespaces is not None
                and not self.is_dir
                and ESSENCE_NAMESPACE in namespaces
        ):
            info_dict = dict(info.raw)
            info_dict[ESSENCE_NAMESPACE] = self.essence.copy()
            info = Info(info_dict)
        return info


class ChunkyFS(MemoryFS):
    def __init__(self) -> None:
        super().__init__()
        self._chunky_meta: Dict[str, object] = {}

    def getmeta(self, namespace: str = "standard") -> Mapping[str, object]:
        if namespace == ESSENCE_NAMESPACE:
            return self._chunky_meta.copy()
        return super().getmeta(namespace)

    def setmeta(self, meta: Dict[str, Any], namespace: str = "standard") -> None:
        if namespace == ESSENCE_NAMESPACE:
            self._chunky_meta = meta.copy()
        else:
            raise NotImplementedError

    def getessence(self, path: str) -> Info:
        return self.getinfo(path, [ESSENCE_NAMESPACE])

    def _make_dir_entry(
            self, resource_type: ResourceType, name: str
    ) -> _ChunkyDirEntry:
        return _ChunkyDirEntry(resource_type, name)


__all__ = [
    "ESSENCE_NAMESPACE",
    "ChunkyFSHandler",
    "ChunkyFSFactory",
    "_ChunkyFile",
    "_ChunkyDirEntry",
    "ChunkyFS",
    "registry",
    "ChunkyFSOpener",
]

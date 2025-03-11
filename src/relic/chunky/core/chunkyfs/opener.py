from __future__ import annotations

import logging
import os
from os.path import expanduser
from typing import BinaryIO, Protocol, List, Union, Type

import fs.opener.errors
from fs.opener import Opener
from fs.opener.parse import ParseResult
from relic.core.entrytools import EntrypointRegistry
from relic.core.errors import RelicToolError
from relic.core.lazyio import BinaryProxy, get_proxy

from relic.chunky.core.definitions import Version, MAGIC_WORD
from relic.chunky.core.chunkyfs.definitions import ChunkyFS
from relic.chunky.core.serialization import VersionSerializer


_TChunkyFS = TypeError("_TChunkFS", ChunkyFS)

logger = logging.getLogger(__file__)


class ChunkyFsOpenerPlugin(Protocol[_TChunkyFS]):
    @property
    def protocols(self) -> List[str]:
        raise NotImplementedError

    @property
    def versions(self) -> List[Version]:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def open_fs(  # pylint: disable=R0917
        self,
        fs_url: str,
        parse_result: ParseResult,
        writeable: bool,
        create: bool,
        cwd: str,
    ) -> _TChunkyFS:
        raise NotImplementedError


def _get_version(file: Union[BinaryProxy, BinaryIO], advance: bool = False) -> Version:
    binio = get_proxy(file)
    start = binio.tell()
    MAGIC_WORD.validate(binio, advance=True)
    version = VersionSerializer.read(binio)
    if not advance:
        binio.seek(start, os.SEEK_CUR)
    return version


class ChunkyFsOpener(
    EntrypointRegistry[Version, ChunkyFsOpenerPlugin[_TChunkyFS]], Opener
):
    """
    A pyfilesystem opener for the relic chunkies

    Can also be instantiated independently for local use
    """

    EP_GROUP = "relic.chunky.opener"
    protocols = ["chunky"]

    def __init__(self, autoload: bool = True):
        super().__init__(
            entry_point_path=self.EP_GROUP,
            key_func=self._version2key,
            auto_key_func=self._val2keys,
            autoload=autoload,
        )

    @staticmethod
    def _version2key(version: Version) -> str:
        return f"v{version.major}.{version.minor}"

    def open_fs(  # pylint: disable=R0917
        self,
        fs_url: str,
        parse_result: ParseResult,
        writeable: bool,
        create: bool,
        cwd: str,
    ) -> ChunkyFS:

        if parse_result.resource == "":
            if create:
                raise RelicToolError(
                    "Cannot create a Chunky from fs.open_fs or relic.chunky.core.chunkyfs.open_chunky;"
                    " please manually create an empty FS object from an appropriate Chunky Plugin."
                )
            raise fs.opener.errors.OpenerError(
                "No path was given and opener not marked for 'create'!"
            )

        path = os.path.abspath(os.path.join(cwd, expanduser(parse_result.resource)))
        with open(path, "rb") as peeker:
            version = _get_version(
                peeker, True
            )  # advance is true to avoid unnecessary seek
        try:
            opener: Union[Type[ChunkyFsOpenerPlugin], ChunkyFsOpenerPlugin] = self[version]  # type: ignore
        except KeyError as e:
            raise RelicToolError(
                f"Version {version} not supported! Supported Chunky Versions '{list(self.keys())}'."
                f" Are you missing a plugin?"
            ) from e

        if isinstance(opener, type):
            logger.warning("Chunky Opener was a type, creating instance")
            opener: ChunkyFsOpenerPlugin = opener()  # type: ignore

        return opener.open_fs(fs_url, parse_result, writeable, create, cwd)  # type: ignore


registry: ChunkyFsOpener[ChunkyFS] = ChunkyFsOpener()
open_chunky = registry.open_fs

__all__ = ["ChunkyFsOpenerPlugin", "ChunkyFsOpener", "registry", "open_chunky"]

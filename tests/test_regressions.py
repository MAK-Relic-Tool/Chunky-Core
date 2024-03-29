"""
Tests which ensures releases do not break backwards-compatibility by failing to expose modules/names
"""

import importlib
from typing import List, Iterable, Tuple

import pytest

core__all__ = [
    "definitions",
    "errors",
    "filesystem",
    "protocols",
    "serialization",
]

ROOT = "relic.chunky.core"


@pytest.mark.parametrize("submodule", core__all__)
def test_import_module(submodule: str):
    try:
        importlib.import_module(f"{ROOT}.{submodule}")
    except ImportError:
        raise AssertionError(f"{submodule} is no longer exposed!")


definitions__all__ = ["ChunkFourCC", "Version", "MagicWord", "ChunkType"]
errors__all__ = [
    "ChunkError",
    "ChunkTypeError",
    "ChunkNameError",
    "VersionMismatchError",
    "VersionNotSupportedError",
]
fs__all__ = [
    "ESSENCE_NAMESPACE",
    "ChunkyFSHandler",
    "ChunkyFSFactory",
    "_ChunkyFile",
    "_ChunkyDirEntry",
    "ChunkyFS",
    "registry",
    "ChunkyFSOpener",
]
protocols__all__ = ["T", "StreamSerializer"]
serialization__all__ = [
    "chunk_cc_serializer",
    "chunk_type_serializer",
    "ChunkTypeSerializer",
    "ChunkFourCCSerializer",
    "MinimalChunkHeader",
    "TChunkHeader",
    "TChunkyHeader",
    "default_slugify_parts",
    "ChunkCollectionHandler",
    "ChunkyFSSerializer",
]


def module_imports_helper(submodule: str, all: List[str]) -> Iterable[Tuple[str, str]]:
    return zip([submodule] * len(all), all)


@pytest.mark.parametrize(
    ["submodule", "attribute"],
    [
        *module_imports_helper("errors", errors__all__),
        *module_imports_helper("definitions", definitions__all__),
        *module_imports_helper("filesystem", fs__all__),
        *module_imports_helper("protocols", protocols__all__),
        *module_imports_helper("serialization", serialization__all__),
    ],
)
def test_module_imports(submodule: str, attribute: str):
    module = importlib.import_module(f"{ROOT}.{submodule}")
    _ = getattr(module, attribute)

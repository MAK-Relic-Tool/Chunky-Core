# from typing import List, Dict, BinaryIO
#
# from relic.chunky.core import v1, v3, protocols
# from relic.chunky.core._core import Version, MagicWord
#
# _APIS: List[protocols.API] = [v1_1.API, v3_1.API]
# apis: Dict[Version, protocols.API] = {api.version: api for api in _APIS}
#
#
# def read(
#     stream: BinaryIO,
#     lazy: bool = False,
#     api_lookup: Dict[Version, protocols.API] = None,
# ):
#     api_lookup = api_lookup if api_lookup is not None else apis
#     start = stream.tell()
#     MagicWord.read_magic_word(stream)
#     version = Version.unpack(stream)
#     api = api_lookup[version]
#     stream.seek(start)
#     return api.read(stream, lazy)


# This looks like it shouldn't be in core; to avoid cyclic dependencies
# It should also be lazy;
import importlib
from typing import Dict, Optional, List, Tuple

from relic.chunky.core._core import Version
from relic.chunky.core import protocols


def get_api(module_name: str) -> Tuple[Version,protocols.API]:
    module = importlib.import_module(module_name)
    version = getattr(module, "version")
    API = getattr(module, "API")

    if not isinstance(version, Version):
        raise TypeError(f"version is not a `{Version}`")
    if not isinstance(API, protocols.API):
        raise TypeError(f"API is not a `{protocols.API}`")
    return version, API


def gather_apis(modules: Optional[List[str]] = None):
    if modules is None:
        modules = ["v1", "v3"]
    apis: Dict[Version, protocols.API] = {}
    for module in modules:
        try:
            version, api = get_api(module)
            apis[version] = api
        except ImportError:
            pass
    return apis

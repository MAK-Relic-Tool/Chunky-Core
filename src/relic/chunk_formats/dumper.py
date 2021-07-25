import json
import struct
from dataclasses import asdict
from enum import Enum, auto
from os import makedirs
from os.path import splitext, dirname, join, split
from typing import BinaryIO, Optional, Iterable, Tuple, Dict

from relic.chunk_formats.fda.converter import FdaConverter
from relic.chunk_formats.fda.fda_chunky import FdaChunky
from relic.chunk_formats.rsh.rsh_chunky import RshChunky
from relic.chunk_formats.rtx.rtx_chunky import RtxChunky
from relic.chunk_formats.shared.imag.writer import ImagConverter, get_imag_chunk_extension
from relic.chunk_formats.whm.errors import UnimplementedMslcBlockFormat
from relic.chunk_formats.whm.mslc_chunk import DB_UniqueCodes
from relic.chunk_formats.whm.whm_chunky import WhmChunky
from relic.chunk_formats.whm.writer import write_mtllib_to_obj, write_msgr_to_obj, write_msgr_to_mtl, \
    InvalidMeshBufferError
from relic.chunk_formats.wtp.dumper import WTP_LAYER_NAMES
from relic.chunk_formats.wtp.writer import create_mask_image
from relic.chunk_formats.wtp.wtp_chunky import WtpChunky
from relic.chunky import RelicChunky, DataChunk
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky
from relic.chunky.magic import RELIC_CHUNKY_MAGIC
from relic.config import get_latest_dow_game, get_dow_root_directories
from relic.sga.archive import Archive
from relic.sga.dumper import __get_bar_spinner, __safe_makedirs, write_file_as_binary, walk_archive_paths, \
    walk_archives, walk_archive_files, filter_archive_files_by_extension, collapse_walk_in_files
from relic.sga.file import File
from relic.shared import KW_LIST, EnhancedJSONEncoder, filter_path_by_keyword
from relic.ucs import build_locale_environment, get_lang_string_for_file


class ChunkyFormat(Enum):
    Unsupported = auto()
    FDA = auto()
    RSH = auto()
    WHM = auto()
    WTP = auto()
    RTX = auto()

    # Audio = FDA

    @classmethod
    def from_class(cls, instance: AbstractRelicChunky) -> 'ChunkyFormat':
        if isinstance(instance, FdaChunky):
            return ChunkyFormat.FDA
        elif isinstance(instance, WtpChunky):
            return ChunkyFormat.WTP
        elif isinstance(instance, RshChunky):
            return ChunkyFormat.RSH
        elif isinstance(instance, RtxChunky):
            return ChunkyFormat.RTX
        elif isinstance(instance, WhmChunky):
            return ChunkyFormat.WHM
        else:
            return ChunkyFormat.Unsupported

    @classmethod
    def from_extension(cls, extension: str) -> 'ChunkyFormat':
        extension = extension.lstrip(".").lower()

        lookup = {
            'fda': ChunkyFormat.FDA,
            'rsh': ChunkyFormat.RSH,
            'whm': ChunkyFormat.WHM,
            'wtp': ChunkyFormat.WTP,
            'rtx': ChunkyFormat.RTX,
        }
        return lookup.get(extension, ChunkyFormat.Unsupported)

    @classmethod
    def from_path(cls, path: str) -> 'ChunkyFormat':
        _, x = splitext(path)
        return cls.from_extension(x)


def unpack_file(path: str) -> AbstractRelicChunky:
    format = ChunkyFormat.from_path(path)
    with open(path, "rb") as handle:
        unpack_stream(handle, format)


def unpack_archive_file(file: File, check_magic: bool = True) -> Optional[AbstractRelicChunky]:
    """Returns the unpacked relic chunky; if check_magic is True; none is returned for Non-Chunkies"""
    with file.open_readonly_stream() as handle:
        if check_magic and not RELIC_CHUNKY_MAGIC.check_magic_word(handle):
            return None
        format = ChunkyFormat.from_path(file.name)
        return unpack_stream(handle, format)


def unpack_stream(stream: BinaryIO, chunk_format: ChunkyFormat) -> AbstractRelicChunky:
    chunky = RelicChunky.unpack(stream)
    return create(chunky, chunk_format)


def create(chunky: RelicChunky, chunk_format: ChunkyFormat) -> AbstractRelicChunky:
    if chunk_format == ChunkyFormat.RTX:
        return RtxChunky.create(chunky)
    elif chunk_format == ChunkyFormat.FDA:
        return FdaChunky.create(chunky)
    elif chunk_format == ChunkyFormat.RSH:
        return RshChunky.create(chunky)
    elif chunk_format == ChunkyFormat.WHM:
        try:
            return WhmChunky.create(chunky)
        except (UnimplementedMslcBlockFormat, UnicodeDecodeError, struct.error) as e:
            return chunky
    elif chunk_format == ChunkyFormat.WTP:
        return WtpChunky.create(chunky)
    elif chunk_format == ChunkyFormat.Unsupported:
        return chunky


def __create_dirs(output_path: str, use_dirname: bool = True):
    output_path = dirname(output_path) if use_dirname else output_path
    try:
        makedirs(output_path)
    except FileExistsError:
        pass


def __file_replace_name(output_path: str, ext: str, replace_ext: bool = False) -> str:
    no_ext, _ = splitext(output_path)
    return no_ext + ext if replace_ext else output_path


def __dir_replace_name(output_path: str, replace_ext: bool = False) -> str:
    no_ext, _ = splitext(output_path)
    return no_ext if replace_ext else output_path


def dump_fda(fda: FdaChunky, output_path: str, replace_ext: bool = True, use_wave: bool = True,
             locale_environment: Dict[int, str] = None, **kwargs):
    # KWARGS is neccessary to catch unexpected keyword args
    if locale_environment:
        output_path = get_lang_string_for_file(locale_environment, output_path)

    output_path = __file_replace_name(output_path, ".wav" if use_wave else ".aiffc", replace_ext)
    __create_dirs(output_path)
    with open(output_path, "wb") as handle:
        if use_wave:
            FdaConverter.Fda2Wav(fda, handle)
        else:
            FdaConverter.Fda2Aiffr(fda, handle)


def dump_rsh(rsh: RshChunky, output_path: str, replace_ext: bool = True, format: str = "png", force_valid:bool=False, **kwargs):
    output_path = __file_replace_name(output_path, f".{format}", replace_ext)
    if force_valid:
        d, b = split(output_path)
        output_path = join(d, b.replace(" ", "_"))
    # Theres more to dump here, but for now, we only dump the Image
    with open(output_path, "wb") as handle:
        ImagConverter.Imag2Stream(rsh.shrf.texture.imag, handle, format)


def dump_whm(whm: WhmChunky, output_path: str, replace_ext: bool = True, texture_root: str = None,
             texture_ext: str = None, include_meta: bool = False, force_valid:bool=False, **kwargs):
    output_path = __dir_replace_name(output_path, replace_ext)
    obj_path = output_path + f".obj"
    mtl_path = output_path + f".mtl"
    with open(obj_path, "w") as obj_handle:
        write_mtllib_to_obj(obj_handle, mtl_path)
        write_msgr_to_obj(obj_handle, whm.msgr)
    with open(mtl_path, "w") as mtl_handle:
        write_msgr_to_mtl(mtl_handle, whm.msgr, texture_root, texture_ext, force_valid)

    if include_meta:
        dump_chunky(whm, output_path, replace_ext=False, include_meta=True)
        # dump_chunky_meta(whm, output_path, replace_ext=False)
    #     with open(output_path + ".meta", "w") as meta:
    #         json_text = json.dumps(whm.header, indent=4, cls=EnhancedJSONEncoder)
    #         meta.write(json_text)


def dump_chunky_meta(chunky: AbstractRelicChunky, output_path: str, replace_ext: bool = True, **kwargs):
    with open(output_path + ".meta", "w") as meta:
        json_text = json.dumps(chunky.header, indent=4, cls=EnhancedJSONEncoder)
        meta.write(json_text)
    for sub_root, _, chunks in chunky.walk_chunks():
        full_root = join(output_path, sub_root)

        for i, chunk in enumerate(chunks):
            chunk: DataChunk
            file_name_parts = [chunk.header.id.strip(), chunk.header.name.strip().replace("\\", "_").replace("/", "_"),
                               "Chunk", str(i)]
            file_name_parts = (p for p in file_name_parts if p and len(p) > 0)
            file_name = "-".join(file_name_parts)
            full_path = join(full_root, file_name)
            __create_dirs(full_path)

            with open(full_path + f".meta", "w") as handle:
                # d = asdict(chunk.header)
                json_text = json.dumps(chunk.header, indent=4, cls=EnhancedJSONEncoder)
                handle.write(json_text)


def dump_chunky(chunky: RelicChunky, output_path: str, replace_ext: bool = True, include_meta: bool = False, **kwargs):
    output_path = __file_replace_name(output_path, "", replace_ext)

    if include_meta:
        with open(output_path + ".meta", "w") as meta:
            json_text = json.dumps(chunky.header, indent=4, cls=EnhancedJSONEncoder)
            meta.write(json_text)

    for sub_root, _, chunks in chunky.walk_chunks():
        full_root = join(output_path, sub_root)

        for i, chunk in enumerate(chunks):
            chunk: DataChunk
            file_name_parts = [chunk.header.id.strip(), chunk.header.name.strip().replace("\\", "_").replace("/", "_"),
                               "Chunk", str(i)]
            file_name_parts = (p for p in file_name_parts if p and len(p) > 0)
            file_name = "-".join(file_name_parts)
            full_path = join(full_root, file_name)
            __create_dirs(full_path)

            with open(full_path + ".bin", "wb") as handle:
                handle.write(chunk.data)

            if include_meta:
                with open(full_path + f".meta", "w") as handle:
                    # d = asdict(chunk.header)
                    json_text = json.dumps(chunk.header, indent=4, cls=EnhancedJSONEncoder)
                    handle.write(json_text)


def dump_wtp(chunky: WtpChunky, output_path: str, replace_ext: bool = True, **kwargs):
    imag = chunky.tpat.imag
    ext = get_imag_chunk_extension(imag.attr.img)
    output_path = __dir_replace_name(output_path, replace_ext)
    __create_dirs(output_path, use_dirname=False)
    with open(join(output_path, "Diffuse" + ext), "wb") as writer:
        ImagConverter.Imag2Stream(imag, writer)
    for p in chunky.tpat.ptld:
        with open(join(output_path, f"Layer-{WTP_LAYER_NAMES.get(p.layer)}.tga"), "wb") as writer:
            create_mask_image(writer, p, chunky.tpat.info)


def dump_rtx(chunky: RtxChunky, output_path: str, replace_ext: bool = True, format: str = "png",
             force_valid: bool = True, **kwargs):
    output_path = __file_replace_name(output_path, f".{format}", replace_ext)
    if force_valid:
        d, b = split(output_path)
        output_path = join(d, b.replace(" ", "_"))
    # Theres more to dump here, but for now, we only dump the Image
    with open(output_path, "wb") as handle:
        ImagConverter.Imag2Stream(chunky.txtr.imag, handle, format)


def dump(chunky: AbstractRelicChunky, output_path: str, replace_ext: bool = True, **kwargs):
    """Output path may be used as a directory if multiple files are dumped from a single Chunky.
    If a single file is dumped, replace_ext will set the ext to the expected dump extension.
    If multiple files are dumped, replace_ext will trim the extension from output_path.

    It is expected that output_path already exists, subdirectories will be created as needed
    """

    if isinstance(chunky, FdaChunky):
        dump_fda(chunky, output_path, replace_ext, **kwargs)
    elif isinstance(chunky, RshChunky):
        dump_rsh(chunky, output_path, replace_ext, **kwargs)
    elif isinstance(chunky, WhmChunky):
        dump_whm(chunky, output_path, replace_ext, **kwargs)
    elif isinstance(chunky, WtpChunky):
        dump_wtp(chunky, output_path, replace_ext, **kwargs)
    elif isinstance(chunky, RtxChunky):
        dump_rtx(chunky, output_path, replace_ext, **kwargs)
    elif isinstance(chunky, RelicChunky):
        # Special case; ignore replace_ext
        dump_chunky(chunky, output_path, replace_ext=False, **kwargs)
    else:
        raise NotImplementedError(chunky)


#
def dump_archive_files(walk: Iterable[Tuple[str, File]], out_directory: str, dump_non_chunkies: bool = True,
                       dump_unsupported_chunkies: bool = True, **kwargs):
    for directory, file in walk:
        out_path = join(out_directory, directory, file.name)
        file.decompress()  # May be a bug; files aren't being decompressed somewhere? This has led to fewer errors
        try:
            chunky = unpack_archive_file(file)
            if chunky:
                if not dump_unsupported_chunkies and isinstance(chunky, RelicChunky):  # Default means unsupported
                    continue
                __safe_makedirs(out_path)
                dump(chunky, out_path, **kwargs)
            elif dump_non_chunkies:
                __safe_makedirs(out_path)
                write_file_as_binary(directory, file, out_directory)
        except (TypeError,
                InvalidMeshBufferError):  # Covers the two most basic cases: TypeError in Headers & WHM's still mysterious mesh buffer format
            if dump_unsupported_chunkies:
                __safe_makedirs(out_path)
                write_file_as_binary(directory, file, out_directory)


def quick_dump(out_dir: str, input_folder: str = None, ext_whitelist: KW_LIST = None,
               ext_blacklist: KW_LIST = None, lang_code: Optional[str] = "en", **kwargs):
    # HACK to do some pretty printing
    input_folder = input_folder or get_latest_dow_game(get_dow_root_directories())[1]

    if lang_code:
        locale_env = build_locale_environment(input_folder, lang_code)
        kwargs['locale_environment'] = locale_env

    def print_walk_archive_path(w: Iterable[str]) -> Iterable[str]:
        for path in w:
            print(path)
            yield path
            # We can't erase once we new line, so we just print the file; not whether its dumping or being dumped

    current_file = 1
    file_count = 0

    # This doesnt print but is required to setup current_file and file_count
    def print_walk_archive(w: Iterable[Archive]) -> Iterable[Archive]:
        nonlocal current_file
        nonlocal file_count
        for archive in w:
            current_file = 1
            file_count = archive._total_files
            # print("\t", "Files:\t", archive.total_files)
            yield archive
            # print("\r", end="")  # Erase Archive count

    def print_walk_archive_files(w: Iterable[Tuple[str, File]]) -> Iterable[Tuple[str, File]]:
        nonlocal current_file
        nonlocal file_count

        spinner = __get_bar_spinner()
        for p, f in w:
            fp = join(p, f.name)
            print(f"\t({next(spinner)}) Dumping File [ {current_file} / {file_count} (MAX) ] '{fp}'", end="")
            current_file += 1
            yield p, f
            print("\r", end="")
        print("\r", end="\n")  # Erase 'Dumping'

    walk = walk_archive_paths(input_folder)  # , whitelist="Speech")
    # I was trying to speed things up on my speech debugging, I will add whitelist/blacklist for keywords, the current funciton seems to be bugged
    # TODO support whitelist/blacklsit on Archives & Files
    # walk = (f for f in walk if filter_path_by_keyword(f, blacklist=["Speech", "Sound", "Texture"]))
    walk = print_walk_archive_path(walk)  # PRETTY

    walk = walk_archives(walk)

    walk = print_walk_archive(walk)  # PRETTY

    walk = walk_archive_files(walk)
    walk = filter_archive_files_by_extension(walk, ext_whitelist, ext_blacklist)
    walk = collapse_walk_in_files(walk)

    walk = print_walk_archive_files(walk)  # PRETTY

    dump_archive_files(walk, out_dir, **kwargs)
    # How long has this been duplicated?
    # dump_archive_files(walk, out_dir, **kwargs)


if __name__ == "__main__":
    quick_dump(r"D:\Dumps\DOW_I\full_dump", texture_root=r"D:\Dumps\DOW_I\full_dump", texture_ext=".png",
               ext_whitelist=[".rsh"],
               force_valid=True,
               include_meta=False)  # , ext_whitelist=".fda")  # , ext_blacklist=[".wtp",".whm",".rsh",".fda"])

    print("---")
    for u, v in DB_UniqueCodes:
        # v_l = [i for i in v]
        # v_l.sort()
        # 0, 1, ???, 0,
        assert u.reserved_zero_a == 0
        # assert u.flag_b == 1
        assert u.reserved_zero_b == 0
        print(", ".join((str(b) for b in u.unk_b)), "\t~\t", ", ".join((str(w) for w in v)))
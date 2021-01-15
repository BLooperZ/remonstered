import os
import itertools
from typing import IO, Iterable, Mapping, Tuple, cast

from . import lpak
from .resource import read_extractmap
from .utils import copy_stream_buffered


def extract_files(archive: lpak.LPakArchive, files: Iterable[str], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    for fname in files:
        with archive.open(fname, 'rb') as src, open(
            os.path.join(output_dir, os.path.basename(fname)), 'wb'
        ) as out:
            src = cast(IO[bytes], src)
            yield from copy_stream_buffered(src, out)


def get_files_to_extract(
    archive: lpak.LPakArchive, data_files: Mapping[str, Iterable[str]]
) -> Iterable[Tuple[str, Iterable[str]]]:
    for output_dir, patterns in data_files.items():
        yield output_dir, set(
            itertools.chain.from_iterable(
                archive.iglob(pattern) for pattern in patterns
            )
        )


def extract_progress(
    archive: lpak.LPakArchive, data_files: Mapping[str, Iterable[str]]
):
    dirs, files = zip(*get_files_to_extract(archive, data_files))
    all_files = itertools.chain.from_iterable(files)
    action = 'Extracting data files...'
    total_bytes = sum(archive.index[fname].decompressed_size for fname in all_files)
    if total_bytes > 0:
        writes = itertools.chain.from_iterable(
            extract_files(archive, dir_files, output_dir)
            for output_dir, dir_files in zip(dirs, files)
        )
        yield action, (writes, total_bytes)


def extract(archive: lpak.LPakArchive, index_dir: str):
    return extract_progress(archive, read_extractmap(index_dir))

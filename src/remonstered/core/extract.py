import itertools
import os
import pathlib
from collections.abc import Iterable, Iterator, Mapping

from pakal.archive import ArchivePath  # type: ignore[import-untyped]

from . import lpak
from .resource import read_extractmap
from .utils import copy_stream_buffered


def extract_files(
    entries: Iterable[ArchivePath],
    output_dir: str | os.PathLike[str],
) -> Iterator[int]:
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        output_file = output_dir / entry.name
        with (
            entry.open('rb') as src,
            output_file.open('wb') as out,
        ):
            yield from copy_stream_buffered(src, out)


def get_files_to_extract(
    archive: lpak.LPakArchive,
    data_files: Mapping[str, Iterable[str]],
) -> Iterable[tuple[str, Iterable[ArchivePath]]]:
    for output_dir, patterns in data_files.items():
        yield (
            output_dir,
            set(
                itertools.chain.from_iterable(
                    archive.glob(pattern) for pattern in patterns
                )
            ),
        )


def extract_progress(
    archive: lpak.LPakArchive,
    data_files: Mapping[str, Iterable[str]],
) -> Iterator[tuple[str, tuple[Iterator[int], int]]]:
    dirs, files = zip(*get_files_to_extract(archive, data_files), strict=True)
    all_files = itertools.chain.from_iterable(files)
    action = 'Extracting data files...'
    total_bytes = sum(
        archive.index[str(fname)].decompressed_size for fname in all_files
    )
    if total_bytes > 0:
        writes = itertools.chain.from_iterable(
            extract_files(dir_files, output_dir)
            for output_dir, dir_files in zip(dirs, files, strict=True)
        )
        yield action, (writes, total_bytes)


def extract(
    archive: lpak.LPakArchive,
    index_dir: str,
) -> Iterator[tuple[str, tuple[Iterator[int], int]]]:
    return extract_progress(archive, read_extractmap(index_dir))

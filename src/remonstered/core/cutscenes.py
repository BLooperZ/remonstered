import concurrent.futures
import functools
import itertools
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from struct import Struct

from nutcracker.smush import anim
from nutcracker.smush.compress import strip_compress_san

from . import lpak
from .missing import closed_tempfile_name

UINT32LE = Struct('<I')
G_PAK = None


@contextmanager
def suppress_stdout() -> Iterator[None]:
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def extract_ogv_audio(source: bytes, dest: str) -> None:
    with closed_tempfile_name(content=source, mode='w+b', suffix='.ogv') as src:
        try:
            _ = subprocess.run(
                # # Direct extract of audio stream is disabled until supported
                # [
                #     'ffmpeg',
                #     '-y',
                #     '-i',
                #     src,
                #     '-vn',
                #     '-map',
                #     '0:a',
                #     '-acodec',
                #     'copy',
                #     dest,
                # ],
                [
                    'ffmpeg',
                    '-y',
                    '-i',
                    src,
                    '-vn',
                    '-map',
                    '0:1',
                    '-ac',
                    '2',
                    '-b:a',
                    '320k',
                    dest,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError:
            print('ERROR: ffmpeg not available.')
            print('Please make sure ffmpeg binaries can be found in PATH.')
            sys.exit(1)


def get_smush_offsets(res: bytes) -> Iterator[int]:
    _, frames = anim.parse(anim.from_bytes(memoryview(res)))
    for elem in frames:
        yield elem.attribs['offset'] + 8


def get_base_size(pak: lpak.LPakArchive, fname: str) -> int:
    no_file = lpak.LPAKFileEntry(0, 0, 0, 0, 0)
    basename = os.path.basename(fname)
    simplename, ext = os.path.splitext(basename)
    videohd = os.path.join('videohd', f'{simplename}.ogv')
    flubase = f'{simplename}.flu'
    flufile = os.path.join(os.path.dirname(fname), flubase)
    return (
        pak.index[fname].decompressed_size
        + pak.index.get(videohd, no_file).decompressed_size
        + pak.index.get(flufile, no_file).decompressed_size
    )


def compress_single(
    pak: lpak.LPakArchive,
    fname: str | os.PathLike[str],
    output_dir: str | os.PathLike[str] = '.',
) -> int:
    fname = pathlib.Path(fname)
    basename = fname.name
    simplename = fname.stem
    output_dir = pathlib.Path(output_dir)

    videohd = next(pak.iglob(os.path.join('videohd', f'{simplename}.ogv')), None)
    if videohd:
        # override SAN file with compressed version
        with pak.open(str(fname), 'rb') as res, suppress_stdout():
            cont = anim.from_bytes(memoryview(res.read()))
            data = strip_compress_san(cont)

        directory = output_dir / fname.parent.name
        os.makedirs(directory, exist_ok=True)
        (directory / basename).write_bytes(data)

        flubase = f'{simplename}.flu'
        flufile = next(
            pak.iglob(str(fname.parent / flubase)),
            None,
        )
        if flufile:
            with pak.open(flufile, 'rb') as res:
                flu = res.read(0x324)
                flurest = res.read()

            with pak.open(str(fname), 'rb') as res:
                raw_content = res.read()
            assert flurest == b''.join(
                UINT32LE.pack(offset) for offset in get_smush_offsets(raw_content)
            )

            (directory / flubase).write_bytes(
                flu
                + b''.join(UINT32LE.pack(offset) for offset in get_smush_offsets(data))
            )

        # extract audio stream from HD video
        with pak.open(videohd, 'rb') as vid:
            stream = vid.read()
        extract_ogv_audio(stream, str(directory / f'{simplename}.ogg'))
    return get_base_size(pak, str(fname))


def init_worker(archive_name: str) -> None:
    global G_PAK
    G_PAK = lpak.LPakArchive(archive_name)


def convert_worker(fname: str, output_dir: str = '.') -> int:
    global G_PAK
    assert G_PAK is not None
    return compress_single(G_PAK, fname, output_dir)


def compress_and_convert_cutscenes(
    pak: lpak.LPakArchive, files: Iterable[str] = (), output_dir: str = '.'
) -> Iterator[int]:
    worker = functools.partial(convert_worker, output_dir=output_dir)
    with concurrent.futures.ProcessPoolExecutor(
        initializer=init_worker, initargs=(pak.path,)
    ) as executor:
        try:
            results = executor.map(worker, files)
            yield from results
        except KeyboardInterrupt:
            executor.shutdown(wait=False)
            raise


def convert_cutscenes(
    pak: lpak.LPakArchive,
    output_dir: str = '.'
) -> Iterator[tuple[str, tuple[Iterator[int], int]]]:
    patterns = {'video/*.san', 'data/*.san'}
    files = set(
        itertools.chain.from_iterable(pak.iglob(pattern) for pattern in patterns)
    )
    if len(files) > 0:
        action = 'Converting cutscenes...'
        total_size = sum(get_base_size(pak, fname) for fname in files)
        yield (
            action,
            (
                compress_and_convert_cutscenes(pak, files, output_dir),
                total_size,
            ),
        )


if __name__ == '__main__':
    from .utils import drive_progress

    if not len(sys.argv) > 1:
        print('ERROR: Archive filename not specified.')
        sys.exit(1)

    res_file = sys.argv[1]

    with lpak.open(res_file) as pak:
        prog = convert_cutscenes(pak, output_dir='out')
        for action, (task, total) in prog:
            print(action)
            drive_progress(task, total=total)
        print('Done!')

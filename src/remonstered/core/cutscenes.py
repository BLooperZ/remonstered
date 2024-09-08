import concurrent.futures
import functools
import itertools
import os
import pathlib
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from struct import Struct

from nutcracker.smush import anim
from nutcracker.smush.compress import strip_compress_san

from remonstered.core import lpak
from remonstered.core.ffmpeg import closed_tempfile_name, ffmpeg_run

UINT32LE = Struct('<I')
G_PAK = None


@contextmanager
def suppress_stdout() -> Iterator[None]:
    with pathlib.Path(os.devnull).open('w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def extract_ogv_audio(source: bytes, dest: str) -> None:
    with closed_tempfile_name(content=source, mode='w+b', suffix='.ogv') as src:
        ffmpeg_run(
            src,
            dest,
            # # Direct extract of audio stream is disabled until supported
            # ['-vn', '-map', '0:a', '-acodec', 'copy'],  # noqa: ERA001
            # Downmix to stereo
            ['-vn', '-map', '0:1', '-ac', '2', '-b:a', '320k'],
        )


def get_smush_offsets(res: bytes) -> Iterator[int]:
    _, frames = anim.parse(anim.from_bytes(memoryview(res)))
    for elem in frames:
        yield elem.attribs['offset'] + 8


def get_base_size(pak: lpak.LPakArchive, fname: str) -> int:
    no_file = lpak.LPAKFileEntry(0, 0, 0, 0, 0)
    path = pathlib.Path(fname)
    videohd = str(pathlib.Path('videohd', f'{path.stem}.ogv'))
    flubase = f'{path.stem}.flu'
    flufile = str(path.parent / flubase)
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

    videohd_path = str(pathlib.Path('videohd', f'{fname.stem}.ogv'))

    entry = next(pak.glob(str(fname)))
    videohd = next(pak.glob(str(videohd_path)), None)
    if videohd:
        raw_content = entry.read_bytes()
        # override SAN file with compressed version
        with suppress_stdout():
            cont = anim.from_bytes(memoryview(raw_content))
            data = strip_compress_san(cont)

        directory = output_dir / fname.parent.name
        os.makedirs(directory, exist_ok=True)
        (directory / basename).write_bytes(data)

        flubase = f'{simplename}.flu'
        flufile = next(
            pak.glob(str(fname.parent / flubase)),
            None,
        )
        if flufile:
            flu = flufile.read_bytes()
            flu, flurest = flu[:0x324], flu[0x324:]

            assert flurest == b''.join(
                UINT32LE.pack(offset) for offset in get_smush_offsets(raw_content)
            )

            (directory / flubase).write_bytes(
                flu
                + b''.join(UINT32LE.pack(offset) for offset in get_smush_offsets(data))
            )

        # extract audio stream from HD video
        extract_ogv_audio(videohd.read_bytes(), str(directory / f'{simplename}.ogg'))
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
        initializer=init_worker, initargs=(pak._filename,) # type: ignore[arg-type] # noqa: SLF001
    ) as executor:
        try:
            results = executor.map(worker, files)
            yield from results
        except KeyboardInterrupt:
            executor.shutdown(wait=False)
            raise


def convert_cutscenes(
    pak: lpak.LPakArchive, output_dir: str = '.'
) -> Iterator[tuple[str, tuple[Iterator[int], int]]]:
    patterns = {'video/*.san', 'data/*.san'}
    files = {
        str(entry)
        for entry in itertools.chain.from_iterable(
            pak.glob(pattern) for pattern in patterns
        )
    }
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

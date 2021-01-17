import concurrent.futures
import functools
import io
import itertools
import os
import subprocess
import sys
from struct import Struct
from contextlib import contextmanager
from typing import Iterable

from nutcracker.compress_san import strip_compress_san
from nutcracker.smush.preset import smush

from . import lpak
from .missing import closed_tempfile_name


UINT32LE = Struct('<I')
G_PAK = None


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
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


def get_smush_offsets(res):
    with io.BytesIO(res) as stream:
        anim = smush.assert_tag('ANIM', smush.untag(stream))
        assert stream.read() == b''

    _, *frames = smush.read_chunks(anim)
    for (offset, _) in frames:
        yield offset + 8


def get_base_size(pak: lpak.LPakArchive, fname: str):
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


def compress_single(pak: lpak.LPakArchive, fname: str, output_dir: str = '.'):
    basename = os.path.basename(fname)
    simplename, ext = os.path.splitext(basename)

    videohd = next(pak.iglob(os.path.join('videohd', f'{simplename}.ogv')), None)
    if videohd:
        # override SAN file with compressed version
        with pak.open(fname, 'rb') as res, suppress_stdout():
            data = strip_compress_san(res)

        directory = os.path.join(output_dir, os.path.basename(os.path.dirname(fname)))
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, basename), 'wb') as out:
            out.write(data)

        flubase = f'{simplename}.flu'
        flufile = next(
            pak.iglob(os.path.join(os.path.dirname(fname), flubase)),
            None,
        )
        if flufile:
            with pak.open(flufile, 'rb') as res:
                flu = res.read(0x324)
                flurest = res.read()

            with pak.open(fname, 'rb') as res:
                raw_content = res.read()
            assert flurest == b''.join(
                UINT32LE.pack(offset) for offset in get_smush_offsets(raw_content)
            )

            with open(os.path.join(directory, flubase), 'wb') as out:
                out.write(flu)
                out.write(
                    b''.join(
                        UINT32LE.pack(offset) for offset in get_smush_offsets(data)
                    )
                )

        # extract audio stream from HD video
        with pak.open(videohd, 'rb') as vid:
            stream = vid.read()
        extract_ogv_audio(stream, os.path.join(directory, f'{simplename}.ogg'))
    return get_base_size(pak, fname)


def init_worker(archive_name: str):
    global G_PAK
    G_PAK = lpak.LPakArchive(archive_name)


def convert_worker(fname: str, output_dir: str = '.'):
    global G_PAK
    assert G_PAK is not None
    return compress_single(G_PAK, fname, output_dir)


def compress_and_convert_cutscenes(
    pak: lpak.LPakArchive, files: Iterable[str] = (), output_dir: str = '.'
):
    worker = functools.partial(convert_worker, output_dir=output_dir)
    with concurrent.futures.ProcessPoolExecutor(
        initializer=init_worker, initargs=(pak.path,)
    ) as executor:
        try:
            results = executor.map(worker, files)
            yield from results
        except KeyboardInterrupt as kbi:
            executor.shutdown(wait=False)
            raise kbi


def convert_cutscenes(pak: lpak.LPakArchive, output_dir: str = '.'):
    patterns = {'video/*.san', 'data/*.san'}
    files = set(
        itertools.chain.from_iterable(pak.iglob(pattern) for pattern in patterns)
    )
    if len(files) > 0:
        action = 'Converting cutscenes...'
        total_size = sum(get_base_size(pak, fname) for fname in files)
        yield action, (
            compress_and_convert_cutscenes(pak, files, output_dir),
            total_size,
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

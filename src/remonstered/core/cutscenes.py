import itertools
import os
import subprocess
import sys
from contextlib import contextmanager
from typing import Iterable

from nutcracker.compress_san import strip_compress_san

from . import lpak
from .missing import closed_tempfile_name


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


def compress_and_convert_cutscenes(
    pak: lpak.LPakArchive, files: Iterable[str] = (), output_dir: str = '.'
):
    for fname in files:
        basename = os.path.basename(fname)
        simplename, ext = os.path.splitext(basename)

        videohd = next(pak.iglob(os.path.join('videohd', f'{simplename}.ogv')), None)
        if videohd:
            # override SAN file with compressed version
            with pak.open(fname, 'rb') as res, suppress_stdout():
                data = strip_compress_san(res)

            directory = os.path.join(
                output_dir, os.path.basename(os.path.dirname(fname))
            )
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, basename), 'wb') as out:
                out.write(data)

            # extract audio stream from HD video
            with pak.open(videohd, 'rb') as vid:
                stream = vid.read()
            extract_ogv_audio(stream, os.path.join(directory, f'{simplename}.ogg'))
        yield 1


def convert_cutscenes(pak: lpak.LPakArchive, output_dir: str = '.'):
    patterns = {'video/*.san', 'data/*.san'}
    files = set(
        itertools.chain.from_iterable(pak.iglob(pattern) for pattern in patterns)
    )
    if len(files) > 0:
        action = 'Converting cutscenes...'
        total_size = len(files)
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
        prog = convert_cutscenes(pak)
        for action, (task, total) in prog:
            print(action)
            drive_progress(task, total=total)
        print('Done!')

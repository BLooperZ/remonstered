import os
import sys
import subprocess
import tempfile
from contextlib import contextmanager
from functools import partial
from typing import AnyStr, Iterator, Mapping, Optional


@contextmanager
def closed_tempfile_name(
    content: Optional[AnyStr] = None, *args, **kwargs
) -> Iterator[str]:
    with tempfile.NamedTemporaryFile(  # type: ignore
        *args, **kwargs, delete=False
    ) as tmp:
        try:
            if content:
                tmp.write(content)
            tmp.close()
            yield tmp.name
        finally:
            os.unlink(tmp.name)


def cut_audio_without_re_encoding(source: bytes, start: str, end: str):
    with closed_tempfile_name(
        content=source, mode='w+b', suffix='.mp3'
    ) as src, closed_tempfile_name(mode='w+b', suffix='.mp3') as dst:
        try:
            _ = subprocess.run(
                ['ffmpeg', '-y', '-i', src, '-ss', start, '-t', end, '-c', 'copy', dst],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            with open(dst, 'rb') as f:
                return f.read()
        except OSError:
            print('ERROR: ffmpeg not available.')
            print('Please make sure ffmpeg binaries can be found in PATH.')
            sys.exit(1)


def cut_stream(source: str, start: str, end: str, container: Mapping[str, bytes]):
    return cut_audio_without_re_encoding(container[source], start, end)


missing = {
    'ben_OFFICE-LINE2019': partial(
        cut_stream, 'ben_BIG-DOOR-LINE2015', '00:00:00.02', '00:00:01.20'
    )
}


def build_missing_entry(container: Mapping[str, bytes], fname: str) -> bytes:
    return missing[fname](container)

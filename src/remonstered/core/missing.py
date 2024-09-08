from collections.abc import Mapping
from functools import partial

from remonstered.core.ffmpeg import closed_tempfile_name, ffmpeg_run


def cut_audio_without_re_encoding(source: bytes, start: str, end: str) -> bytes:
    with closed_tempfile_name(
        content=source, mode='w+b', suffix='.mp3'
    ) as src, closed_tempfile_name(mode='w+b', suffix='.mp3') as dst:
        ffmpeg_run(src, dst, ['-ss', start, '-t', end, '-c', 'copy'])
        return dst.read_bytes()


def cut_stream(
    source: str,
    start: str,
    end: str,
    container: Mapping[str, bytes],
) -> bytes:
    return cut_audio_without_re_encoding(container[source], start, end)


missing = {
    'ben_OFFICE-LINE2019': partial(
        cut_stream, 'ben_BIG-DOOR-LINE2015', '00:00:00.02', '00:00:01.20'
    )
}


def build_missing_entry(container: Mapping[str, bytes], fname: str) -> bytes:
    return missing[fname](container)

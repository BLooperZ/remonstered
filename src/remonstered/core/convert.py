import concurrent.futures
import io
import warnings
from collections.abc import Iterable, Iterator
from functools import partial

from remonstered.core.ffmpeg import LibraryFFMPEGNotAvailableError

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import pydub  # type: ignore[import-untyped]



def convert_sound(src_ext: str, target_ext: str, snd_data: bytes) -> bytes:
    if src_ext == target_ext:
        return snd_data
    with io.BytesIO(snd_data) as in_snd:
        snd = pydub.AudioSegment.from_file(in_snd, format=src_ext)
    with io.BytesIO() as out_snd:
        snd.export(out_snd, format=target_ext)
        return out_snd.getvalue()


def convert_streams(
    streams: Iterable[tuple[bytes, bytes, bytes]], src_ext: str, target_ext: str
) -> Iterator[tuple[bytes, bytes, bytes]]:
    offs, tags_info, sounds = zip(*streams, strict=True)
    convert = partial(convert_sound, src_ext, target_ext)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        try:
            converted = executor.map(convert, sounds)
            yield from zip(offs, tags_info, converted, strict=True)
        except KeyboardInterrupt:
            executor.shutdown(wait=False)
            raise


def test_converter(target_ext: str) -> None:
    try:
        with io.BytesIO() as stream:
            pydub.AudioSegment.empty().export(stream, format=target_ext)
    except OSError as ose:
        raise LibraryFFMPEGNotAvailableError('ffmpeg') from ose


def format_streams(
    streams: Iterable[tuple[bytes, bytes, bytes]],
    src_ext: str,
    target_ext: str,
) -> Iterator[tuple[bytes, bytes, bytes]]:
    if src_ext == target_ext:
        return iter(streams)
    test_converter(target_ext)
    return convert_streams(streams, src_ext, target_ext)

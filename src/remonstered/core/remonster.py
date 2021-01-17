#!/usr/bin/env python
import io
import tempfile
import itertools
from struct import Struct
from typing import IO, Iterable, Optional, Tuple

from . import lpak
from .audio import get_output_extension
from .convert import format_streams
from .utils import copy_stream_buffered, consume, iterate
from .resource import fetch_sources

UINT32BE = Struct('>I')


def collect_streams(
    output_idx: IO[bytes],
    audio_stream: IO[bytes],
    streams: Iterable[Tuple[bytes, bytes, bytes]],
):
    for offset, tags, stream in streams:
        output_idx.write(offset)
        output_idx.write(UINT32BE.pack(audio_stream.tell()))
        output_idx.write(UINT32BE.pack(len(tags)))

        audio_stream.write(tags)
        audio_stream.write(stream)
        output_idx.write(UINT32BE.pack(len(stream)))

        yield offset, tags, stream


def finalize_output(output: IO[bytes], index: IO[bytes], stream: IO[bytes]):
    output.write(UINT32BE.pack(index.tell()))
    index.seek(0, io.SEEK_SET)
    stream.seek(0, io.SEEK_SET)

    return itertools.chain(
        copy_stream_buffered(index, output), copy_stream_buffered(stream, output)
    )


def build_monster(
    streams: Iterable[Tuple[bytes, bytes, bytes]], output_file: str, index_size: int
):
    with io.BytesIO() as output_idx, tempfile.TemporaryFile() as audio_stream:

        action = 'Collecting audio streams...'
        streaming = iterate(collect_streams(output_idx, audio_stream, streams))
        yield action, (streaming, index_size)
        consume(streaming)

        action = 'Writing output file...'
        total_size = output_idx.tell() + audio_stream.tell()
        with open(output_file, 'wb') as output:
            writes = finalize_output(output, output_idx, audio_stream)
            yield action, (writes, total_size)
            consume(writes)


def remonster(
    archive: lpak.LPakArchive,
    index_dir: Optional[str] = '.',
    target_ext: Optional[str] = None,
):
    with fetch_sources(archive, index_dir) as source:
        ext, index, source_streams = source
        target_ext = target_ext or ext
        output_ext = get_output_extension(target_ext)
        streams = format_streams(source_streams, ext, target_ext)
        yield from build_monster(streams, f'monster.{output_ext}', len(index))

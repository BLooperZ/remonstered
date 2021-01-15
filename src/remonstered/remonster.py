#!/usr/bin/env python
import io
import tempfile
import struct
import itertools
from typing import IO, Iterable, Optional, Tuple

import click

from remonstered import lpak

from .audio import get_output_extension, output_exts
from .convert import format_streams
from .utils import copy_stream_buffered, drive_progress, consume, iterate
from .resource import fetch_sources


def collect_streams(
    output_idx: IO[bytes],
    audio_stream: IO[bytes],
    streams: Iterable[Tuple[bytes, bytes, bytes]],
):
    for offset, tags, stream in streams:
        output_idx.write(offset)
        output_idx.write(struct.pack('>I', audio_stream.tell()))
        output_idx.write(struct.pack('>I', len(tags)))

        audio_stream.write(tags)
        audio_stream.write(stream)
        output_idx.write(struct.pack('>I', len(stream)))

        yield offset, tags, stream


def finalize_output(output: IO[bytes], index: IO[bytes], stream: IO[bytes]):
    output.write(struct.pack('>I', index.tell()))
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


@click.command()
@click.argument('filename', metavar='<filename>', required=False, default='./tenta.cle')
@click.option(
    '--format',
    '-f',
    'audio_format',
    type=str,
    metavar=f"[{'|'.join(output_exts)}]",
    default=None,
    help='Output audio format',
)
@click.option(
    '--index',
    '-i',
    'index_dir',
    type=click.Path(),
    metavar='<path>',
    default=None,
    help='Path to directory with .tbl files',
)
@click.help_option('-h', '--help')
def main(filename, index_dir, audio_format):
    prog = remonster(filename, index_dir, audio_format)
    for action, (task, total) in prog:
        print(action)
        drive_progress(task, total=total)
    print('Done!')


if __name__ == '__main__':
    import multiprocessing as mp

    mp.freeze_support()

    main()

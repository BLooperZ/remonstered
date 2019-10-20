#!/usr/bin/env python
import sys
import io
import binascii
import tempfile
import struct
import itertools
import functools

import fsb5

from convert import format_streams
from missing import build_missing_entry

def print_progress(total, iterable, size=50):
    init = '-' * (size - 1)
    print(f'\r|>{init}| Completed: {0:0.2f}%', end='\r')
    for idx, _ in enumerate(iterable):
        if total:
            prefix = '=' * ((idx * size) // total)
            suffix = '-' * (((total - idx - 1) * size) // total)
            completed = (idx + 1) / total
            print(f'\r|{prefix}>{suffix}| Completed: {100 * completed:0.2f}%', end='\r')
    print()

output_exts = {
    'ogg': 'sog',
    'flac': 'sof',
    'mp3': 'so3'
}

def collect_streams(output_idx, audio_stream, streams):
    for offset, tags, stream in streams:
        output_idx.write(offset)
        output_idx.write(struct.pack('>I', audio_stream.tell()))
        output_idx.write(struct.pack('>I', len(tags)))

        audio_stream.write(tags)
        audio_stream.write(stream)
        output_idx.write(struct.pack('>I', len(stream)))

        yield offset, tags, stream

def build_monster(streams, output_file, progress):
    with io.BytesIO() as output_idx, \
            tempfile.TemporaryFile() as audio_stream:

        print('Collecting audio streams...')
        progress(collect_streams(output_idx, audio_stream, streams))

        print('Writing output file...')
        total = calculate_stream_size(output_idx.tell(), audio_stream.tell())
        progress = functools.partial(print_progress, total)
        with open(output_file, 'wb') as output:
            output.write(struct.pack('>I', output_idx.tell()))
            output_idx.seek(0, io.SEEK_SET)
            audio_stream.seek(0, io.SEEK_SET)
            progress(itertools.chain(
                copy_stream_buffered(output_idx, output),
                copy_stream_buffered(audio_stream, output)
            ))

def read_index(monster_table, tags_table):
    for sound, tags in zip(monster_table, tags_table):
        sound, tags = sound[:-1], tags[:-1]
        offset, fname = sound[:8], sound[8:]
        yield binascii.unhexlify(offset.encode()), binascii.unhexlify(tags.encode()), fname

def calculate_stream_size(*sizes):
    return sum(((size + io.DEFAULT_BUFFER_SIZE - 1) // io.DEFAULT_BUFFER_SIZE) for size in sizes)

def copy_stream_buffered(in_stream, out_stream):
    for buffer in iter(functools.partial(in_stream.read, io.DEFAULT_BUFFER_SIZE), b''):
        out_stream.write(buffer)
        yield len(buffer)

def read_streams(speech, index):
    for offset, tags, fname in index:
        stream = speech.get(f'EN_HQ_{fname}', None)
        if not stream:
            stream = build_missing_entry(speech, fname)
        yield offset, tags, stream

if __name__ == '__main__':
    import multiprocessing as mp

    mp.freeze_support()

    try:
        with open('monster.tbl', 'r') as monster_table, \
                open('tags.tbl', 'r') as tags_table:
            index = list(read_index(monster_table, tags_table))

        with open('iMUSEClient_SPEECH.fsb', 'rb') as f:
            fsb = fsb5.FSB5(f.read())
            speech = {sample.name: sample.data for sample in fsb.samples}
            ext = fsb.get_sample_extension()

    except OSError as e:
        print(f'ERROR: Failed to load file: {e.filename}.')
        print('Please make sure this file is available in current working directory.')
        sys.exit(1)

    target_ext = ext
    if len(sys.argv) > 1:
        target_ext = sys.argv[1]
        if target_ext not in output_exts:
            available = '|'.join(output_exts)
            print(f'ERROR: Unsupported audio format: {target_ext}.')
            print(f'Available options are <{available}>.')
            sys.exit(1)

    output_ext = output_exts[target_ext]
    streams = format_streams(read_streams(speech, index), ext, target_ext)
    build = build_monster(streams, f'monster.{output_ext}', progress=functools.partial(print_progress, len(index)))
    print('Done!')

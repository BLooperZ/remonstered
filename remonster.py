#!/usr/bin/env python
import sys
import io
import binascii
import tempfile
import os
import json
import struct
import itertools
import functools

from tqdm import tqdm

import lpak
from convert import format_streams
from utils import copy_stream_buffered
from soundbank import get_soundbanks_view
from missing import build_missing_entry

output_exts = {
    'ogg': 'sog',
    'flac': 'sof',
    'mp3': 'so3'
}

print_progress = functools.partial(
    tqdm,
    ascii=f'->>=',
    bar_format='[{bar:50}] Completed: {percentage:0.2f}%'
)

def collect_streams(output_idx, audio_stream, streams):
    for offset, tags, stream in streams:
        output_idx.write(offset)
        output_idx.write(struct.pack('>I', audio_stream.tell()))
        output_idx.write(struct.pack('>I', len(tags)))

        audio_stream.write(tags)
        audio_stream.write(stream)
        output_idx.write(struct.pack('>I', len(stream)))

        yield offset, tags, stream

def build_monster(streams, output_file, index_size):
    with io.BytesIO() as output_idx, \
            tempfile.TemporaryFile() as audio_stream:

        print('Collecting audio streams...')
        with print_progress(total=index_size) as pbar:
            for _ in collect_streams(output_idx, audio_stream, streams):
                pbar.update(1)

        print('Writing output file...')
        total_size = output_idx.tell() + audio_stream.tell()
        with open(output_file, 'wb') as output:
            output.write(struct.pack('>I', output_idx.tell()))
            output_idx.seek(0, io.SEEK_SET)
            audio_stream.seek(0, io.SEEK_SET)

            writes = itertools.chain(
                copy_stream_buffered(output_idx, output),
                copy_stream_buffered(audio_stream, output)
            )
            with print_progress(total=total_size) as pbar:
                for dp in writes:
                    pbar.update(dp)

def read_hex(hexstr):
    return binascii.unhexlify(hexstr.encode())

def read_index(monster_table, tags_table):
    for sound, tags in zip(monster_table, tags_table):
        sound, tags = sound[:-1], tags[:-1]
        offset, fname = sound[:8], sound[8:]
        yield read_hex(offset), read_hex(tags), fname

def read_streams(sounds, index):
    for offset, tags, fname in index:
        stream = sounds.get(fname, None)
        if not stream:
            stream = build_missing_entry(sounds, fname)
        yield offset, tags, stream

def read_tables(path):
    filemap = os.path.join(path, 'monster.tbl')
    tagmap = os.path.join(path, 'tags.tbl')
    with open(filemap, 'r') as monster_table, \
            open(tagmap, 'r') as tags_table:
        return list(read_index(monster_table, tags_table))

def read_audiomap(path):
    mapfile = os.path.join(path, 'stream.json')
    with open(mapfile, 'r') as audiomap:
        return json.load(audiomap)

if __name__ == '__main__':
    import multiprocessing as mp

    mp.freeze_support()

    # TODO: accept file path as first parameter with current directory as default
    res_file = './tenta.cle'

    try:
        index, audiomap = read_tables('.'), read_audiomap('.')

        with lpak.open(res_file) as pak:
            with get_soundbanks_view(pak, audiomap) as (ext, sounds):
                target_ext = ext
                if len(sys.argv) > 1:
                    target_ext = sys.argv[1]
                    if target_ext not in output_exts:
                        available = '|'.join(output_exts)
                        print(f'ERROR: Unsupported audio format: {target_ext}.')
                        print(f'Available options are <{available}>.')
                        sys.exit(1)

                output_ext = output_exts[target_ext]
                streams = format_streams(read_streams(sounds, index), ext, target_ext)
                build = build_monster(streams, f'monster.{output_ext}', len(index))
                print('Done!')

    except OSError as e:
        print(f'ERROR: Failed to load file: {e.filename}.')
        print('Please make sure this file is available in current working directory.')
        sys.exit(1)

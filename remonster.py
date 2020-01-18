#!/usr/bin/env python
import sys
import io
import binascii
import tempfile
import struct
import itertools
import functools

import fsb5
from tqdm import tqdm

import lpak
from convert import format_streams
from utils import copy_stream_buffered

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

def read_index(monster_table, tags_table):
    for sound, tags in zip(monster_table, tags_table):
        sound, tags = sound[:-1], tags[:-1]
        offset, fname = sound[:8], sound[8:]
        yield binascii.unhexlify(offset.encode()), binascii.unhexlify(tags.encode()), fname

def read_streams(sfx, speech, index):
    for offset, tags, fname in index:
        stream = sfx[fname] if fname in sfx else speech[f'EN_{fname}']
        yield offset, tags, stream

if __name__ == '__main__':
    import multiprocessing as mp

    mp.freeze_support()

    # TODO: accept file path as first parameter with current directory as default
    res_file = './tenta.cle'
    try:
        with open('dott/monster.tbl', 'r') as monster_table, \
                open('dott/tags.tbl', 'r') as tags_table:
            index = list(read_index(monster_table, tags_table))

        with lpak.open(res_file) as pak:
            with pak.open('audio/iMUSEClient_SFX.fsb', 'rb') as f:
                fsb = fsb5.FSB5(f)
                sfx = {sample.name: sample.data for sample in fsb.samples}
                ext = fsb.get_sample_extension()

            with pak.open('audio/iMUSEClient_VO.fsb', 'rb') as f:
                fsb = fsb5.FSB5(f)
                speech = {sample.name: sample.data for sample in fsb.samples}
                assert fsb.get_sample_extension() == ext
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
    streams = format_streams(read_streams(sfx, speech, index), ext, target_ext)
    build = build_monster(streams, f'monster.{output_ext}', len(index))
    print('Done!')

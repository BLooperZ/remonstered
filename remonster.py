#!/usr/bin/env python

import io
import binascii
import tempfile
import struct
from functools import partial

import fsb5

output_exts = {
    'ogg': 'sog',
    'flac': 'sof',
    'mp3': 'so3'
}

def read_index(monster_table, tags_table):
    for sound, tags in zip(monster_table, tags_table):
        sound, tags = sound[:-1], tags[:-1]
        offset, fname = sound[:8], sound[8:]
        yield binascii.unhexlify(offset.encode()), binascii.unhexlify(tags.encode()), fname

if __name__ == '__main__':

    try:
        with open('monster.tbl', 'r') as monster_table, \
                open('tags.tbl', 'r') as tags_table:
            index = list(read_index(monster_table, tags_table))

        with open('iMUSEClient_SFX.fsb', 'rb') as f:
            fsb = fsb5.FSB5(f.read())
            sfx = {sample.name: sample.data for sample in fsb.samples}
            ext = fsb.get_sample_extension()

        with open('iMUSEClient_VO.fsb', 'rb') as f:
            fsb = fsb5.FSB5(f.read())
            speech = {sample.name: sample.data for sample in fsb.samples}
            assert fsb.get_sample_extension() == ext
    except OSError as e:
        print(f'ERROR: Failed to load file: {e.filename}.')
        print('Please make sure this file is available in current working directory.')
        exit(1)

    output_ext = output_exts[ext]

    with io.BytesIO() as output_idx, \
            tempfile.TemporaryFile() as audio_stream:
        for offset, tags, fname in index:
            output_idx.write(offset)
            output_idx.write(struct.pack('>I', audio_stream.tell()))
            output_idx.write(struct.pack('>I', len(tags)))

            audio_stream.write(tags)
            stream = sfx[fname] if fname in sfx else speech[f'EN_{fname}']
            audio_stream.write(stream)
            output_idx.write(struct.pack('>I', len(stream)))

        with open(f'monster.{output_ext}', 'wb') as output:
            output.write(struct.pack('>I', output_idx.tell()))
            output_idx.seek(0, io.SEEK_SET)
            audio_stream.seek(0, io.SEEK_SET)
            for buffer in iter(partial(output_idx.read, io.DEFAULT_BUFFER_SIZE), b''):
                output.write(buffer)
            for buffer in iter(partial(audio_stream.read, io.DEFAULT_BUFFER_SIZE), b''):
                output.write(buffer)

import sys
import binascii
import os
import json
from contextlib import contextmanager

import click

from . import lpak
from .soundbank import get_soundbanks_view
from .missing import build_missing_entry

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

        # # DEBUG: Uncomment this block to dump audio streams.
        # os.makedirs('VO', exist_ok=True)
        # with open(f'VO/EN_{fname}.mp3', 'wb') as eff:
        #     eff.write(stream)

        yield offset, tags, stream

def resource(base_path, *paths):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if not base_path:
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath('.')

    return os.path.join(base_path, *paths)

def read_tables(path):
    """Read input tables"""
    filemap = resource(path, 'monster.tbl')
    tagmap = resource(path, 'tags.tbl')
    with open(filemap, 'r') as monster_table, \
            open(tagmap, 'r') as tags_table:
        return list(read_index(monster_table, tags_table))

def read_audiomap(path):
    """Read input audio map"""
    mapfile = resource(path, 'stream.json')
    with open(mapfile, 'r') as audiomap:
        return json.load(audiomap)

class FailedToLoadFileError(click.ClickException):
    def show(self):
        print(f'ERROR: Failed to load file: {self.message}.')
        print('Please make sure this file is available in current working directory.')

@contextmanager
def fetch_sources(res_file, index_dir='.'):
    try:
        index = read_tables(index_dir)
        audiomap = read_audiomap(index_dir)
        with lpak.open(res_file) as pak:
            with get_soundbanks_view(pak, audiomap) as stream_view:
                ext, sounds = stream_view
                yield ext, index, read_streams(sounds, index)
    except OSError as e:
        raise FailedToLoadFileError(e.filename)

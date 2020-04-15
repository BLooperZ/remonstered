import builtins
import io
import os
import struct
import operator
from itertools import takewhile
from functools import partial
from contextlib import contextmanager
from typing import NamedTuple
from pathlib import Path

from streamview import PartialStreamView
from utils import copy_stream_buffered

GLOB_ALL = '*'

class LPAKFileEntry(NamedTuple):
    data_offset: int
    name_offset: int
    compressed_size: int
    decompressed_size: int
    is_compressed: int

def read_uint32le(stream):
    val = stream.read(4)
    return struct.unpack('<I', val)[0] if val else None

def read_uint32le_x4(stream):
    return struct.unpack('<4I', stream.read(4 * 4))

def readcstr(stream):
    pos = stream.tell()
    bound_read = iter(partial(stream.read, 1), b'')
    res = b''.join(takewhile(partial(operator.ne, b'\00'), bound_read))
    return (pos, res.decode()) if res else None

def read_filentry(stream):
    val = stream.read(5 * 4)
    return LPAKFileEntry(*struct.unpack('<5I', val)) if val else None

def get_partial_streams(stream, cues):
    pos = stream.tell()
    for offset, size in cues:
        stream.seek(offset, io.SEEK_SET)
        yield offset, PartialStreamView(stream, size)
    stream.seek(pos, io.SEEK_SET)

def read_header(stream):
    tag = stream.read(4)
    assert tag == b'LPAK'[::-1]
    version = read_uint32le(stream)
    cues = list(zip(*[read_uint32le_x4(stream), read_uint32le_x4(stream)]))
    views = list(get_partial_streams(stream, cues))
    return tag, version, views

def build_index(ftable, names):
    # ftable = sorted(ftable, key=operator.attrgetter('name_offset'))
    for (off, name), entry in zip(names, ftable):
        # assert off == entry.name_offset, (off, entry.name_offset)
        # print(off, name, len(name), entry)
        yield os.path.normpath(name), entry

def get_findex(stream, views):
    index, ftable, names, data = views
    assert stream.tell() == index[0]
    index = list(iter(partial(read_uint32le, index[1]), None))
    assert stream.tell() == ftable[0]
    ftable = list(iter(partial(read_filentry, ftable[1]), None))
    assert stream.tell() == names[0]
    names = list(iter(partial(readcstr, names[1]), None))
    assert stream.tell() == data[0]
    findex = dict(build_index(ftable, names))
    return findex, data[1]

class LPakArchive:
    def __init__(self, filename, fileobj=None) -> None:
        self._stream = fileobj if fileobj else builtins.open(filename, 'rb')
        tag, version, views = read_header(self._stream)
        self.index, self._data = get_findex(self._stream, views)

    def __enter__(self):
        return self

    @contextmanager
    def open(self, fname, mode='r'):
        try:
            member = self.index[os.path.normpath(fname)]
        except KeyError:
            raise ValueError(f'no member {fname}')
        self._data.seek(member.data_offset)
        restream = PartialStreamView(self._data, member.decompressed_size)

        if not 'b' in mode:
            restream = io.TextIOWrapper(restream, encoding='utf-8')
        yield restream

    def __exit__(self, type, value, traceback):
        return self._stream.close()

    def iglob(self, pattern):
        return (fname for fname in self.index if Path(fname).match(pattern))

    def listdir(self, path=''):
        path = os.path.join(os.path.normpath(path), '')
        if path == './':
            return list(self.index.keys())
        return [fname for fname in self.index if fname.startswith(path)]

    def __iter__(self):
        for fname, member in self.index.items():
            self._data.seek(member.data_offset)
            yield fname, PartialStreamView(self._data, member.decompressed_size)

    def extractall(self, dirname, pattern=GLOB_ALL):
        for fname, filestream in self:
            if Path(fname).match(pattern):
                sdir = os.path.dirname(fname)
                os.makedirs(os.path.join(dirname, sdir), exist_ok=True)
                with builtins.open(os.path.join(dirname, fname), 'wb') as out_file:
                    for _ in copy_stream_buffered(filestream, out_file):
                        pass

@contextmanager
def open(*args, **kwargs):
    yield LPakArchive(*args, **kwargs) 

if __name__ == '__main__':
    import sys

    if not len(sys.argv) > 1:
        print(f'ERROR: Archive filename not specified.')
        sys.exit(1)

    filename = sys.argv[1]
    pattern = sys.argv[2] if len(sys.argv) > 2 else GLOB_ALL
    print(filename, pattern)
    with open(filename) as lpak:

        if pattern == GLOB_ALL:
            assert set(lpak.iglob(pattern)) == set(fname for fname in lpak.index)

        lpak.extractall('out', pattern)

        # for fname in lpak.glob(pattern):
        #     os.makedirs(os.path.dirname(fname), exist_ok=True)
        #     # base = os.path.basename(fname)
        #     with lpak.open(fname, 'rb') as f:
        #         with builtins.open(fname, 'wb') as o:
        #             o.write(f.read())

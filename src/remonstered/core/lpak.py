import builtins
import io
import os
from struct import Struct
from contextlib import contextmanager
from types import TracebackType
from typing import (
    Any,
    Dict,
    IO,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    cast,
)
from pathlib import Path

from .streamview import PartialStreamView, Stream
from .utils import copy_stream_buffered

GLOB_ALL = '*'

UINT32LE = Struct('<I')
UINT32LE_X4 = Struct('<4I')
FLOAT32LE = Struct('<f')

FILE_ENTRY_1_0 = Struct('<5I')
FILE_ENTRY_1_5 = Struct('<Q4I')


class LPAKFileEntry(NamedTuple):
    data_offset: int
    name_offset: int
    compressed_size: int
    decompressed_size: int
    is_compressed: int


def read_uint32le_x4(stream: IO[bytes]) -> Tuple[int, int, int, int]:
    return UINT32LE_X4.unpack(stream.read(UINT32LE_X4.size))  # type: ignore


def read_float(stream: IO[bytes]) -> float:
    return FLOAT32LE.unpack(stream.read(FLOAT32LE.size))[0]


def read_iter(structure: Struct, stream: IO[bytes]) -> Iterator[Tuple[Any, ...]]:
    return structure.iter_unpack(stream.read())


def get_partial_streams(stream: IO[bytes], cues) -> Iterator[Tuple[int, IO[bytes]]]:
    pos = stream.tell()
    for offset, size in cues:
        stream.seek(offset, io.SEEK_SET)
        yield offset, cast(IO[bytes], PartialStreamView(stream, size))
    stream.seek(pos, io.SEEK_SET)


def get_stream_size(stream: IO[bytes]) -> int:
    pos = stream.tell()
    stream.seek(0, io.SEEK_END)
    size = stream.tell()
    stream.seek(pos, io.SEEK_SET)
    return size


def read_header(
    stream: IO[bytes],
) -> Tuple[bytes, float, List[Tuple[int, IO[bytes]]]]:
    size = get_stream_size(stream)
    tag = stream.read(4)
    assert tag == b'LPAK'[::-1]
    version = read_float(stream)
    if version >= 1.5:
        assert version == 1.5, version
        offs = list(read_uint32le_x4(stream))
        sizes = list(read_uint32le_x4(stream))
        resizes = sizes[1], sizes[0], sizes[2], size - offs[0]
        cues = list(zip(offs, resizes))
        views = list(get_partial_streams(stream, cues))
        return tag, version, views
    assert version == 1.0, version
    cues = list(
        zip(*[read_uint32le_x4(stream), read_uint32le_x4(stream)])  # type: ignore
    )
    views = list(get_partial_streams(stream, cues))
    return tag, version, views


def build_index(ftable: Iterable[LPAKFileEntry], names: Iterable[str]):
    # ftable = sorted(ftable, key=operator.attrgetter('name_offset'))
    # off = 0
    for name, entry in zip(names, ftable):
        # assert off == entry.name_offset, (off, entry.name_offset)
        # print(off, name, len(name), entry)
        yield os.path.normpath(name), entry
        # off += len(name)


def get_findex(
    stream: IO[bytes],
    views: List[Tuple[int, IO[bytes]]],
) -> Tuple[Dict[str, LPAKFileEntry], IO[bytes]]:
    index, ftable, names, data = views
    assert stream.tell() == index[0]
    _ = [val[0] for val in read_iter(UINT32LE, index[1])]
    assert stream.tell() == ftable[0]
    rftable = [LPAKFileEntry(*val) for val in read_iter(FILE_ENTRY_1_0, ftable[1])]
    assert stream.tell() == names[0]
    rnames = [name.decode() for name in names[1].read().split(b'\0')]
    assert stream.tell() == data[0]
    findex = dict(build_index(rftable, rnames))
    return findex, data[1]


def get_findex_v15(
    stream: IO[bytes],
    views: List[Tuple[int, IO[bytes]]],
) -> Tuple[Dict[str, LPAKFileEntry], IO[bytes]]:
    ftable, index, names, data = views
    _ = stream.read(8)
    assert stream.tell() == ftable[0], (stream.tell(), ftable[0])
    rftable = [LPAKFileEntry(*val) for val in read_iter(FILE_ENTRY_1_5, ftable[1])]
    assert stream.tell() == index[0], (stream.tell(), index[0])
    _ = [val[0] for val in read_iter(UINT32LE, index[1])]
    assert stream.tell() == names[0]
    rnames = [name.decode() for name in names[1].read().split(b'\0')]
    assert stream.tell() == data[0]
    findex = dict(build_index(rftable, rnames))
    return findex, data[1]


class LPakArchive:
    def __init__(self, filename: str, fileobj: Optional[IO[bytes]] = None) -> None:
        self._stream = fileobj if fileobj else builtins.open(filename, 'rb')
        tag, version, views = read_header(self._stream)
        read_findex = get_findex if version < 1.5 else get_findex_v15
        self.index, self._data = read_findex(self._stream, views)
        self.path = filename

    def __enter__(self) -> 'LPakArchive':
        return self

    @contextmanager
    def open(self, fname: str, mode: str = 'r') -> Iterator[Stream]:
        try:
            member = self.index[os.path.normpath(fname)]
        except KeyError:
            raise ValueError(f'no member {fname}')
        self._data.seek(member.data_offset)
        restream: Stream = PartialStreamView(self._data, member.decompressed_size)

        if 'b' not in mode:
            restream = cast(IO[bytes], restream)
            restream = io.TextIOWrapper(restream, encoding='utf-8')
        yield restream

    def __exit__(
        self,
        exctype: Optional[Type[BaseException]],
        excinst: Optional[BaseException],
        exctb: Optional[TracebackType],
    ) -> Optional[bool]:
        return self._stream.close()

    def iglob(self, pattern: str) -> Iterator[str]:
        return (fname for fname in self.index if Path(fname).match(pattern))

    def listdir(self, path: str = '') -> List[str]:
        path = os.path.join(os.path.normpath(path), '')
        if path == './':
            return list(self.index.keys())
        return [fname for fname in self.index if fname.startswith(path)]

    def __iter__(self) -> Iterator[Tuple[str, Stream]]:
        for fname, member in self.index.items():
            self._data.seek(member.data_offset)
            yield fname, PartialStreamView(self._data, member.decompressed_size)

    def extractall(self, dirname: str, pattern: str = GLOB_ALL) -> None:
        for fname, filestream in self:
            if Path(fname).match(pattern):
                sdir = os.path.dirname(fname)
                os.makedirs(os.path.join(dirname, sdir), exist_ok=True)
                with builtins.open(os.path.join(dirname, fname), 'wb') as out_file:
                    filestream = cast(IO[bytes], filestream)
                    for _ in copy_stream_buffered(filestream, out_file):
                        pass


@contextmanager
def open(*args, **kwargs) -> Iterator[LPakArchive]:
    yield LPakArchive(*args, **kwargs)


if __name__ == '__main__':
    import sys

    if not len(sys.argv) > 1:
        print('ERROR: Archive filename not specified.')
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

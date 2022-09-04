#!/usr/bin/env python3

import os
import binascii


def read_uint32_be(stream):
    return int.from_bytes(stream.read(4), byteorder='big', signed=False)


SOU_HEADER = b'SOU '
VCTL_HEADER = b'VCTL'
VTTL_HEADER = b'VTTL'
VTLK_HEADER = b'VTLK'


def read_voc_data(stream):
    creative = stream.read(4)

    # FT uses VTLK header, which makes it easier to determine file size
    if creative == VTLK_HEADER:
        max_size = int.from_bytes(stream.read(4), byteorder='big', signed=False)
        return stream.read(max_size - 8)

    stream.seek(-4, os.SEEK_CUR)

    creative = stream.read(8)
    stream.seek(-8, os.SEEK_CUR)
    assert creative == b'Creative', creative

    voc_header = stream.read(27)
    size_bytes = stream.read(3)
    size = int.from_bytes(size_bytes, byteorder='little', signed=False)

    return voc_header + size_bytes + stream.read(size + 1)


def get_next_part(stream):
    loc = stream.tell()

    while not stream.read(4) in (VCTL_HEADER, VTTL_HEADER):
        stream.seek(-3, os.SEEK_CUR)
        loc = stream.tell()

    tags = read_uint32_be(stream)
    assert tags >= 8
    tags -= 8
    skipped = stream.read(tags)

    return loc, read_voc_data(stream), binascii.hexlify(skipped).decode()


def get_parts(stream):
    stream.seek(0, os.SEEK_END)
    end = stream.tell()
    stream.seek(8, os.SEEK_SET)
    while stream.tell() < end:
        yield get_next_part(stream)


def extract_monster(stream, subdir, index):
    tag = stream.read(4)
    if tag != SOU_HEADER:
        raise ValueError(tag)
    assert read_uint32_be(stream) == 0
    os.makedirs(subdir, exist_ok=True)
    for loc, data, skipped in get_parts(stream):
        basename = index.get(loc, f'{loc:08x}.voc')
        fname = os.path.join(subdir, basename).replace('\\', '/')
        with open(fname, 'wb') as out_file:
            out_file.write(data)
        print(f'{loc:08x}{fname}|{skipped}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Process speech resources for SCUMM games.'
    )
    parser.add_argument(
        'filename',
        help='Path to soundbank resource (usually MONSTER.SOU)',
    )
    parser.add_argument(
        '--subdir',
        '-s',
        default='ext',
        required=False,
        help='Sub-directory for extracted voice samples',
    )
    parser.add_argument(
        '--index',
        '-i',
        default=None,
        required=False,
        help='Index for naming voice samples',
    )

    args = parser.parse_args()

    index = {}
    if args.index:
        from .resource import read_tables
        index = {
            int.from_bytes(off, byteorder='big', signed=False): fname
            for off, _, fname in read_tables(args.index)
        }

    with open(args.filename, 'rb') as input_file:
        extract_monster(input_file, args.subdir, index)

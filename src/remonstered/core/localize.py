import io
import struct
import sys
from collections import defaultdict
from typing import IO

from nutcracker.sputm.build import rebuild_resources
from nutcracker.sputm.schema import SCHEMA
from nutcracker.sputm.strings import (
    get_all_scripts,
    get_optable,
    get_script_map,
    update_element_strings,
)
from nutcracker.sputm.tree import narrow_schema, open_game_resource

UINT32BE = struct.Struct('>I')
UINT32LE = struct.Struct('<I')


def read_uint32be(stream: IO[bytes]) -> int:
    return UINT32BE.unpack(stream.read(UINT32BE.size))[0]


def read_uint32le(stream: IO[bytes]) -> int:
    return UINT32LE.unpack(stream.read(UINT32LE.size))[0]


def read_index(stream):
    num = read_uint32le(stream)
    for _ in range(num):
        eid = stream.read(4)

        offs = [(read_uint32le(stream), read_uint32le(stream)) for _ in range(5)]
        yield (eid, offs)


def create_loc_map(stream):
    magic = stream.read(4)
    assert magic == b'LOC '
    size = read_uint32be(stream)
    data = stream.read(size)
    assert stream.read() == b''

    loc_map = defaultdict(list)

    with io.BytesIO(data) as st:
        ind = list(read_index(st))
        for eid, offs in ind:
            entry = []
            for off, ln in offs:
                assert off + 4 == st.tell(), (off, st.tell())
                msg = st.read(ln)
                if ln > 0:
                    assert msg[-1] == 0, msg
                    msg = msg[:-1]
                entry.append(msg)
            assert len(entry) == 5, entry
            # # commented out for duplicate entries with same eid for 'toilet' in DOTT
            # # in spanish, one of them is 'aseo' while other are 'letrina'
            # assert eid not in loc_map, (eid, entry, loc_map[eid])
            loc_map[eid].append(entry)
        assert st.read() == b''

    return loc_map


def dump_loc_map(loc_map, file=sys.stdout):
    for key, val in loc_map.items():
        print(f'{key.hex(" ").upper()}:', file=file)
        for v in val:
            print(f'- {v}', file=file)


langmap = {
    'EN': 0,
    'DE': 1,
    'ES': 2,
    'FR': 3,
    'IT': 4,
}


def translate_game_resource(filename, archive, lang):
    yield 1
    gameres = open_game_resource(filename)
    basename = gameres.basename
    print(f'Extracting strings from game resources: {basename}')

    script_ops = get_optable(gameres.game)
    script_map = get_script_map(gameres.game)

    root = list(gameres.read_resources(
        schema=narrow_schema(
            SCHEMA, {'LECF', 'LFLF', 'RMDA', 'ROOM', 'OBCD', *script_map}
        )
    ))

    with archive.open('localization/ClassicLoc.bin', 'rb') as clf:
        loc_map = create_loc_map(clf)
        useful_loc_map = {val[0][0]: val for _, val in loc_map.items()}

    # dump loc_map
    with open('loc_map.txt', 'w') as f:
        dump_loc_map(loc_map, f)

    strings = []

    for msg in get_all_scripts(root, script_ops, script_map):
        translated = msg
        if msg in useful_loc_map:
            option = 0
            num_options = len(useful_loc_map[msg])
            if num_options > 1:
                print(f'Multiple options found for {msg}: {num_options}')
            # TODO: Figure out which option should be used when multiple options are available
            translated = useful_loc_map[msg][option][langmap[lang]]
        strings.append(translated)

    updated_resource = list(
        update_element_strings(root, strings, script_ops, script_map)
    )

    rebuild_resources(gameres, basename, updated_resource)
    yield 1


def drive_translate_game_resource(filename, archive, lang):
    yield 'Translation', (
        translate_game_resource(filename, archive, lang),
        2,
    )


if __name__ == '__main__':
    with open('localization/ClassicLoc.bin', 'rb') as f:
        loc_map = create_loc_map(f)
        useful_loc_map = {val[0]: val for val in loc_map.values()}

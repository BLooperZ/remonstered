import io
import struct

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


def read_uint32be(stream):
    return UINT32BE.unpack(stream.read(UINT32BE.size))[0]


def read_uint32le(stream):
    return UINT32LE.unpack(stream.read(UINT32LE.size))[0]


def read_index(stream):
    num = read_uint32le(stream)
    for _ in range(num):
        eid = read_uint32le(stream)

        offs = [(read_uint32le(stream), read_uint32le(stream)) for _ in range(5)]
        yield (eid, offs)


def create_loc_map(stream):
    magic = stream.read(4)
    assert magic == b'LOC '
    size = read_uint32be(stream)
    data = stream.read(size)
    assert stream.read() == b''

    loc_map = {}

    with io.BytesIO(data) as st:
        ind = list(read_index(st))
        for eid, offs in ind:
            # # commented out for duplicate entries with same eid for 'toilet' in DOTT
            # # in spanish, one of them is 'aseo' while other are 'letrina'
            # assert eid not in loc_map, eid
            entry = []
            for off, ln in offs:
                assert off + 4 == st.tell(), (off, st.tell())
                msg = st.read(ln)
                if ln > 0:
                    assert msg[-1] == 0, msg
                    msg = msg[:-1]
                entry.append(msg)
            
            loc_map[eid] = entry + loc_map.get(eid, [])

    return loc_map


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
        useful_loc_map = {val[0]: val for _, val in loc_map.items()}

    strings = []

    for msg in get_all_scripts(root, script_ops, script_map):
        translated = msg
        if msg in useful_loc_map:
            translated = useful_loc_map[msg][langmap[lang]]
            if len(useful_loc_map[msg]) > len(langmap):
                useful_loc_map[msg] = useful_loc_map[msg][len(langmap):]
        # translated = useful_loc_map.get(msg, [msg] * len(langmap))[langmap[lang]]
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

import contextlib
from collections import ChainMap
from typing import Iterator, Mapping, Tuple

import fsb5

from .lpak import LPakArchive


@contextlib.contextmanager
def open_soundbank(
    pak: LPakArchive, fname: str, prefix: str = ''
) -> Iterator[fsb5.FSB5]:
    with pak.open(fname, 'rb') as sb:
        yield fsb5.FSB5(sb, prefix=prefix)


@contextlib.contextmanager
def get_soundbanks_view(
    pak: LPakArchive, audiomap: Mapping[str, str]
) -> Iterator[Tuple[str, Mapping[str, bytes]]]:
    with contextlib.ExitStack() as cm:
        banks = [
            cm.enter_context(open_soundbank(pak, fname, prefix=pre))
            for fname, pre in audiomap.items()
        ]
        exts = list(set(sb.get_sample_extension() for sb in banks))
        assert len(exts) == 1
        yield exts[0], ChainMap(*banks)

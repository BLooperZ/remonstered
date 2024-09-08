from collections import ChainMap
from collections.abc import Iterator, Mapping
from contextlib import ExitStack, contextmanager

import fsb5  # type: ignore[import-untyped]

from .lpak import LPakArchive


@contextmanager
def open_soundbank(
    pak: LPakArchive, fname: str, prefix: str = ''
) -> Iterator[fsb5.FSB5]:
    with pak.open(fname, 'rb') as sb:
        yield fsb5.FSB5(sb, prefix=prefix)


@contextmanager
def get_soundbanks_view(
    pak: LPakArchive, audiomap: Mapping[str, str]
) -> Iterator[tuple[str, Mapping[str, bytes]]]:
    with ExitStack() as cm:
        banks = [
            cm.enter_context(open_soundbank(pak, fname, prefix=pre))
            for fname, pre in audiomap.items()
        ]
        exts = list({sb.get_sample_extension() for sb in banks})
        assert len(exts) == 1
        yield exts[0], ChainMap(*banks)

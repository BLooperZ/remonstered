import contextlib
from collections import ChainMap

import fsb5

@contextlib.contextmanager
def open_soundbank(pak, fname, prefix=''):
    with pak.open(fname, 'rb') as sb:
        yield fsb5.FSB5(sb, prefix=prefix)

@contextlib.contextmanager
def get_soundbanks_view(pak, audiomap):
    with contextlib.ExitStack() as cm:
        banks = [
            cm.enter_context(
                open_soundbank(pak, fname, prefix=pre)
            ) for fname, pre in audiomap.items()
        ]
        exts = list(set(sb.get_sample_extension() for sb in banks))
        assert len(exts) == 1
        yield exts[0], ChainMap(*banks)

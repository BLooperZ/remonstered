import itertools
import os
import struct
import subprocess
import sys
import zlib
from typing import List, IO

from nutcracker.compress_san import strip_compress_san

from . import lpak
from .missing import closed_tempfile_name

def extract_ogv_audio(source, dest):
    with closed_tempfile_name(content=source, mode='w+b', suffix='.ogv') as src:
        try:
            p = subprocess.run(
                ['ffmpeg', '-y', '-i', src, '-vn', '-map', '0:1', '-ac', '2', '-b:a', '320k', dest],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except OSError:
            print('ERROR: ffmpeg not available.')
            print('Please make sure ffmpeg binaries can be found in PATH.')
            sys.exit(1)

if __name__ == '__main__':
    import sys
    from pathlib import Path

    if not len(sys.argv) > 1:
        print(f'ERROR: Archive filename not specified.')
        sys.exit(1)

    res_file = sys.argv[1]

    pattern = 'video/*.san'

    with lpak.open(res_file) as pak:
        for fname in pak.iglob(pattern):
            basename = os.path.basename(fname)
            simplename, ext = os.path.splitext(basename)

            with pak.open(fname, 'rb') as res:
                data = strip_compress_san(res)
            directory = os.path.join('out', os.path.basename(os.path.dirname(fname)))
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, basename), 'wb') as out:
                out.write(data)

            for videohd in pak.iglob(os.path.join('videohd', f'{simplename}.ogv')):

                with pak.open(videohd, 'rb') as vid:
                    stream = vid.read()
                extract_ogv_audio(
                    stream,
                    os.path.join(directory, f'{simplename}.ogg')
                )

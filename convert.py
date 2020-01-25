import io
import sys
import warnings
import concurrent.futures
from functools import partial

import click

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pydub

def convert_sound(src_ext, target_ext, snd_data):
    if src_ext == target_ext:
        return snd_data
    with io.BytesIO(snd_data) as in_snd:
        snd = pydub.AudioSegment.from_file(in_snd, format=src_ext)
    with io.BytesIO() as out_snd:
        snd.export(out_snd, format=target_ext)
        return out_snd.getvalue()

def convert_streams(streams, src_ext, target_ext):
    offs, tags_info, sounds = zip(*streams)
    convert = partial(convert_sound, src_ext, target_ext)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        try:
            converted = executor.map(convert, sounds)
            for offset, tags, sound in zip(offs, tags_info, converted):
                yield offset, tags, sound
        except KeyboardInterrupt as kbi:
            executor.shutdown(wait=False)
            raise kbi

class LibraryFFMPEGNotAvailableError(click.ClickException):
    def show(self):
        print('ERROR: ffmpeg not available.')
        print('To convert audio, please make sure ffmpeg binaries can be found in PATH.')

def test_converter(target_ext):
    try:
        with io.BytesIO() as stream:
            pydub.AudioSegment.empty().export(stream, format=target_ext)
    except OSError:
        raise LibraryFFMPEGNotAvailableError('ffmpeg')

def format_streams(streams, src_ext, target_ext):
    if src_ext == target_ext:
        return streams
    test_converter(target_ext)
    return convert_streams(streams, src_ext, target_ext)

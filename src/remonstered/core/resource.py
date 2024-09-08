import binascii
import json
import os
import sys
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from typing import IO, Any

import click

from . import lpak
from .missing import build_missing_entry
from .soundbank import get_soundbanks_view


def read_hex(hexstr: str) -> bytes:
    return binascii.unhexlify(hexstr.encode())


def read_index(
    monster_table: Iterable[str], tags_table: Iterable[str]
) -> Iterator[tuple[bytes, bytes, str]]:
    for sound, tags in zip(monster_table, tags_table, strict=True):
        sound, tags = sound[:-1], tags[:-1]
        offset, fname = sound[:8], sound[8:]
        yield read_hex(offset), read_hex(tags), fname


def read_streams(
    sounds: Mapping[str, bytes],
    index: Iterable[tuple[bytes, bytes, str]],
) -> Iterator[tuple[bytes, bytes, bytes]]:
    for offset, tags, fname in index:
        stream = sounds.get(fname, None)
        if not stream:
            stream = build_missing_entry(sounds, fname)
        assert stream is not None, fname

        # # DEBUG: Uncomment this block to dump audio streams.
        # os.makedirs('VO', exist_ok=True)
        # with open(f'VO/EN_{fname}.mp3', 'wb') as eff:
        #     eff.write(stream)

        yield offset, tags, stream


def resource(base_path: str | None, *paths: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if not base_path:
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS  # type: ignore[attr-defined]  # noqa: SLF001
        except AttributeError:
            base_path = os.path.abspath('.')

    assert base_path is not None
    return os.path.join(base_path, *paths)


def read_tables(path: str | None) -> list[tuple[bytes, bytes, str]]:
    """Read input tables"""
    filemap = resource(path, 'monster.tbl')
    tagmap = resource(path, 'tags.tbl')
    with open(filemap, 'r') as monster_table, open(tagmap, 'r') as tags_table:
        return list(read_index(monster_table, tags_table))


def read_audiomap(path: str | None) -> dict[str, str]:
    """Read input audio map"""
    mapfile = resource(path, 'stream.json')
    with open(mapfile, 'r') as audiomap:
        return dict(json.load(audiomap))


def read_extractmap(path: str | None) -> dict[str, str]:
    """Read files to extract"""
    mapfile = resource(path, 'extract.json')
    with open(mapfile, 'r') as extractmap:
        return dict(json.load(extractmap))


class FailedToLoadFileError(click.ClickException):
    def show(self, file: IO[Any] | None = None) -> None:
        click.echo(f'ERROR: Failed to load file: {self.message}.')
        click.echo(
            'Please make sure this file is available in current working directory.',
        )


@contextmanager
def fetch_sources(
    archive: lpak.LPakArchive,
    index_dir: str | None = '.',
) -> Iterator[
    tuple[str, list[tuple[bytes, bytes, str]], Iterator[tuple[bytes, bytes, bytes]]]
]:
    try:
        index = read_tables(index_dir)
        audiomap = read_audiomap(index_dir)
        with get_soundbanks_view(archive, audiomap) as stream_view:
            ext, sounds = stream_view
            yield ext, index, read_streams(sounds, index)
    except OSError as e:
        raise FailedToLoadFileError(e.filename) from e

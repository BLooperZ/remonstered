import itertools

import click

from remonstered.core import lpak
from remonstered.core.audio import output_exts
from remonstered.core.extract import extract
from remonstered.core.remonster import remonster
from remonstered.core.utils import drive_progress


@click.command()
@click.argument('filename', metavar='<filename>', required=False, default='./tenta.cle')
@click.option(
    '--format',
    '-f',
    'audio_format',
    type=str,
    metavar=f"[{'|'.join(output_exts)}]",
    default=None,
    help='Output audio format',
)
@click.option(
    '--index',
    '-i',
    'index_dir',
    type=click.Path(),
    metavar='<path>',
    default=None,
    help='Path to directory with .tbl files',
)
@click.help_option('-h', '--help')
def main(filename, index_dir, audio_format):
    with lpak.open(filename) as archive:
        prog = itertools.chain(
            remonster(archive, index_dir, audio_format),
            extract(archive, index_dir),
        )
        for action, (task, total) in prog:
            print(action)
            drive_progress(task, total=total)
    print('Done!')


if __name__ == '__main__':
    import multiprocessing as mp

    mp.freeze_support()

    main()

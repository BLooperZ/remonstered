from typing import IO, Any

import click

output_exts = {
    'ogg': 'sog',
    'flac': 'sof',
    'mp3': 'so3',
}


class UnsupportedAudioFormatError(click.ClickException):
    def show(self, file: IO[Any] | None = None) -> None:
        available = '|'.join(output_exts)
        click.echo(f'ERROR: Unsupported audio format: {self.message}.')
        click.echo(f'Available options are [{available}].')


def get_output_extension(target_ext: str) -> str:
    try:
        return output_exts[target_ext]
    except KeyError as ke:
        raise UnsupportedAudioFormatError(target_ext) from ke

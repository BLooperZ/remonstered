import click

output_exts = {
    'ogg': 'sog',
    'flac': 'sof',
    'mp3': 'so3',
}


class UnsupportedAudioFormatError(click.ClickException):
    def show(self):
        available = '|'.join(output_exts)
        print(f'ERROR: Unsupported audio format: {self.message}.')
        print(f'Available options are [{available}].')


def get_output_extension(target_ext: str) -> str:
    try:
        return output_exts[target_ext]
    except KeyError:
        raise UnsupportedAudioFormatError(target_ext)

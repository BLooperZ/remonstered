import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from typing import IO, Any, AnyStr, override

import click


class LibraryFFMPEGNotAvailableError(click.ClickException):
    @override
    def show(self, file: IO[Any] | None = None) -> None:
        click.echo('ERROR: ffmpeg not available.')
        click.echo('Please make sure ffmpeg binaries can be found in PATH.')
        sys.exit(1)


@contextmanager
def closed_tempfile_name(
    content: AnyStr | None = None,
    *args: Any,
    **kwargs: Any,
) -> Iterator[pathlib.Path]:
    with tempfile.NamedTemporaryFile(  # type: ignore[call-overload]
        *args, **kwargs, delete=False
    ) as tmp:
        try:
            if content:
                tmp.write(content)
            tmp.close()
            path = pathlib.Path(tmp.name)
            yield path
        finally:
            path.unlink(missing_ok=True)


def ffmpeg_run(
    src: str | os.PathLike[str],
    dst: str | os.PathLike[str],
    args: list[str],
) -> None:
    try:
        _ = subprocess.run(  # noqa: S603, UP022
            [  # noqa: S607
                'ffmpeg',
                '-y',
                '-i',
                str(src),
                *args,
                str(dst),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as ose:
        raise LibraryFFMPEGNotAvailableError('ffmpeg') from ose

import io
import functools
from typing import Any, Callable, IO, Iterator

from tqdm import tqdm

print_progress = functools.partial(
    tqdm,
    ascii='->>=',
    bar_format='[{bar:50}] Completed: {percentage:0.2f}%',
)


def drive_progress(it: Iterator[Any], *args: Any, **kwargs: Any) -> None:
    with print_progress(it, *args, **kwargs) as pbar:
        for dp in it:
            pbar.update(dp)


def consume(it: Iterator[Any], *args: Any, **kwargs: Any) -> None:
    for _ in it:
        pass


def buffered(
    source: Callable[[int], bytes], buffer_size: int = io.DEFAULT_BUFFER_SIZE
) -> Iterator[bytes]:
    return iter(functools.partial(source, buffer_size), b'')


def copy_stream_buffered(in_stream: IO[bytes], out_stream: IO[bytes]) -> Iterator[int]:
    for buffer in buffered(in_stream.read):
        out_stream.write(buffer)
        yield len(buffer)


def iterate(it: Iterator[Any]) -> Iterator[int]:
    return (1 for _ in it)

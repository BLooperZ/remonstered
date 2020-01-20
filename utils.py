import io
import functools

from tqdm import tqdm

print_progress = functools.partial(
    tqdm,
    ascii=f'->>=',
    bar_format='[{bar:50}] Completed: {percentage:0.2f}%'
)

def drive_progress(it, *args, **kwargs):
    with print_progress(it, *args, **kwargs) as pbar:
        for dp in it:
            pbar.update(dp)

def copy_stream_buffered(in_stream, out_stream):
    for buffer in iter(functools.partial(in_stream.read, io.DEFAULT_BUFFER_SIZE), b''):
        out_stream.write(buffer)
        yield len(buffer)

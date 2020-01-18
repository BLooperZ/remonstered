import io
import functools

def print_progress(total, iterable, size=50):
    init = '-' * (size - 1)
    print(f'\r|>{init}| Completed: {0:0.2f}%', end='\r')
    for idx, _ in enumerate(iterable):
        if total:
            prefix = '=' * ((idx * size) // total)
            suffix = '-' * (((total - idx - 1) * size) // total)
            completed = (idx + 1) / total
            print(f'\r|{prefix}>{suffix}| Completed: {100 * completed:0.2f}%', end='\r')
    print()

def copy_stream_buffered(in_stream, out_stream):
    for buffer in iter(functools.partial(in_stream.read, io.DEFAULT_BUFFER_SIZE), b''):
        out_stream.write(buffer)
        yield len(buffer)

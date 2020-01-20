import io
import functools

def copy_stream_buffered(in_stream, out_stream):
    for buffer in iter(functools.partial(in_stream.read, io.DEFAULT_BUFFER_SIZE), b''):
        out_stream.write(buffer)
        yield len(buffer)

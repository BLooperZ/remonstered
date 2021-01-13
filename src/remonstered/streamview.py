import io

class PartialStreamView:
    def __init__(self, stream, size):
        self._stream = stream
        self._start = stream.tell()
        self._size = size
        self._pos = 0

    def seek(self, pos, whence=io.SEEK_SET):
        if whence == io.SEEK_CUR:
            pos += self._pos
        elif whence == io.SEEK_END:
            pos += self._size
        self._pos = pos

    def tell(self):
        return self._pos
    
    def read(self, size=None):
        self._stream.seek(self._start + self._pos, io.SEEK_SET)
        if size is not None and size >= 0:
            size = min(self._size - self._pos, size)
        else:
            size = self._size - self._pos
        res = self._stream.read(size)
        self._pos += len(res)
        return res

#!/usr/bin/env python

class Buffer(object):
    """Read data from a filelike object without blocking
    """
    def __init__(self, filelike):
        self.filelike = filelike
        self._data = ''

    def doRead(self):
        """Called when data are available for reading

        To avoid blocking, read() will only be called once on the underlying
        filelike object.
        """
        self._data += self.filelike.read()

    def append(self, newdata):
        """Append additional data to the buffer
        """
        self._data += newdata

    def readline(self):
        """Read a complete line from the buffer

        Only complete lines are returned.  If no data are available, or if
        there is no newline character, None will be returned, and any
        remaining data will remain in the buffer.
        """
        data = self._data
        pos = data.find('\n')
        if pos is not -1:
            line = data[0:pos+1]
            self._data = data[pos+1:]
            return line
        else:
            return None


# vim: et sw=4 sts=4
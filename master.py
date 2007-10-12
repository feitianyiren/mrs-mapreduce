#!/usr/bin/env python

# TODO: Switch to using "with" for locks when we stop supporting pre-2.5.
# from __future__ import with_statement

import threading

class Slave(object):
    def __init__(self, host, port, cookie):
        self.host = host
        self.port = port
        self.cookie = cookie

class Slaves(object):
    def __init__(self):
        self._slaves = []
        self._idle_slaves = []

        self._lock = threading.Lock()
        self._idle_sem = threading.Semaphore()

    def add_slave(self, slave):
        self._lock.acquire()
        self._slaves.append(slave)
        self._idle_slaves.append(slave)
        self._lock.release()

    del remove_slave(self, slave):
        """Remove a slave, whether it is busy or idle.

        Presumably, the slave has stopped responding.
        """
        self._lock.acquire()
        if slave in self._idle_slaves:
            # Note that we don't decrement the semaphore.  Tough luck for the
            # sap that thinks the list has more entries than it does.
            self._idle_slaves.remove(slave)
        self._slaves.remove(slave)
        self._lock.release()

    def push_idle(self, slave):
        """Set a slave as idle.
        """
        self._lock.acquire()
        if slave not in self._slaves:
            self._lock.release()
            raise RuntimeError("Slave does not exist!")
        if slave not in self._idle_slaves:
            self._idle_slaves.append(slave)
        self._idle_sem.release()
        self._lock.release()

    def pop_idle(self, blocking=False):
        """Request an idle slave, setting it as busy.

        Return None if all slaves are busy.  Block if requested with the
        blocking parameter.  If you set blocking, we will never return None.
        """
        idler = None
        while blocking and idler is None:
            if self._idle_sem.acquire(blocking):
                self._lock.acquire()
                try:
                    idler = self._idle_slaves.pop()
                except IndexError:
                    # This can happen if remove_slave was called.  So sad.
                    pass
                self._lock.release()
        return idler


class MasterRPC(object):
    def __init__(self):
        self.slaves = Slaves()

    def _listMethods(self):
        import SimpleXMLRPCServer
        return SimpleXMLRPCServer.list_public_methods(self)

    def signin(self, cookie, slave_port, host=None, port=None):
        """Slave reporting for duty.
        """
        slave = Slave(host, slave_port, cookie)
        self.slaves.add_slave(slave)
        return True

    def done(self, cookie, host=None, port=None):
        """Slave is done with whatever it was working on.
        """
        pass

    def ping(self):
        """Slave checking if we're still here.
        """
        return True


if __name__ == '__main__':
    # Testing standalone server.
    import rpc
    instance = MasterRPC()
    PORT = 8000
    #PORT = 0
    server = rpc.new_server(instance, host='127.0.0.1', port=PORT)
    server.serve_forever()


# vim: et sw=4 sts=4
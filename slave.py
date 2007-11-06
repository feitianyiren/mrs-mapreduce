#!/usr/bin/env python

# TODO: if the cookie check fails too many times, we may want to alert the
# user somehow.

COOKIE_LEN = 8
SLAVE_PING_INTERVAL = 5.0

import threading, xmlrpclib

class SlaveInterface(object):
    """Public XML-RPC Interface
    
    Note that any method not beginning with an underscore will be exposed to
    remote hosts.
    """
    def __init__(self, slave):
        self.slave = slave

    def _listMethods(self):
        return SimpleXMLRPCServer.list_public_methods(self)

    def start_map(self, map_name, part_name, taskid, inputs, output,
            reduce_tasks, cookie, **kwds):
        self.slave.check_cookie(cookie)
        return self.slave.worker.start_map(map_name, part_name, taskid,
                inputs, output, reduce_tasks)

    def start_reduce(self, func_name, taskid, inputs, output, cookie, **kwds):
        self.slave.check_cookie(cookie)
        return self.slave.worker.start_reduce(func_name, taskid, inputs,
                output)

    def quit(self, cookie, **kwds):
        self.slave.check_cookie(cookie)
        self.slave.alive = False
        import sys
        print >>sys.stderr, "Quitting as requested by an RPC call."
        return True

    def ping(self, **kwds):
        """Master checking if we're still here.
        """
        return True


class CookieValidationError(Exception):
    pass


def run_slave(mrs_prog, uri, options):
    """Mrs Slave

    The uri is of the form scheme://username:password@host/target with
    username and password possibly omitted.
    """
    import xmlrpclib

    # Create an RPC proxy to the master's RPC Server
    master = xmlrpclib.ServerProxy(uri)
    slave = Slave(master, mrs_prog, options.port)

    slave.run()
    return 0


class Slave(object):
    def __init__(self, master, mrs_prog, port):
        import rpc

        self.alive = True
        self.cookie = self.rand_cookie()
        self.master = master
        self.mrs_prog = mrs_prog
        self.port = port

        # Create a worker thread.  This thread will die when we do.
        self.worker = Worker(self, master)

        # Create a slave RPC Server
        self.interface = SlaveInterface(self)
        self.server = rpc.new_server(self.interface, port)

        self.host, self.port = self.server.socket.getsockname()

        # Register with master.
        self.id = self.master.signin(self.cookie, self.port,
                mrs_prog.main_hash, mrs_prog.registry.reg_hash())
        if self.id < 0:
            import sys
            print >>sys.stderr, "Master rejected signin."
            raise RuntimeError

    @classmethod
    def rand_cookie(cls):
        # Generate a cookie so that mostly only authorized people can connect.
        from random import choice
        import string
        possible = string.letters + string.digits
        return ''.join(choice(possible) for i in xrange(COOKIE_LEN))

    def check_cookie(self, cookie):
        if cookie != self.cookie:
            raise CookieValidationError

    def handle_request(self):
        """Try to handle a request on the RPC connection.

        Timeout after SLAVE_PING_INTERVAL seconds.
        """
        import select
        server_fd = self.server.fileno()
        rlist, wlist, xlist = select.select([server_fd], [], [],
                SLAVE_PING_INTERVAL)
        if server_fd in rlist:
            self.server.handle_request()
            return True
        else:
            return False

    def run(self):
        # Spin off the worker thread.
        self.worker.start()

        # Report for duty.
        self.master.ready(self.id, self.cookie)

        # Handle requests on the RPC server.
        while self.alive:
            if not self.handle_request():
                # TODO: limit the sorts of exceptions that get caught:
                try:
                    master_alive = self.master.ping()
                except:
                    master_alive = False
                if not master_alive:
                    import sys
                    print >>sys.stderr, "Master failed to respond to ping."
                    return -1


class Worker(threading.Thread):
    """Execute map tasks and reduce tasks.

    The worker waits for other threads to make assignments by calling
    start_map and start_reduce.
    """
    def __init__(self, slave, master, **kwds):
        threading.Thread.__init__(self, **kwds)
        # Die when all other non-daemon threads have exited:
        self.setDaemon(True)

        self.slave = slave
        self.master = master

        # TODO: Should we have a queue of work to be done rather than
        # to just store a single item?
        self._task = None
        self._cond = threading.Condition()
        self.active = False
        self.exception = None

    def start_map(self, map_name, part_name, taskid, inputs, output,
            reduce_tasks):
        """Tell this worker to start working on a map task.

        This will ordinarily be called from some other thread.
        """
        from mapreduce import MapTask
        success = False
        self._cond.acquire()
        if self._task is None:
            self._task = MapTask(taskid, self.slave.mrs_prog, map_name,
                    part_name, output, reduce_tasks)
            self._task.inputs = inputs
            success = True
            self._cond.notify()
        self._cond.release()
        return success

    def start_reduce(self, reduce_name, taskid, inputs, output):
        """Tell this worker to start working on a reduce task.

        This will ordinarily be called from some other thread.
        """
        from mapreduce import ReduceTask
        success = False
        self._cond.acquire()
        if self._task is None:
            self._task = ReduceTask(taskid, self.slave.mrs_prog, reduce_name,
                    output)
            self._task.inputs = inputs
            success = True
            self._cond.notify()
        self._cond.release()
        return success

    def run(self):
        """Run the worker thread."""
        while True:
            self._cond.acquire()
            while self._task is None:
                self._cond.wait()
            task = self._task
            self._cond.release()

            task.run()
            files = task.output.filenames()

            self._cond.acquire()
            self._task = None
            self._cond.release()

            self.master.done(self.slave.id, files, self.slave.cookie)


# vim: et sw=4 sts=4

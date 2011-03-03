# Mrs
# Copyright 2008-2010 Brigham Young University
#
# This file is part of Mrs.
#
# Mrs is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Mrs is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# Mrs.  If not, see <http://www.gnu.org/licenses/>.
#
# Inquiries regarding any further use of Mrs, please contact the Copyright
# Licensing Office, Brigham Young University, 3760 HBLL, Provo, UT 84602,
# (801) 422-9339 or 422-3821, e-mail copyright@byu.edu.

"""Mrs. RPC

RPC mechanisms built on Python's xmlrpc library.
"""

import httplib
import SimpleXMLRPCServer
import socket
import sys
import xmlrpclib

import logging
logger = logging.getLogger('mrs')

# TODO: switch parent class to xmlrpclib.SafeTransport
# TODO: consider using the Transport's enable_threshold setting for gzip
class TimeoutTransport(xmlrpclib.Transport):
    """XMLRPC Transport monkeypatched to accept a timeout parameter."""
    def __init__(self, timeout):
        xmlrpclib.Transport.__init__(self)
        self.timeout = timeout

    # Variant of the basic make_connection that adds a timeout param to
    # HTTPConnection.
    def make_connection(self, host):
        #return an existing connection if possible.  This allows
        #HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            return self._connection[1]

        # create a HTTP connection object from a host descriptor
        chost, self._extra_headers, x509 = self.get_host_info(host)
        #store the host argument along with the connection object
        if self.timeout:
            self._connection = host, httplib.HTTPConnection(chost,
                    timeout=self.timeout)
        else:
            self._connection = host, httplib.HTTPConnection(chost)
        return self._connection[1]

    # Python 2.6 has an old implementation of Transport that doesn't play well
    # with the above function.  Fall back on an alternate version if needed.
    if sys.version_info[0] == 2 and sys.version_info[1] < 7:
        def make_connection(self, host):
            prev = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.timeout)
            value = xmlrpclib.Transport.make_connection(self, host)
            socket.setdefaulttimeout(prev)
            return value


class ServerProxy(xmlrpclib.ServerProxy):
    def __init__(self, uri, timeout):
        transport = TimeoutTransport(timeout)
        uri = rpc_url(uri)
        xmlrpclib.ServerProxy.__init__(self, uri, transport=transport)


class RequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    """Simple HTTP request handler
    """
    # The sequence of calls is a bit counter-intuitive.  The do_POST method in
    # SimpleXMLRPCRequestHandler calls the server's _marshaled_dispatch
    # method, passing it a reference to its own _dispatch method.  This
    # _dispatch method, overridden here, calls the server's _dispatch method
    # with extra information about the connection.  The reason this is
    # necessary is that the request handler knows about the connection, but
    # the server does not.

    def _dispatch(self, method, params):
        host, _ = self.client_address
        return self.server._dispatch(method, params, host)


class Server(SimpleXMLRPCServer.SimpleXMLRPCServer):
    """XMLRPC Server that supports passing the client host to the method.

    This server takes an instance used for dispatching requests; methods of
    the instance beginning with 'xmlrpc_' are called.  If the uses_host
    attribute is set on the method, then the host is passed as a keyword
    argument.
    """
    def __init__(self, addr, instance):
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, addr,
                requestHandler=RequestHandler, logRequests=False)
        self.instance = instance

    def _dispatch(self, method, params, host):
        try:
            func = getattr(self.instance, 'xmlrpc_' + method)
        except AttribuetError:
            raise RuntimeError('method "%s" is not supported' % method)

        try:
            if hasattr(func, 'uses_host'):
                return func(*params, host=host)
            else:
                return func(*params)
        except Exception, e:
            import traceback
            msg = 'Exception in RPC Server: %s' % e
            logger.critical(msg)
            tb = traceback.format_exc()
            msg = 'Traceback: %s' % tb
            logger.error(msg)
            raise


def uses_host(f):
    """Decorate f with the attribute `uses_host`.

    When XMLRPC renders the given XML RPC method, it will pass the host
    as a named argument.
    """
    f.uses_host = True
    return f


def rpc_url(urlstring):
    """Tidy a URL to be used to connect to an XML RPC server.

    >>> rpc_url('http://localhost')
    'http://localhost/RPC2'
    >>> rpc_url('http://localhost/')
    'http://localhost/RPC2'
    >>> rpc_url('http://localhost/path/to/xmlrpc')
    'http://localhost/path/to/xmlrpc'
    >>> rpc_url('localhost/path/to/xmlrpc')
    'http://localhost/path/to/xmlrpc'
    >>>
    """
    from urlparse import urlsplit, urlunsplit

    if '://' not in urlstring:
        urlstring = 'http://' + urlstring

    scheme, netloc, path, query, fragment = urlsplit(urlstring)
    if not path and not query and not fragment:
        path = '/RPC2'
    return urlunsplit((scheme, netloc, path, query, fragment))

# vim: et sw=4 sts=4
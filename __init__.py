#!/usr/bin/env python
# TODO: fix the sample code in the following docstring:
"""MapReduce: a simple implementation (Mrs)

Your Mrs MapReduce program might look something like this:

def mapper(key, value):
    yield newkey, newvalue

def reducer(key, values):
    yield newvalue

if __name__ == '__main__':
    import mrs
    mrs.main(mapper, reducer)
"""

__all__ = ['VERSION', 'main', 'option_parser', 'Registry', 'TextWriter',
        'HexWriter']

from version import VERSION
from registry import Registry
from io import TextWriter, HexWriter

USAGE = (""
"""%prog [OPTIONS] [ARGS]

Mrs Version """ + VERSION)

def main(registry, run=None, parser=None):
    """Run a MapReduce program.

    Requires a run function and a Registry.  If you want to, you can pass in
    an OptionParser instance called parser with your own custom options.  If
    you want to modify the basic Mrs Parser, call mrs.option_parser().
    """
    if parser is None:
        parser = option_parser()
    (options, args) = parser.parse_args()

    if options.mrs_impl is None:
        parser.error("Mrs Implementation must be specified.")

    if run is None:
        import mapreduce
        run = mapreduce.mrs_simple

    if options.mrs_impl == 'master':
        from parallel import run_master
        impl_function = run_master
    elif options.mrs_impl == 'slave':
        from slave import run_slave
        impl_function = run_slave
    elif options.mrs_impl == 'mockparallel':
        from serial import run_mockparallel
        impl_function = run_mockparallel
    elif options.mrs_impl == 'serial':
        from serial import run_serial
        impl_function = run_serial
    else:
        parser.error("Invalid Mrs Implementation: %s" % options.mrs_impl)

    try:
        retcode = impl_function(registry, run, args, options)
    except KeyboardInterrupt:
        import sys
        print >>sys.stderr, "Interrupted."
        retcode = -1
    return retcode

def option_parser():
    """Create the default Mrs Parser

    The parser is an optparse.OptionParser.  It is configured to use the
    resolve conflict_handler, so any option can be overridden simply by
    defining a new option with the same option string.  The remove_option and
    get_option methods still work, too.  Note that overriding an option only
    shadows it while still allowing its other option strings to work, but
    remove_option completely removes the option with all of its option
    strings.

    The usage string can be specified with set_usage, thus overriding the
    default.  However, often what you really want to set is the epilog.  The
    usage shows up in the help before the option list; the epilog appears
    after.
    """
    import os, optparse

    parser = optparse.OptionParser(conflict_handler='resolve')
    parser.usage = USAGE

    parser.add_option('-I', '--mrs-impl', dest='mrs_impl',
            help='Mrs Implementation')
    parser.add_option('-M', '--mrs-master', dest='mrs_master',
            help='URL of the Master RPC server (slave only)')
    parser.add_option('-P', '--mrs-port', dest='mrs_port', type='int',
            help='RPC Port for incoming requests')
    parser.add_option('-S', '--mrs-shared', dest='mrs_shared',
            help='Shared area for temporary storage (parallel only)')
    parser.add_option('-R', '--mrs-reduce-tasks', dest='mrs_reduce_tasks',
            type='int', help='Default number of reduce tasks (parallel only)')

    parser.set_defaults(mrs_reduce_tasks=1, mrs_port=0,
            mrs_shared=os.getcwd())

    return parser


# vim: et sw=4 sts=4

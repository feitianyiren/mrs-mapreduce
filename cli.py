# Mrs
# Copyright 2008 Brigham Young University
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
# Inquiries regarding any further use of the Materials contained on this site,
# please contact the Copyright Licensing Office, Brigham Young University,
# 3760 HBLL, Provo, UT 84602, (801) 422-9339 or 422-3821, e-mail
# copyright@byu.edu.

from version import VERSION

USAGE = (""
"""%prog IMPLEMENTATION [OPTIONS] [ARGS]

Mrs Version """ + VERSION + """

The subcommand IMPLEMENTATION must be the first argument and can be "master",
"slave", "serial", or "mock_parallel".  Note that you can give --help
separately for each subcommand."""
)

import logging
logger = logging.getLogger('mrs')


def main(registry, run=None, setup=None, update_parser=None):
    """Run a MapReduce program.

    Requires a run function and a Registry.
    
    If setup is provided, it will be called before performing any work, and
    all command-line options will be passed in.
    
    If you want to modify the basic Mrs Parser, provide an update_parser
    function that takes a parser and either modifies it or returns a new one.
    The parser will be given all options/arguments except the Mrs
    Implementation.  Note that no option should ever have the value None.
    """
    parser = option_parser()
    import sys
    if len(sys.argv) < 2:
        parser.error("Mrs Implementation must be specified.")

    mrs_impl = sys.argv[1]

    if run is None:
        from run import mrs_simple
        run = mrs_simple

    if mrs_impl in ('-h', '--help'):
        # It's not a Mrs Implementation, but try to help anyway.
        parser.print_help()
        sys.exit(2)
    elif mrs_impl == 'master':
        from master import master_main
        main_function = master_main
        add_parallel_options(parser)
        add_network_options(parser)
        if update_parser:
            parser = update_parser(parser)
    elif mrs_impl == 'slave':
        from slave import slave_main
        main_function = slave_main
        add_slave_options(parser)
        add_network_options(parser)
    elif mrs_impl == 'mockparallel':
        from serial import mockparallel_main
        main_function = mockparallel_main
        add_parallel_options(parser)
        if update_parser:
            parser = update_parser(parser)
    elif mrs_impl == 'serial':
        from serial import serial_main
        main_function = serial_main
        if update_parser:
            parser = update_parser(parser)
    else:
        parser.error("Invalid Mrs Implementation: %s" % mrs_impl)

    (opts, args) = parser.parse_args(sys.argv[2:])

    if opts.mrs_debug:
        logger.setLevel(logging.DEBUG)
    elif opts.mrs_verbose:
        logger.setLevel(logging.INFO)

    try:
        main_function(registry, run, setup, args, opts)
        sys.exit(0)
    except KeyboardInterrupt:
        import sys
        logger.critical('Quitting due to keyboard interrupt.')
        print >>sys.stderr, "Interrupted."
        sys.exit(1)


def primary_impl(impl):
    """Report whether the given implementation is a "main" one or a slave."""

    return impl in ('master', 'mockparallel', 'serial')


def option_parser():
    """Create the default Mrs Parser

    The parser is a param.OptionParser.  It is configured to use the
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
    import param

    parser = param.OptionParser(conflict_handler='resolve')
    parser.usage = USAGE
    parser.add_option('-v', '--mrs-verbose', dest='mrs_verbose',
            action='store_true', help='Verbose mode (set log level to INFO)')
    parser.add_option('-d', '--mrs-debug', dest='mrs_debug',
            action='store_true', help='Debug mode (set log level to DEBUG)')

    return parser


def add_network_options(parser):
    parser.add_option('-P', '--mrs-port', dest='mrs_port', type='int',
            help='RPC Port for incoming requests')
    parser.add_option('-T', '--mrs-timeout', dest='mrs_timeout', type='float',
            help='Timeout for RPC calls (including pings)')
    parser.add_option('--mrs-pingdelay', dest='mrs_pingdelay', type='float',
            help='Interval between pings')
    parser.set_defaults(mrs_port=0, mrs_timeout=20.0, mrs_pingdelay=5.0)


def add_parallel_options(parser):
    import os
    default_shared = os.getcwd()
    parser.add_option('-S', '--mrs-shared', dest='mrs_shared',
            help='Shared area for temporary storage')
    parser.add_option('--mrs-keep-jobdir', dest='mrs_keep_jobdir',
            action='store_true', help="Do not delete jobdir at completion")
    parser.add_option('-R', '--mrs-reduce-tasks', dest='mrs_reduce_tasks',
            type='int', help='Default number of reduce tasks')
    parser.add_option('--mrs-runfile', dest='mrs_runfile',
            help="Server's RPC port will be written here")
    parser.set_defaults(mrs_reduce_tasks=1, mrs_shared=default_shared)


def add_slave_options(parser):
    parser.add_option('-M', '--mrs-master', dest='mrs_master',
            help='URL of the Master RPC server (slave only)')


# vim: et sw=4 sts=4

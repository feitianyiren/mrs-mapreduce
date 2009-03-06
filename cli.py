# Mrs
# Copyright 2008-2009 Brigham Young University
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

from version import VERSION

USAGE = (""
"""%prog [OPTIONS] [ARGS]

Mrs Version """ + VERSION + """

The default implementation is Serial.  Note that you can give --help
separately for each implementation."""
)

import logging
import sys
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
    import param

    parser = option_parser()
    if update_parser:
        parser = update_parser(parser)
    opts, args = parser.parse_args()

    mrs_impl = param.instantiate(opts, 'mrs')
    mrs_impl.run = run
    mrs_impl.setup = setup
    mrs_impl.registry = registry

    try:
        mrs_impl.main(args, opts)
        sys.exit(0)
    except KeyboardInterrupt:
        logger.critical('Quitting due to keyboard interrupt.')
        print >>sys.stderr, "Interrupted."
        sys.exit(1)


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
    parser.add_option('-I', '--mrs', dest='mrs', metavar='IMPLEMENTATION',
            action='extend', search=['mrs.impl'], default='Serial',
            help='Mrs Implementation (Serial, Master, Slave, etc.)')

    return parser


# vim: et sw=4 sts=4

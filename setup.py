#!/usr/bin/env python

from __future__ import with_statement

import re
import sys

from setuptools import setup


def get_version(filename):
    # This regex isn't very robust, but it should work for most files.
    regex = re.compile(r'''__version__.*=.*['"](\d+\.\d+(?:\.\d+)?)['"]''')
    with open(filename) as f:
        for line in f:
            match = regex.search(line)
            if match:
                return match.group(1)


setup(name="mrs-mapreduce",
    version=get_version('mrs/version.py'),
    description="Mrs: A simplified MapReduce implimentation in Python",
    long_description="See README",
    license="GNU GPL",
    author="BYU AML Lab",
    author_email="mrs-mapreduce@googlegroups.com",
    url="http://code.google.com/p/mrs-mapreduce/",
    packages=['mrs'],
    classifiers=['Development Status :: 4 - Beta',
                'Operating System :: POSIX :: Linux',
                'Environment :: Console',
                'Intended Audience :: Science/Research',
                'License :: OSI Approved :: GNU General Public License (GPL)',
                'Natural Language :: English',
                'Programming Language :: Python',
                'Programming Language :: Python :: 2',
                'Programming Language :: Python :: 2.5',
                'Programming Language :: Python :: 2.6',
                'Programming Language :: Python :: 2.7',
                'Topic :: Scientific/Engineering :: Information Analysis'],
    use_2to3=True,
    )

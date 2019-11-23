#! /usr/bin/env python

import sys

from l10n import make_messages
from mwlib.html._version import version


def main(argv):
    if len(argv) != 2:
        sys.exit('Usage: %s LOCALE' % (argv[0],))
    make_messages(
        locale=argv[1],
        localedir='mwlib/html/locale',
        domain='mwlib.html',
        version=str(version),
        inputdir='mwlib/html',
    )


if __name__ == '__main__':
    main(sys.argv)

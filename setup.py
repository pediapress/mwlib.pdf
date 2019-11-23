#! /usr/bin/env python

import os

from setuptools import find_packages
from setuptools import setup

install_requires = ["mwlib>=0.16.0", "tinycss2>=0.6.1", "cssutils>=1.0.2"]


def get_version():
    d = {}
    execfile("mwlib/pdf/_version.py", d, d)
    return str(d["version"])


def main():
    if os.path.exists('Makefile'):
        print 'Running make'
        os.system('make')

    setup(
        name="mwlib.pdf",
        version=get_version(),
        entry_points={
            'mwlib.writers': ['pdf = mwlib.pdf.writer_interface:writer'],
        },
        install_requires=install_requires,
        namespace_packages=['mwlib'],
        packages=find_packages(exclude=[]),
        include_package_data=True,
        url="https://github.com/pediapress/mwlib.pdf",
        description="MediaWiki HTML to PDF renderer")


if __name__ == '__main__':
    main()

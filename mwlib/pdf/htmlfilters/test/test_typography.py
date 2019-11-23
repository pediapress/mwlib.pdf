#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-
from lxml import etree

from mwlib.pdf.htmlfilters import typography


def test_add_center():
    tree = etree.fromstring(
        '<div class="tiInherit" style="text-align:center;"><p>THE END.</p></div>'
    )
    assert "center" not in tree.attrib["class"]
    typography.add_center_class(tree)
    assert "center" in tree.attrib["class"]

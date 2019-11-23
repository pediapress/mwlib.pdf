import os

from lxml import etree

from mwlib.pdf.htmlfilters import tables

file_directory = os.path.dirname(os.path.realpath(__file__))
extra_directory = os.path.join(file_directory, "extra")


def test_markup_table_header():
    with open(os.path.join(extra_directory, "test_markup_header.html")) as fn:
        root = etree.HTML(fn.read())
        assert len(root.xpath("//table")) == 3
        tables.mark_table_header(root)
        nodes = root.xpath("//thead")
        assert len(nodes) == 3

    print(etree.tostring(root))

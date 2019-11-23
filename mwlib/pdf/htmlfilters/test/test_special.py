import os

from lxml import etree

from mwlib.html.htmlfilters import special
from mwlib.pdf import utils

file_directory = os.path.dirname(os.path.realpath(__file__))


def test_fix_election_diagram():
    with open(os.path.join(file_directory, "extra", "test_fix_election_diagram.html")) as fn:
        root = etree.HTML(fn.read())
        node = root.xpath('//div[@boxid="1403"]')[0]
        styles = utils.get_node_style(node)
        assert "width" not in styles
        special.fix_election_charts(root)
        styles = utils.get_node_style(node)
        assert "width" in styles
        assert styles["width"] == "100%"

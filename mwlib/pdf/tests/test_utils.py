#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import mock
import pytest
from lxml import etree

from .. import utils


def test_iter_articles():
    # TODO: analyze input file
    assert True


def test_flatten_tree():
    tree = etree.fromstring("<h1>hello wörld</h1>")
    result = utils.tree_to_string(tree)
    assert result.strip().decode("utf-8") == "<h1>hello wörld</h1>"

    result = utils.tree_to_string(tree, use_doctype_html=True)
    assert result.strip().decode("utf-8") == "<!DOCTYPE html>\n<h1>hello wörld</h1>"


def test_show_tree(capsys):
    tree = etree.fromstring("<h1>hello <ul><li></li><li/></ul></h1>")
    utils.print_tree_segment(tree)
    captured = capsys.readouterr()
    assert captured.out == "<h1>hello <ul>\n<li>\n<li>\n</ul>\n</h1>\n\n"
    utils.print_tree_segment(tree, "//ul")
    captured = capsys.readouterr()
    assert captured.out == "<ul>\n<li>\n<li>\n</ul>\n\n"


def test_remove_node():
    # regular case
    tree = etree.fromstring("<div><p>Some text <b>oops</b> in a paragraph.</p></div>")
    node = tree[0][0]
    assert node.text == "oops"
    utils.remove_node(node)
    assert tree[0].text == "Some text  in a paragraph."

    # no parent
    tree = etree.fromstring("<ul><li>Some text</li></ul>")
    with pytest.raises(ValueError):
        utils.remove_node(tree)

    tree = etree.fromstring(
        "<div><p>Some <em>emphasized</em> text <b>oops</b> in a paragraph.</p></div>"
    )
    node = tree[0][1]
    assert node.text == "oops"
    utils.remove_node(node)
    assert tree[0][0].tail == " text  in a paragraph."


def test_insert_parent():
    tree = etree.fromstring("<h1>hello <ul><li></li><li/></ul> world</h1>")
    node = tree[0]
    utils.wrap_node(node, "div", dict(width="10"))
    assert etree.tostring(tree[0]) == '<div width="10"><ul><li/><li/></ul></div> world'

    with pytest.raises(ValueError):
        utils.wrap_node(tree, "div")


def test_parse_length():
    for unit_to_test in ["px", "pt", "em", "rem", "%"]:
        length, unit = utils._parse_length("12.1{}".format(unit_to_test))
        assert length == 12.1
        assert unit == unit_to_test
    assert utils._parse_length("px") == (None, "px")

    with pytest.raises(ValueError):
        utils._parse_length("14")

    with pytest.raises(ValueError) as e:
        utils._parse_length("14mm")
    assert e.match(r"^Cannot parse")


def test_get_leaves():
    tree = etree.fromstring("<h1>hello <ul><li></li><li/></ul> world</h1>")
    nodes = utils.get_leaves(tree)
    assert len(list(nodes)) == 2
    for node in nodes:
        assert node.tag == "li"


def test_convert_length():
    units = ["pt", "px", "cm", "in"]
    for unit in units:
        assert utils.convert_length("10.1{}".format(unit), unit) == 10.1
    assert utils.convert_length("100px", "pt") == 75
    assert utils.convert_length("100px", "in") == 1.0416666666666665
    assert utils.convert_length("100px", "cm") == 2.6458333333333335
    assert utils.convert_length("100pt", "px") == 133.33333333333331
    assert utils.convert_length("100pt", "in") == 1.3888888888888888
    assert utils.convert_length("100pt", "cm") == 3.5277777777777777
    assert utils.convert_length("100in", "px") == 9600
    assert utils.convert_length("100in", "pt") == 7200
    assert utils.convert_length("100in", "cm") == 254
    assert utils.convert_length("100cm", "px") == 3779.5275590551178
    assert utils.convert_length("100cm", "pt") == 2834.6456692913384
    assert utils.convert_length("100cm", "in") == 39.370078740157474
    with pytest.raises(ValueError) as e:
        utils.convert_length("100cm", "em")
    assert e.match(r"^Conversion from cm to em")
    assert utils.convert_length("100%", "px") == "100%"


def test_width_in_cm():
    assert utils._width_in_cm("pt") == 0
    assert 1.905 == utils._width_in_cm("72px")
    assert 2.54 == utils._width_in_cm("72pt")
    assert 10 == utils._width_in_cm("10cm")
    assert 25.4 == utils._width_in_cm("10in")


def test_get_node_style():
    tree = etree.fromstring('<div style="width: 200px; height: 100px"><img/></div>')
    result = dict(width="200px", height="100px")
    assert result == utils.get_node_style(tree)


def test_serialize_node_style():
    style_dict = dict(width="200px", height="100px")
    result = "width:200px;height:100px"
    assert result == utils.serialize_node_style(style_dict)


def test_get_node_size():
    tree = etree.fromstring('<div width="200"><img/></div>')
    assert 200 == utils.get_node_size(tree, target_unit="px")
    tree = etree.fromstring('<div style="width: 200px"><img/></div>')
    assert 200 == utils.get_node_size(tree, target_unit="px")


def test_get_node_width():
    tree = etree.fromstring('<div width="200"><img/></div>')
    assert 150 == utils.get_node_width(tree, target_unit="pt")


def test_get_node_height():
    tree = etree.fromstring('<div height="200"><img/></div>')
    assert 150 == utils.get_node_height(tree, target_unit="pt")


def test_append_class():
    tree = etree.fromstring('<div class="col"><img/></div>')
    utils.append_class(tree, "col-1")
    assert "col col-1" == tree.attrib.get("class")
    tree = etree.fromstring("<div><img/></div>")
    utils.append_class(tree, "col-2")
    assert "col-2" == tree.attrib.get("class")


def test_remove_class():
    tree = etree.fromstring('<div class="col bar"><img/></div>')
    utils.remove_class(tree, "foo")
    assert "col bar" == tree.attrib.get("class")
    utils.remove_class(tree, "bar")
    assert "col" == tree.attrib.get("class")
    utils.remove_class(tree, "col")
    assert tree.attrib.get("class") is None


def test_add_node_style():
    tree = etree.fromstring('<div style="width: 200px"><img/></div>')
    utils.add_node_style(tree, "height", "100px")
    assert "width:200px;height:100px" == tree.attrib.get("style")
    utils.add_node_style(tree, "height", "1px")
    assert "width:200px;height:1px" == tree.attrib.get("style")


def test_remove_node_styles():
    tree = etree.fromstring('<div style="width: 200px"><img/></div>')
    utils.remove_node_styles(tree, "width")
    assert tree.attrib.get("style") is None
    tree = etree.fromstring('<div style="width: 200px;height: 100px"><img/></div>')
    utils.remove_node_styles(tree, ["width", "height"])
    assert tree.attrib.get("style") is None
    tree = etree.fromstring('<div style="width: 200px;height: 100px"><img/></div>')
    utils.remove_node_styles(tree, "width")
    assert "height:100px" == tree.attrib.get("style")


def test_change_node_size():
    tree = etree.fromstring('<div width="200"><img/></div>')
    utils.change_node_size(tree, 100, "width")
    assert "100" == tree.attrib.get("width")
    utils.change_node_size(tree, 100.2, "width")
    assert "100.2" == tree.attrib.get("width")
    tree = etree.fromstring('<div width="200"><img/></div>')
    utils.change_node_size(tree, 100.2, "width", "px")
    assert "100.2" == tree.attrib.get("width")

    tree = etree.fromstring("<div><img/></div>")
    utils.change_node_size(tree, 100, "width", "px")
    assert "width:100px" == tree.attrib.get("style")
    tree = etree.fromstring("<div><img/></div>")
    utils.change_node_size(tree, 100, "width")
    assert "width:100px" == tree.attrib.get("style")

    tree = etree.fromstring('<div width="200" style="width:101px"><img/></div>')
    utils.change_node_size(tree, 100, "width", "px")
    assert '<div width="100" style="width:100px"><img/></div>' == etree.tostring(tree)

    tree = etree.fromstring('<div width="200"><img/></div>')
    utils.change_node_size(tree, 50, "width", "%")
    assert "50%" == tree.attrib.get("width")

    tree = etree.fromstring('<div width="200" style="width:101px"><img/></div>')
    utils.change_node_size(tree, None, "width", "px")
    assert "<div><img/></div>" == etree.tostring(tree)


def test_change_node_width():
    tree = etree.fromstring('<div width="200"><img/></div>')
    with mock.patch("mwlib.pdf.utils.change_node_size"):
        utils.change_node_width(tree, 100, "px")
        utils.change_node_size.assert_called_once_with(tree, 100, attr="width", unit="px")


def test_change_node_height():
    tree = etree.fromstring('<div width="200"><img/></div>')
    with mock.patch("mwlib.pdf.utils.change_node_size"):
        utils.change_node_height(tree, 100, "px")
        utils.change_node_size.assert_called_once_with(tree, 100, attr="height", unit="px")


def test_remove_node_width():
    tree = etree.fromstring('<div width="200"><img/></div>')
    with mock.patch("mwlib.pdf.utils.change_node_width"):
        utils.remove_node_width(tree)
        utils.change_node_width.assert_called_once_with(tree, None)


def test_remove_node_height():
    tree = etree.fromstring('<div height="200"><img/></div>')
    with mock.patch("mwlib.pdf.utils.change_node_height"):
        utils.remove_node_height(tree)
        utils.change_node_height.assert_called_once_with(tree, None)

from lxml import etree

from mwlib.pdf.htmlfilters import sizetools
from .utils import RelaxNGValidator

rng = RelaxNGValidator(sizetools)


def test_node_size():
    snippet = """
    <div box_height="123" box_width="510.34"><img /> bla </div>
    """
    node = etree.fromstring(snippet)
    width, height = sizetools.node_size(node)
    assert width == 510.34
    assert height == 123


def test_remove_node_size_attrs():
    method = "remove_node_size_attrs"
    snippet = '<div box_height="123" box_width="510.34"><img /> bla </div>'
    rnc = """
    element div {
        element img { empty },
        text
    }
    """
    result, transformed_snippet = rng.validate(method, snippet, rnc)
    print(transformed_snippet)
    assert result


def test_remove_node_widths():
    method = "remove_node_widths"
    snippet = """
    <div width="100" style="width: 100px;">
        <table width="100" style="width: 100px;">
            <tr>
                <th width="100" style="color: blue; height: 10px; width: 100px;">Headline</th>
                <td width="100" style='color: blue; width: 100px'>Cell</td>
            </tr>
        </table>
    </div>
    """
    rnc = """
    element div {
        attribute style { empty }?,
        element table {
            attribute style { empty }?,
            element tr {
                attribute style { empty }?,
                element th {
                    attribute style { "color: blue; height: 10px;" }?, 
                    text 
                },
                element td {
                    attribute style { "color: blue" | empty }?,
                    text 
                }
            }
        }
    }
    """
    result, transformed_snippet = rng.validate(method, snippet, rnc)
    print(transformed_snippet)
    assert result


def test_fix_nested_widths():
    method = "fix_nested_widths"
    snippet = """
<div>
    <table>
        <tr>
            <th box_width="510.34">Headline</th>
            <td box_width="123">Cell</td>
        </tr>
    </table>
</div>
    """
    rnc = """
    element div {
        attribute box_width { text },
        element table {
            attribute box_width { text },
            element tr {
                attribute box_width { text },
                element th {
                    attribute box_width { xsd:float }, 
                    text 
                },
                element td {
                    attribute box_width { xsd:float },
                    text 
                }
            }
        }
    }
    """
    result, transformed_snippet = rng.validate(method, snippet, rnc)
    print(transformed_snippet)
    assert result


def test_handle_wide():
    method = "handle_wide"
    snippet = """
    """
    rnc = """
    """
    # assert rng.validate(method, snippet, rnc)


def test_resize_node_width_to_columns():
    tree = etree.fromstring('<div><img src="image.gif" /></div>')
    sizetools.resize_node_width_to_columns(tree, 1.00)
    assert "col-4" in tree.attrib.get("class")

    tree = etree.fromstring('<div><img src="image.gif" /></div>')
    sizetools.resize_node_width_to_columns(tree, 160.9)
    assert "col-4" in tree.attrib.get("class")

    tree = etree.fromstring('<div><div><img src="image.gif" /></div></div>')
    node = tree.getchildren()[0]
    sizetools.resize_node_width_to_columns(node, 618.00)
    assert "over-wide" in node.attrib.get("class")

    tree = etree.fromstring('<div><img src="image.gif" /></div>')
    sizetools.resize_node_width_to_columns(tree, 619.00)
    assert "rotated" in tree.attrib.get("class")

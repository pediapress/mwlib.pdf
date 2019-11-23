#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-

from math import ceil

from mwlib.pdf import utils
from .. import config


def node_size(node):
    """
    Get node size
    :param node: xpath node
    :return: width and height of node
    """
    w = h = None
    try:
        w = float(node.get("box_width"))
        h = float(node.get("box_height"))
    except TypeError:
        pass
    return w, h


def remove_node_size_attrs(root):
    """
    Remove node size attributes in final output
    :param root: xpath node
    :return:
    """
    for node in root.xpath("//*[@box_width or @box_height]"):
        for attr in ["box_width", "box_height", "box_width_cm", "box_height_cm"]:
            if node.attrib.get(attr):
                del node.attrib[attr]


def node_is_floatable(node, width, height):
    """
    can the node be floated?
    :param node:
    :param width:
    :param height:
    :return:
    """
    if (
        node.tag == "table"
        and width < config.column_width_pt * 0.70
        and not any(node.tag == "table" for node in node.iterancestors())
    ):
        height_factor = width / float(config.column_width_pt) + 1
        text_height = 0

        for sibling in node.itersiblings():
            if sibling.tag in config.float_end_types:
                break
            w, h = node_size(sibling)
            text_height += h * (height_factor if not sibling.tag in config.h_tags(2, 6) else 1)
            if text_height > height * 0.5:  # require only 50% of the float height
                return True
    return False


def handle_tiny_table(node, width, height):
    """
    float small tables 
    - if they are followed by a sufficient amount of text
    """
    if node_is_floatable(node, width, height):
        utils.append_class(node, "pp_float_table")


def handle_reg_shrink(node, width, reg_width, debug):
    """
    scale node to regular width (using CSS transform) 
    """
    if width <= reg_width:
        if debug:
            utils.add_node_style(node, "background", "lightblue")
        utils.add_node_style(node, "transform-origin", "0px 0px;")
        utils.add_node_style(node, "transform", "scalex({:.2f})".format(config.reg_width / width))


def handle_two_col(node, width, height, reg_width, ext_width, debug):
    """
    span node across two columns (to extended width)
    - if it is wider than the regular width
    """
    if reg_width < width <= ext_width:
        if height > config.max_two_col_float_height:
            if debug:
                utils.add_node_style(node, "background-color", "orange")
            utils.append_class(node, "pp_singlecol")
        else:
            utils.append_class(node, "pp_twocol_span")
            if debug:
                utils.add_node_style(node, "background-color", "yellow")


def handle_table_width(node, width):
    """
    set table width
    - according to "natural" size and width attribute
    """
    if node.tag == "table":
        if width <= config.reg_width:
            utils.append_class(node, "reg-table")

        # tables blown up by width attributes
        if node.get("width") and width > config.reg_width:
            node.attrib.pop("width")
            utils.append_class(node, "wide-table")

        if node.getparent().tag == "div":
            if config.reg_width < width <= config.ext_width:
                utils.append_class(node.getparent(), "wide-table")


def handle_span_all(node, width, height, two_col_max_size, debug):
    """
    limit node width to max
    ? not sure about this ?
    """
    if width > two_col_max_size:
        if debug:
            utils.add_node_style(node, "background-color", "red")
        utils.append_class(node, "pp_singlecol")


def handle_wide(root, debug=False):
    """
    set node width and col_span
    """
    reg_width = config.reg_width
    ext_width = config.ext_width
    for node in root.xpath("//article/div/* | //table"):
        if node.get("class") == "firstHeading":
            del node.attrib["id"]
        width, height = node_size(node)
        handle_two_col(node, width, height, reg_width, ext_width, debug)
        handle_span_all(node, width, height, reg_width, debug)
        handle_table_width(node, width)


def fix_nested_widths(root):
    """
    apply width to parent nodes
    """
    for node in utils.get_leaves(root):
        w, h = node_size(node)
        parents = [p for p in node.iterancestors()]
        max_width = w
        for p in parents:
            _w, _h = node_size(p)
            max_width = max(_w, max_width)
            if max_width > _w:
                p.set("box_width", "{:.2f}".format(max_width))


def limit_widths(root):
    for node in root.iterdescendants():
        css_width = utils.get_node_width(node, "px")
        width, height = node_size(node)
        print node.tag, width, css_width
        if css_width > width:
            utils.change_node_width(node, "{:.2f}pt".format(width))


def resize_tables(root):
    conditions = [
        'not(contains(@class, "infobox"))',
        'not(contains(@class, "pullquote"))',
        "not(ancestor::table)",
    ]
    for node in root.xpath("//table[{}]".format(" and ".join(conditions))):
        resize_node_width_to_columns(
            node, float(node.attrib.get("box_width")), use_thirds_only=False
        )


def remove_node_widths(root):
    for node in root.xpath("//table|//div|//td|//th"):
        styles = node.get("style")
        if node.get("width"):
            del node.attrib["width"]
        if styles and "width" in styles:
            node.set(
                "style",
                ";".join(
                    [style for style in styles.split(";") if not style.strip().startswith("width")]
                ),
            )


def handle_col_floats(root):
    for node in root.xpath('//*[contains(@class, "infobox")]'):
        w, h = node_size(node)
        if h < config.min_float_height or (
            h < 2 * config.min_float_height and node_is_floatable(node, w, h)
        ):
            utils.append_class(node, "pp_no_float")
        elif "pp_float_table" in node.get("class", ""):
            utils.remove_class(node, "pp_float_table")


def resize_node_width_to_columns(node, width_in_pt, use_thirds_only=True):
    """
    resizes a given node to columns by adding a col-* class
    """
    utils.remove_node_width(node)
    target_col_width = next((width for width in config.columns.values() if width > width_in_pt), 0)
    if target_col_width == 0:
        if width_in_pt <= config.tolerated_over_width:
            utils.wrap_node(node, "div", {"class": "over-wide-wrapper"})
            utils.append_class(node, "over-wide")
        else:
            utils.append_class(node, "rotated-table")
        return
    cols = config.columns.values().index(target_col_width) + 1
    if use_thirds_only:
        cols = int(4 * ceil(float(cols) / 4))
    utils.append_class(node, "col-{}".format(cols))


def resize_overwide_tables(root):
    """
    scale node to regular width (using CSS transform)
    """
    for node in root.xpath('//table[contains(@class, "over-wide")]'):
        width = float(node.attrib.get("box_width"))
        wrapper = node.getparent()
        utils.add_node_style(wrapper, "transform-origin", "0 0")
        utils.add_node_style(
            wrapper, "transform", "scale({:.2f}) ".format(config.columns["col-12"] / width)
        )

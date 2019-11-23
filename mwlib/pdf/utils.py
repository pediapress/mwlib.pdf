#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-

import gzip
import json
import re

import tinycss2
from lxml import etree
from six import string_types

from mwlib.pdf.config import *


def iter_articles(articlelist_fn):
    """
    Fetch article source
    """
    with open(articlelist_fn) as f:
        articles = json.load(f)
    for article_info in articles:
        path = article_info.get("path")
        if not path:
            print("article not found: {}".format(article_info))
            continue
        with gzip.open(path, "rb") as f:
            data = f.read()
        article_info["data"] = data
        yield article_info


def tree_to_string(tree, use_doctype_html=False):
    """
    Transform DOM-tree to HTML
    """
    return etree.tostring(
        tree,
        pretty_print=True,
        encoding="utf-8",
        method="html",
        doctype="<!DOCTYPE html>" if use_doctype_html else None,
    )


def print_tree_segment(tree, xpath=""):
    """
    Print flattened tree
    """
    if xpath:
        tree = tree.xpath(xpath)[0]
    print(tree_to_string(tree))


def remove_node(node):
    """
    remove node but keep tail if present
    """
    parent = node.getparent()
    if parent is None:
        raise ValueError("Node has no parent!")
    if not node.tail:
        parent.remove(node)
        return
    prev = node.getprevious()
    if prev is not None:
        if prev.tail:
            prev.tail += node.tail
        else:
            prev.tail = node.tail
        parent.remove(node)
        return
    parent.text = parent.text or ""
    parent.text += node.tail
    parent.remove(node)


def wrap_node(node, wrapper_tag, wrapper_attrib={}):
    """
    Wrap an element in a deliberate wrapper
    """
    p = node.getparent()
    if p is None:
        raise ValueError("Node has no parent!")
    wrapper = etree.Element(wrapper_tag, wrapper_attrib)
    p.replace(node, wrapper)
    wrapper.append(node)
    wrapper.tail = node.tail
    node.tail = None
    return wrapper


def _parse_length(txt):
    """
    extract length and unit from a given css string
    """
    if txt == "auto":
        return 100, "%"
    result = re.search(r"(?P<val>[\d.]*?)(?P<unit>(pt|px|em|rem|cm|ex|in|%))", txt)
    if result is None:
        raise ValueError("Cannot parse length! Please enter valid unit: {}".format(txt))
    unit = result.group("unit")
    try:
        length = float(result.group("val"))
    except ValueError:
        length = None
    return length, unit


def get_leaves(root):
    """
    get all nodes without children below a given root node
    """
    for node in root.iterdescendants():
        if len(node.getchildren()) == 0:
            yield node


def convert_length(length_str, target_unit="cm"):
    supported_units = ["pt", "px", "cm", "in"]
    if not length_str:
        return 0
    length, unit = _parse_length(length_str)
    if not length:
        return 0
    elif unit == target_unit:
        return length
    elif unit in ["%", "em", "ex"]:
        # non-supported units are returned as is
        return length_str
    if unit not in supported_units:
        raise ValueError('unit "{}" not supported'.format(unit))
    conversions = {
        "px": {"pt": PPI / CSS_DPI, "in": 1 / CSS_DPI, "cm": IN_2_CM / CSS_DPI,},
        "pt": {"px": CSS_DPI / PPI, "in": 1 / PPI, "cm": IN_2_CM / PPI,},
        "in": {"px": CSS_DPI, "pt": PPI, "cm": IN_2_CM,},
        "cm": {"px": CSS_DPI / IN_2_CM, "pt": PPI / IN_2_CM, "in": 1 / IN_2_CM,},
    }
    if conversions[unit].get(target_unit) is None:
        raise ValueError(
            "Conversion from {} to {} is not supported (yet)!".format(unit, target_unit)
        )
    result = length * conversions[unit][target_unit]
    return result


def _width_in_cm(length_str):
    """
    convert pt, px, em to cm
    """
    return convert_length(length_str, "cm")


def get_node_style(node):
    styles = tinycss2.parse_declaration_list(node.get("style", ""))
    return dict(
        (d.lower_name, "".join([v.serialize() for v in d.value]).strip())
        for d in styles
        if d.type == "declaration"
    )


def serialize_node_style(node_style_dict):
    return ";".join(map(lambda k: "{0}:{1}".format(k, node_style_dict[k]), node_style_dict))


def get_node_size(node, attr="width", target_unit="px"):
    size = node.get(attr, None)
    if size and size.isdigit():
        size = "{}px".format(size)
    else:
        size = get_node_style(node).get(attr, "")
    size = convert_length(size, target_unit=target_unit)
    return size


def get_node_width(node, target_unit="px"):
    """
    get node width in target_unit
    """
    return get_node_size(node, attr="width", target_unit=target_unit)


def get_node_height(node, target_unit="px"):
    """
    get node height in target_unit
    """
    return get_node_size(node, attr="height", target_unit=target_unit)


def append_class(node, cls):
    current_cls = node.get("class")
    if current_cls:
        node.set("class", current_cls + " " + cls)
    else:
        node.set("class", cls)


def remove_class(node, cls):
    if not node.get("class"):
        return
    current_classes = node.get("class").split(" ")
    try:
        current_classes.remove(cls)
    except ValueError:
        return
    class_str = " ".join(current_classes)
    if not class_str:
        del node.attrib["class"]
    else:
        node.set("class", class_str)


def add_node_style(node, style_attr, style_val):
    node_style = get_node_style(node)
    node_style[style_attr] = style_val
    node.set("style", serialize_node_style(node_style))


def remove_node_styles(node, style_attrs):
    node_style = get_node_style(node)
    if isinstance(style_attrs, string_types):
        style_attrs = [style_attrs]
    for style_attr in style_attrs:
        if style_attr in node_style:
            del node_style[style_attr]
    style_str = serialize_node_style(node_style)
    if style_str:
        node.set("style", style_str)
    else:
        if "style" in node.attrib:
            del node.attrib["style"]


def change_node_size(node, size, attr="", unit=""):
    """
    Change size of node, respect existing width and height attributes
    """
    if not size:
        if node.attrib.get("style"):
            remove_node_styles(node, [attr])
        if node.attrib.get(attr):
            del node.attrib[attr]
        return
    if isinstance(size, int) or isinstance(size, float):
        size = str(size)
    if not unit:
        unit = "px"
    if node.get(attr):
        if unit == "%":
            node.set(attr, "{}{}".format(size, unit))
        else:
            node.set(attr, size or "")
    else:
        add_node_style(node, attr, "{0}{1}".format(size, unit))
    if node.get("style") and attr in get_node_style(node):
        add_node_style(node, attr, "{0}{1}".format(size, unit))


def change_node_width(node, width, unit=""):
    change_node_size(node, width, attr="width", unit=unit)


def change_node_height(node, height, unit=""):
    change_node_size(node, height, attr="height", unit=unit)


def remove_node_width(node):
    change_node_width(node, None)


def remove_node_height(node):
    change_node_height(node, None)

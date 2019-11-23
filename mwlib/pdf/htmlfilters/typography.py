#!/usr/bin/env python
from mwlib.pdf import utils


# http://www.mediaevent.de/css/font-size.html
def fix_sizes(root):
    font_sizes = [
        ("xx-small", 3.0 / 5),
        ("x-small", 3.0 / 4),
        ("small", 8.0 / 9),
        ("medium", 1),
        ("large", 6.0 / 5),
        ("x-large", 3.0 / 2),
        ("xx-large", 2.0 / 1),
    ]
    for size_name, size_factor in font_sizes:
        for node in root.xpath('//*[contains(@style, "font-size: {}")]'.format(size_name)):
            style = node.get("style")
            node.set(
                "style",
                style.replace(
                    "font-size: {}".format(size_name), "font-size: {}%".format(size_factor * 100)
                ),
            )


def add_center_class(root):
    for node in root.xpath('//div[contains(@style, "text-align:center")]'):
        utils.append_class(node, "center")


def remove_p_padding(root):
    for node in root.xpath('//p[contains(@style, "padding")]'):
        utils.remove_node_styles(node, "padding")

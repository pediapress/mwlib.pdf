#!/usr/bin/env python

from mwlib.pdf import utils


def clean_infobox_inner_width(root):
    for node in root.xpath('//*[contains(@class, "infobox")]//div[contains(@style, "width")]'):
        if "width" in utils.get_node_style(node):
            utils.remove_node_styles(node, "width")


def clean_infobox_padding(root):
    for node in root.xpath(
        '//*[contains(@class, "infobox")]//*[(self::div or self::td or self::th) and @style]'
    ):
        if "padding" in node.attrib["style"]:
            utils.remove_node_styles(
                node,
                ["padding", "padding-left", "padding-right", "padding-top", "padding-bottom",],
            )


def clean_infobox_background_color(root):
    for node in root.xpath('//*[contains(@class, "infobox")]//th[contains(@style, "background")]'):
        utils.remove_node_styles(node, ["background-color", "background"])

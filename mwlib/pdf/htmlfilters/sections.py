#!/usr/bin/env python

import json
import os

from mwlib.pdf import utils


def get_section_ids(language):
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../ref_section_info.json")
    with open(fn) as f:
        ref_section_map = json.load(f)
    return ref_section_map.get(language, [])


def remove_references(root, language):
    section_ids = get_section_ids(language)
    remove_list = []
    pred = " or ".join(['.//@id="{}"'.format(section) for section in section_ids])
    if not pred:
        return
    for node in root.xpath("//h2[{}]".format(pred)):
        remove_list.append(node)
        for sib in node.itersiblings():
            remove_list.append(sib)
        break
    for node in remove_list:
        node.getparent().remove(node)


def remove_empty(root):
    # remove <p><br></p> nodes
    for bad in root.xpath("//p[* and not (*[not(self::br)]) and not(text())]"):
        utils.remove_node(bad)

    # remove a <br> if it's the first node in a paragraph
    for bad in root.xpath("//p/*[1][self::br]"):
        previous_text = bad.getparent().text
        if previous_text is None or previous_text.strip() == "":
            utils.remove_node(bad)

    # remove <p></p> nodes
    for bad in root.xpath("//p[not(*)]"):
        if not bad.text or bad.text.strip() == "":
            utils.remove_node(bad)

    # remove <li> text that starts with a space
    for bad in root.xpath("//li"):
        if bad.text:
            bad.text = bad.text.lstrip()

    # remove space in tails after h1
    for h1 in root.xpath("//h1"):
        if h1.tail is not None:
            h1.tail = h1.tail.strip()


def h1_add_no_top_margin(root):
    # add no-top-margin class to h1 in articles that immediately follow a chapter
    for h1 in root.xpath(
        '//article[@class="pp_chapter" and count(*) = 1]/following-sibling::article[1]'
    ):
        utils.append_class(h1, "no-top-margin")


def change_references_id_to_class(root):
    for node in root.xpath('//*[@id="References"]'):
        if node.tag == "h2":
            utils.append_class(node, "references")
        else:
            utils.append_class(node.getparent(), "references")
        del node.attrib["id"]

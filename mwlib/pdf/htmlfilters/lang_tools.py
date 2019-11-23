#!/usr/bin/env python

from mwlib.pdf import utils


def get_map(map_name, language):
    _map = map_name.get(language, {})
    _map.update(map_name.get("*", {}))
    return _map


_class_to_style_map = {
    "no": {"basisbilde": ("position", "relative"), "hide": ("display", "none"),},
}

_class_map = {"*": {"infobox_v2": "infobox",}}


# map class names to explicit styles.
# we do this since we use Wikipedias stylesheets
def map_class_to_style(article):
    class_to_style_map = get_map(_class_to_style_map, article.language)
    if not class_to_style_map:
        return
    for css_class in class_to_style_map:
        style_attr, style_val = class_to_style_map[css_class]
        for node in article.dom.xpath('//*[contains(@class, "{}")]'.format(css_class)):
            utils.add_node_style(node, style_attr, style_val)
            utils.remove_class(node, css_class)


def map_classes(article):
    class_map = get_map(_class_map, article.language)
    if not class_map:
        return
    for node in article.dom.xpath("//*[@class]"):
        class_list = node.get("class").split(" ")
        for cls in class_map:
            if cls in class_list:
                utils.remove_class(node, cls)
                utils.append_class(node, class_map[cls])


def filter_nl_references(root):
    if article.language != "nl":
        return
    for ref_box in root.xpath('//table[.//b[text()="Bronnen, noten en/of referenties"]]'):
        utils.remove_node(ref_box)


def filter_content(root):
    filter_nl_references(article)

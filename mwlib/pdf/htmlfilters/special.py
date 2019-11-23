#!/usr/bin/env python

from mwlib.pdf import utils


# https://en.wikipedia.org/wiki/A.D._Baucau
# https://en.wikipedia.org/wiki/A.E.K._Athens_F.C.
def remove_soccer_kits(root):
    def get_kit_images(node):
        return node.xpath('.//img[contains(@_src, "/Kit_")]')

    min_kit_images = 5
    kit_images = get_kit_images(root)
    kit_container = None

    for img in kit_images:
        start = True
        container = img
        while start or (
            len(kits_in_container) < min_kit_images
            or (len(kits_in_container) >= min_kit_images and kit_leaves_ratio >= 0.35)
        ):
            kit_container = container
            container = container.getparent()
            if container is None:
                kit_container = None
                break
            kits_in_container = get_kit_images(container)
            kit_leaves_ratio = len(kits_in_container) / float(
                len(list(utils.get_leaves(container)))
            )
            if kit_container.tag == "tr":
                break
            start = False
        if kit_container is not None and len(get_kit_images(kit_container)) >= min_kit_images:
            utils.remove_node(kit_container)


# https://de.wikipedia.org/wiki/Wiesbaden#Stadtverordnetenversammlung
def fix_election_charts(root):
    for node in root.xpath('//div[@class="float-right"]/div[contains(@style, "relative;")]/div'):
        styles = utils.get_node_style(node)
        if "width" not in styles:
            utils.add_node_style(node, "width", "100%")

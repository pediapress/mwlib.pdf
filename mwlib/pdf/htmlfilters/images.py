#!/usr/bin/env python

import os
import re
import urllib

from PIL import Image
from lxml import etree
from lxml.builder import ElementMaker
from mwlib.log import Log

from mwlib.pdf import utils
from mwlib.pdf.htmlfilters.sizetools import resize_node_width_to_columns
from .. import config
from ..config import column_width_pt

log = Log("mwlib.pdf.html2pdf")
E = ElementMaker()
number_re = re.compile(r"^(\d+)")


valid_image_extensions = [".png", ".jpg", ".gif", ".svg", ".jpeg"]


def fix_image_src(article):
    """
    replace img src with path on local disc
    """
    for img in article.dom.xpath("//img"):
        src = img.get("src")
        if os.path.splitext(src)[1] == ".gif":
            img_name = src.split("/")[-1]
        else:
            img_name = src.split("/")[-2]
        img_name = urllib.unquote(img_name)
        img_disk_path = article.env.images.getDiskPath(img_name)
        if img_disk_path and os.path.exists(img_disk_path):
            img.set("src", img_disk_path)
        else:
            img.set("src", "")
            log.debug("No local image source found for `{}`".format(img_name))


def set_size_attributes(root):
    """
    Set width and height attributes on image (deprecated)
    """
    for img in root.xpath("//img"):
        variants = ["width", "height"]
        for variant in variants:
            if img.get(variant) is None:
                style = utils.get_node_style(img)
                value = style.get(variant)
                try:
                    value = number_re.match(value).group(0)
                except Exception:
                    continue
                img.set(variant, value)


def get_img_size(node):
    """
    get size of a node in px
    """
    try:
        width = utils.get_node_width(node)
        height = utils.get_node_height(node)
        return width, height
    except TypeError:
        return 0, 0


def get_original_image_size(node):
    """
    extract original size from web page markup
    """
    path = node.get("src")
    if os.path.splitext(path) == ".svg":
        svg_root = etree.parse(path).getroot()
        width = float(svg_root.get("width")[:-2])
        height = float(svg_root.get("height")[:-2])
        node.set("data-source-image-width", str(width) + "px")
    else:
        width, height = get_img_size(node)
    return width, height


def node_has_valid_image_src(node):
    ext = os.path.splitext(node.get("src"))[1]
    return ext.lower() in valid_image_extensions


def remove_missing(root):
    """
    remove missing images
    """
    for img in root.xpath("//img"):
        if not node_has_valid_image_src(img):
            img.getparent().remove(img)


def strip_height(root):
    for img in root.xpath("//img"):
        if img.get("height"):
            del img.attrib["height"]


def check_size(article):
    for img in article.dom.xpath(
        '//img[not(substring(@src, string-length(@src)-3) = ".svg"'
        ' or substring(@src, string-length(@src)-3) = ".SVG")]'
    ):
        if not node_has_valid_image_src(img):
            continue
        path = img.get("src")
        if os.name == "nt":
            regex = "%2[fF]|%5[cC]"
            path = re.sub(regex, "/", path)
        if not os.path.exists(path):
            continue
        im = Image.open(path)
        width, height = im.size
        physical_width_in = config.px2in * float(img.get("width"))
        ppi = int(round(width / physical_width_in))
        img.set("data-ppi", str(ppi) + "ppi")
        img.set("data-source-image-width", str(width) + "px")
        if ppi < 240:
            utils.append_class(img, "low-ppi")


def tag_local_images(root, collection):
    input_image_path = collection.get("image_path")
    if input_image_path and os.path.exists(input_image_path):
        input_images = os.listdir(input_image_path)
        for img in root.xpath("//img"):
            file_name = str.split(img.get("_src", ""), "/")[-1]
            if file_name in input_images:
                utils.append_class(img, "local-image")


def scale_inline(root):
    max_inline_width = 50
    max_inline_height = 50
    for img in root.xpath(
        "//img[@width<{max_inline_width}][@height<{max_inline_height}]".format(**locals())
    ):
        w, h = get_img_size(img)
        img.set("width", str(w / 2))
        img.set("height", str(h / 2))
        utils.append_class(img, "inline")


def limit_size(root):
    for img in root.xpath('//img[not(contains(@class, "inline"))]'):
        w, h = get_img_size(img)
        if w == 0 or h == 0:
            continue
        if isinstance(h, unicode) or isinstance(h, str):
            continue
        in_table = any(node.tag == "table" for node in img.iterancestors())
        max_height_outside = 7.5 * config.cm2px
        max_height_in_table = 5 * config.cm2px
        max_height = max_height_in_table if in_table else max_height_outside
        max_width = 6.03 * config.cm2px

        # downscale if dimensions too big
        scale_factor = min(min(1, max_height / h), min(1, max_width / w))
        # upscale image too full width, if the image is wider than 70% of max width
        if scale_factor == 1:
            scaled_height = max_width / w * h
            if 0.7 * max_width < w < max_width and scaled_height < max_height:
                scale_factor = max_width / w

        if scale_factor != 1:
            img.set("width", str(w * scale_factor))
            img.set("height", str(h * scale_factor))

            for node in [n for n in img.iterancestors()]:
                w = utils.get_node_width(node, "px")
                h = utils.get_node_height(node, "px")
                if w:
                    utils.change_node_width(node, w * scale_factor, unit="px")
                if h:
                    utils.change_node_height(node, h * scale_factor, unit="px")


def fix_thumbs(root):
    """
    remove explit width in thumbinner div
    otherwise correct image sizing/positioning is not guaranteed
    """
    for div in root.xpath('.//div[contains(@class, "thumbinner")]'):
        utils.remove_node_width(div)


def fix_galleries(root):
    for gallery in root.xpath('.//ul[contains(@class, "gallery")]'):
        for leaf in gallery.xpath(".//*"):
            utils.remove_node_width(leaf)
            utils.remove_node_height(leaf)
            utils.remove_node_styles(leaf, "margin")
        for leaf in gallery.xpath('.//li[contains(@class, "gallerybox")]'):
            utils.append_class(leaf, "col-4")
            img = leaf[0][0][0][0][0]
            utils.append_class(img, "thumbimage")
            url = img.attrib.get("src")
            utils.add_node_style(leaf[0][0][0], "background-image", "url({})".format(url))


def mark_img_container(root):
    """https://de.wikipedia.org/wiki/Chaoyang_%28Shantou%29"""
    for img_container in root.xpath('//article/div/*[self::div[contains(@class,"thumb ")]]'):
        utils.append_class(img_container, "pp_figure")


def fix_abspos_overlays(root):
    for container in root.xpath(
        ('//*[contains(@style, "position")' ' and contains(@style, "relative")]')
    ):
        w = utils.get_node_width(container, target_unit="px")
        h = utils.get_node_height(container, target_unit="px")
        if not (w and h):
            img = container.xpath(".//img")
            if not img:
                continue
            img = img[0]
            w, h = get_img_size(img)
        for node in container.xpath(
            ('.//*[contains(@style, "position")' ' and contains(@style, "absolute")]')
        ):
            style = utils.get_node_style(node)
            left = style.get("left")
            top = style.get("top")
            for attr in ["left", "top"]:
                val = locals()[attr]
                if not val:
                    continue
                if val.endswith("%"):
                    continue
                elif val.endswith("px"):
                    val = val[:-2]
                elif val.isdigit():
                    pass
                else:
                    continue
                try:
                    new_val = 100 * int(float(val)) / (w if attr == "left" else h)
                except (ValueError, ZeroDivisionError):
                    continue
                utils.add_node_style(node, attr, "{}%".format(new_val))


def fix_links_on_images(root):
    for a in root.xpath("//a[img]"):
        a.attrib["wiki_href"] = a.attrib.get("href")
        del a.attrib["href"]


def set_figure_div_size(root):
    for figure_div in root.xpath("//div"):
        classes = figure_div.get("class", "").split(" ")
        if "thumb" not in classes:
            continue
        img_width = figure_div.xpath(".//img/@width")
        if img_width:
            utils.add_node_style(figure_div, "width", img_width[0] + "px")


def move_caption_below_image(root):
    """
    move the caption behind / below the image
    """
    for img_container in root.xpath('//article/div//*[self::div[contains(@class,"thumb ")]]'):
        if img_container[0][0].get("class") == "thumbcaption":
            img_container[0].append(img_container[0][0])


def remove_img_style_size(root):
    """
    add class to img container and remove explicit width attributes
    """
    xpath_conditions = [
        'contains(@class,"thumb") ',
        'and not(contains(@class, "tmulti"))',
        'and not(contains(@class, "thumbinner"))',
        'and not(contains(@class, "thumbcaption"))',
        'and not(contains(@class, "thumbimage"))',
    ]
    result = root.xpath("//div[{}]".format(" ".join(xpath_conditions)))
    for img_container in result:
        if "map" in img_container.attrib.get("class", ""):
            continue
        thumbinner = img_container.xpath('.//*[contains(@class,"thumbinner")]')
        for node in thumbinner:
            utils.remove_node_styles(node, ["width", "height", "max-width"])
        if not img_container.xpath(".//img"):
            log.debug("No <img> found in {}".format(etree.tostring(img_container)))
            continue
        img = img_container.xpath(".//img")[0]
        width = utils.get_node_width(img, target_unit="pt")
        utils.remove_node_styles(img, ["width", "height"])
        cols = int(round(width / (column_width_pt * 4)))
        if cols > 3:
            cols = 3
        cols = cols * 4
        utils.append_class(img_container, "col-{}".format(cols))
        utils.remove_node_width(img_container)
        utils.remove_node_width(img)


def fix_img_style_size_tmulti(root):
    """
    replace explicit width attributes with col-* classes and percentages
    """
    xpath_conditions = [
        'contains(@class,"thumb") ',
        'and contains(@class, "tmulti")',
        'and not(contains(@class, "thumbinner"))',
        'and not(contains(@class, "thumbcaption"))',
        'and not(contains(@class, "thumbimage"))',
    ]
    result = root.xpath("//div[{}]".format(" ".join(xpath_conditions)))
    for img_container in result:
        thumbinner = img_container.xpath('.//*[contains(@class, "thumbinner")]')[0]
        total_width = utils.get_node_size(thumbinner, attr="max-width", target_unit="pt")
        utils.remove_node_styles(thumbinner, "max-width")
        resize_node_width_to_columns(img_container, total_width)
        for tsingle in thumbinner.xpath('.//*[contains(@class, "tsingle")]'):
            width = _remove_inner_image_node_width(tsingle, inner_class="thumbimage")
            single_width = width / total_width * 100
            utils.add_node_style(tsingle, "width", "{}%".format(single_width))


def fix_image_tables(root):
    img_tables = root.xpath(
        '//table[contains(@class, "short-table") and not(contains(@class, "infobox")) and .//a[contains(@class, "image")]]'
    )
    for table in img_tables:
        utils.remove_node_styles(table, "margin")
        utils.append_class(table, "image-table")
        max_widths = {}
        for row in table.xpath(".//tr"):
            for n, column in enumerate(row.xpath(".//td")):
                for img in column.xpath(".//img"):
                    width = utils.get_node_width(img, target_unit="px")
                    max_widths[n] = max(width, max_widths.get(n, 0))
        total_width = sum(max_widths.values())
        if total_width * config.px2pt > config.page_width_pt:
            utils.append_class(table, "wide-image-table")
            for row in table.xpath(".//tr"):
                for n, column in enumerate(row.xpath(".//td")):
                    _remove_inner_image_node_width(column, "image")
                    utils.remove_node_styles(column, ["padding-left", "padding", "margin"])
                    utils.add_node_style(
                        column, "width", "{}%".format(max_widths.get(n, 0) / total_width * 100)
                    )
        elif total_width > 0:
            for img in table.xpath(".//img"):
                _resize_image_node_width_to_pt(img)


def fix_col8_low_ppi(root):
    xpath_conditions = [
        'contains(@class, "thumb ")',
        'and contains(@class, "col-8")',
        'and //img[contains(@class, "low-ppi")]',
    ]
    result = root.xpath("//div[{}]".format(" ".join(xpath_conditions)))
    for img_container in result:
        img_container.attrib["class"] = img_container.attrib["class"].replace("col-8", "col-4")


def remove_low_ppi(root):
    result = root.xpath('//img[contains(@class, "low-ppi")]')
    for img in result:
        utils.remove_class(img, "low-ppi")


def remove_responsive_styles(root):
    result = root.xpath("//style")
    for node in result:
        if "@media" in node.text and "max-width" in node.text:
            utils.remove_node(node)


def _remove_inner_image_node_width(node, inner_class="thumbinner"):
    """
    remove explicit widths from an image node
    Side effect: removes the node if it doesn't contain an image!
    :param node:
    :param inner_class: "thumbinner" or "thumbimage"
    :return: original width of the image in pt
    """
    utils.remove_node_styles(node, ["width", "height", "max-width"])
    wrapper_nodes = node.xpath('.//*[contains(@class,"{}")]'.format(inner_class))
    for wrapper_node in wrapper_nodes:
        utils.remove_node_styles(wrapper_node, ["width", "height", "max-width"])
    if not node.xpath(".//img"):
        log.debug("No <img> found in {}. Removing node.".format(etree.tostring(node)))
        utils.remove_node(node)
        return 0
    img = node.xpath(".//img")[0]
    width = utils.get_node_width(img, target_unit="pt")
    utils.remove_node_styles(img, ["width", "height"])
    utils.remove_node_width(img)
    return width


def _resize_image_node_width_to_pt(node):
    """
    resize images from px to pt: 96px -> 72pt = shrink to 75%
    the scale factor is more or less deliberate but looks decent in sample pages
    """
    if node.tag != "img":
        return
    width = utils.get_node_width(node, target_unit="px")
    utils.remove_node_styles(node, ["width", "height"])
    utils.remove_node_width(node)
    utils.add_node_style(node, "width", "{}px".format(width * config.px2pt))


def remove_images_with_class_remove(root):
    """
    images with incompatible licenses are tagged with class="remove"
    """
    for img in root.xpath('//img[contains(@class, "remove")]'):
        # case 1: the map in the table:
        for ancestor in img.xpath(
            './ancestor::div[@class="noviewer" and @style="position: relative;"]'
        ):
            utils.remove_node(ancestor.getnext())
            utils.remove_node(ancestor)
        for ancestor in img.xpath('./ancestor::li[contains(@class, "gallerybox")]'):
            utils.remove_node(ancestor)
        for ancestor in img.xpath('./ancestor::div[contains(@class, "thumb")]'):
            utils.remove_node(ancestor)
        for ancestor in img.xpath("./ancestor::tr"):
            removal_is_safe = True
            for node in ancestor.iterdescendants():
                if len(node.getchildren()) > 1:
                    removal_is_safe = False
            if removal_is_safe:
                utils.remove_node(ancestor)
        if img.getparent() is not None:
            utils.remove_node(img)


def add_class_to_infobox_wide_images(root):
    """
    add `infobox-wide` to images wider than 100px in an infobox and remove explicit width
    """
    for node in root.xpath('//*[contains(@class, "infobox")]//img'):
        if "width" in node.attrib and int(node.attrib.get("width")) > 100:
            utils.append_class(node, "infobox-img-wide")
            utils.remove_node_width(node)
            utils.remove_node_height(node)
            for td in node.xpath("./ancestor::td"):
                utils.append_class(td, "contains-img-wide")
        elif "width" in node.attrib and int(node.attrib.get("width")) <= 100:
            node.attrib["width"] = str(int(node.attrib["width"]) / config.px2pt)


def optimize_maps(root):
    for node in root.xpath('//div[contains(@class, "map")]'):
        for subnode in node.xpath('.//div[contains(@style, "border")]'):
            utils.remove_node_styles(subnode, "border")

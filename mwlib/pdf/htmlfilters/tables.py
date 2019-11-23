#!/usr/bin/env python

import re
from copy import deepcopy

from lxml import etree
from lxml.builder import ElementMaker

from mwlib.pdf import utils
from .. import config

E = ElementMaker()


def _get_header_row(root):
    header = {}
    col_idx = 0
    for node in root.xpath(".//tr[1]/th"):
        node.tag = "b"
        header[col_idx] = node
        col_idx += int(node.get("colspan", "1"))
        for attrib in node.attrib:
            node.set(attrib, "")
    return header


def remove_multicolumn(root):
    mergable_content = ["ul", "ol"]
    allowed_tags = set(mergable_content + ["div"])
    heading_tags = set(config.h_tags(2, 6))
    for table in root.xpath("//table[not(.//table) and not(ancestor::table)]"):
        # all content must either be: 1) a heading 2) no tag 3) allowed tag
        # a mix of different allowed tags is prohibited!
        content_tags = set(
            [node.tag for node in table.xpath(".//td/*") if node.tag not in heading_tags]
        )
        if len(content_tags) != 1 or content_tags.pop() not in allowed_tags:
            continue

        # make sure that table headers are only present in "headers rows"
        # and not in one column
        horizontal_headers = True
        for row in table.xpath(".//tr[.//th]"):
            if any(node.tag != "th" for node in row.iterchildren()):
                horizontal_headers = False
                break
        if not horizontal_headers:
            continue

        num_cols = len(table.xpath(".//tr/td"))
        content = []
        for col_idx in range(1, num_cols + 1):
            for cell in table.xpath(
                ".//tr/th[position()={0}]|.//tr/td[position()={0}]".format(col_idx)
            ):
                if cell.tag == "th":
                    header = deepcopy(cell)
                    header.tag = "b"
                    content.append(header)
                    continue
                for node in cell:
                    if content and node.tag == content[-1].tag and node.tag in mergable_content:
                        for item in node:
                            content[-1].append(item)
                    else:
                        content.append(node)
        if len(content) == 1:
            table.getparent().replace(table, content[0])
        else:
            for node in content:
                table.addprevious(node)
            table.getparent().remove(table)
        if content:
            content[-1].tail = table.tail


def remove_explicit_multicolumn(root):
    for multicoltable in root.xpath('//table[contains(@class, "multicol")]'):
        for cell_content in multicoltable.xpath("./tbody/tr/td/*|./tr/td"):
            for node in reversed(cell_content):
                multicoltable.addnext(node)
        multicoltable.getparent().remove(multicoltable)


def remove_infobox_divs(root):
    for div in root.xpath('//div[contains(@class,"infobox")]'):
        for attr in div.keys():
            del div.attrib[attr]
        div.set("class", "infobox")


def add_infobox_wrapper(root):
    for infobox in root.xpath('//*[contains(@class,"infobox")]'):
        utils.wrap_node(infobox, "div", dict({"class": "infobox-wrapper"}))


def identify_infoboxes(root):
    for table in root.xpath('//table[not(contains(@class, "infobox"))]'):
        if any("infobox" in val.lower() for val in table.values()):
            utils.append_class(table, "infobox")

    # https://de.wikipedia.org/wiki/Das_M%C3%A4dchen_auf_dem_Meeresgrund
    # tables less than 3 siblings away from article start are considered infoboxes
    # if they are wrapped in container nodes, the containers are stripped if
    # no siblings are present - otherwise the table is *not* marked as an infobox
    path = (
        '//h1[@class="firstHeading"]/'
        "following-sibling::*[position()<3]/"
        'descendant-or-self::table[not(contains(@class, "infobox"))]'
    )
    for table in root.xpath(path):
        ancestors = [node for node in table.iterancestors() if (node.tag != "article")]
        if any(len(node.getchildren()) != 1 for node in ancestors):
            continue
        if len(ancestors):
            container = ancestors[-1]
            container.getparent().replace(container, table)
        utils.append_class(table, "infobox")


def mark_table_header(root):
    for table in root.xpath("//table"):  # //table[not(descendant::node()[@rowspan>2])]
        thead = None
        tags = [node.tag for node in table.iterchildren()]
        if "tbody" in tags:
            start_node = table.xpath("./tbody")[0]
        else:
            start_node = table
        for row in start_node.iterchildren():
            if row.tag == "caption":
                continue
            if all(cell.tag == "th" for cell in row.iterchildren()):
                if thead is None:
                    thead = etree.Element("thead")
                    if start_node.tag == "table":
                        row.addprevious(thead)
                    else:
                        start_node.addprevious(thead)
                thead.append(row)
            else:
                break


def improve_table_breaks(root):
    # https://de.wikipedia.org/wiki/Suzy_Batkovic-Brown
    for table in root.xpath('//table[not(ancestor::table) and not(contains(@class, "infobox"))]'):
        rows = table.xpath("./tr|./thead/tr|./tbody/tr")
        for idx in range(min(len(rows), config.table_no_break_max_lines)):
            utils.append_class(rows[idx], "pp_nobreak_after")
            utils.append_class(rows[-1 * (idx + 1)], "pp_nobreak_before")


# FIXME : we are loosing content here:
# the text property of the cell needs to be copied as well
def remove_single_cell_tables(root):
    for table in root.xpath("//table"):
        rows = table.xpath("./tr|./thead/tr|./tbody/tr|./tfoot/tr")
        if len(rows) == 1:
            cells = rows[0].getchildren()
            if len(cells) == 1:
                for item in cells[0]:
                    table.addprevious(item)
                table.getparent().remove(table)


def remove_style_sizes(root):
    for table in root.xpath("//table[@style]"):
        utils.remove_node_styles(table, ["width", "height"])
        utils.remove_node_width(table)
        if table.attrib.get("border"):
            del table.attrib["border"]
            utils.append_class(table, "pp_border_table")


def remove_styles_in_floats(root):
    for table in root.xpath('//table[contains(@class, "table_noCSS")]'):
        if table.attrib.get("style"):
            del table.attrib["style"]


def bold_tablenote_marker(root):
    """
    wrap tablenote indicators with <b> tags
    :param root:
    :return:
    """
    xpaths = [
        '//div[@class="pp-table"]/p[not(@class="pp-table-caption")]',
        '//p[@class="tablenote-details"]',
        '//p[@class="tablenote-details"]/br[following-sibling::text()]',
    ]
    for p in root.xpath("|".join(xpaths)):
        if p.tag == "br":
            if p.tail is not None and re.match(r"^\[[0-9a-z]+\]", p.tail.strip()):
                tablenote = p.tail.strip()
                reference_number = re.match(r"^\[[0-9a-z]+\]", tablenote).group(0)
                b = E.b(reference_number)
                b.tail = re.sub(r"^(\[[0-9a-z]+\])", r"", tablenote)
                p.tail = ""
                p.addnext(b)
        elif p.text and re.match(r"^\[[0-9a-z]+\]", p.text):
            node = E.p({"class": "tablenote-details"})
            reference_number = re.match(r"^\[[0-9a-z]+\]", p.text).group(0)
            b = E.b(reference_number)
            b.tail = re.sub(r"^(\[[0-9a-z]+\])", r"", p.text)
            node.insert(0, b)
            for n in p.getchildren():
                node.append(n)
            p.getparent().replace(p, node)


def markup_short_tables(root):
    for my_table in root.xpath("//table"):
        if 0 < len(my_table.xpath("descendant::tr")) < 20:
            utils.append_class(my_table, "short-table")


def remove_pullquote_margin_styles(root):
    for table in root.xpath('//table[contains(@class, "pullquote")]'):
        utils.remove_node_styles(table, "margin")


def markup_floated_tables(root):
    for my_table in root.xpath("//table"):
        styles = utils.get_node_style(my_table)
        if "float" in styles and styles["float"] == "right":
            utils.append_class(my_table, "right-floated-table")


def remove_styles(root):
    for my_table in root.xpath("//table"):
        utils.remove_node_styles(my_table, ["margin-left", "text-align"])

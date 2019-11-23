#!/usr/bin/env python

import hashlib
import re
from copy import deepcopy

from cssutils import parseStyle
from cssutils.css import CSSStyleDeclaration
from lxml import etree
from lxml.builder import ElementMaker
from tinycss2 import color3

from mwlib.pdf import utils
from mwlib.pdf.generators.cover import get_article_count

E = ElementMaker()


def parse(html_data):
    return etree.HTML(html_data)


def add_article_title(article):
    for node in article.dom.xpath("//article"):
        first_node = node.iterchildren().next()
        displaytitle = article.caption if hasattr(article, "caption") else article.title
        first_heading = E.h1(displaytitle)
        first_node.addprevious(first_heading)
        first_heading.append(hash_anchor(article.title))

        article_count = get_article_count(article.env.metabook.items)
        footer = E.div(
            {"class": "footer"},
            E.span(displaytitle, {"class": "title"}),
            E.span("Article {} of {}".format(article.idx, article_count), {"class": "counter"},),
        )
        first_heading.addnext(footer)


def hash_anchor(title):
    anchor = E.A(
        {
            "name": "article_{}".format(hashlib.md5(title.encode("utf-8")).hexdigest()),
            "class": "toc_entry",
        },
        "",
    )
    return anchor


def add_pagebreaks(root, article):
    if "page-break-before" in article:
        for xp in article["page-break-before"]:
            nodelist = root.xpath(xp)
            for node in nodelist:
                utils.append_class(node, "page-break-before")

    if "page-break-after" in article:
        for xp in article["page-break-after"]:
            nodelist = root.xpath(xp)
            for node in nodelist:
                utils.append_class(node, "page-break-after")

    return root


# def filter_content(root, article_num=1, title=''):
def filter_content(article):
    content_filter = [
        '//div[@id="mw-content-text"]',
        '//div[@id="bodyContent"]',
        "//body",
        "//",
    ]
    for query in content_filter:
        content = article.dom.xpath(query)
        if len(content) == 1:
            break
    assert len(content) == 1
    footer_text = _("{} | Article {} of {}").format(
        article.title, article.idx, len(article.env.metabook.items)
    )
    article_node = E.article(
        {
            "data-pp-article-num": str(article.idx),
            "id": "article{}".format(article.idx),
            "data-pp-footer-text": footer_text,
            "class": "pp-chapter",
        }
    )
    for node in content[0].getchildren():
        article_node.append(node)
    article.dom = E.html(E.head(E.meta({"charset": "utf-8"})), E.body(article_node))


def remove_nodes_and_content(root):
    query_shorthands = {
        "div": {
            "@class": [
                "magnify",
                "rellink",
                "printfooter",
                "dablink",
                "collapsed",
                "NavFrame",
                "mediaContainer",
                "metadata",
                "homonymie",
                "loupe",
                "bandeau",
            ],
            "@id": [
                "siteSub",
                "jump-to-nav",
                "catlinks",
                "normdaten",
                "disambig",
                "spoiler",  # https://sr.wikipedia.org/wiki/CY-208243
            ],
        },
        "table": {
            "@class": ["ambox", "metadata", "navbox", "navigatiesjabloon"],
            "@id": ["disambigbox", "commonscat"],
        },
        "span": {"@class": ["mw-editsection"], "@id": ["coordinates"]},
        "ul": {"@id": ["bandeau"], "@class": ["bandeau"]},
        "*": {
            "@class": [
                "noprint",
                "noexport",
                "hatnote navigation-not-searchable",
                "beginnetje",  # https://nl.wikipedia.org/wiki/Tafalisca_bogotensis
                "UitklapFrame",  # https://nl.wikipedia.org/wiki/Stoodleigh
                "navigation-only",  # https://fr.wikipedia.org/wiki/Villalval
                "vedlikehold",  # https://no.wikipedia.org/wiki/Santa_Teresinha
            ],
            "@id": ["tpl_Coordinaten", "toc",],  # https://nl.wikipedia.org/wiki/Aldeyjarfoss
        },
    }
    queries = []
    for node in query_shorthands:
        predicates = []
        for attr in query_shorthands[node]:
            for filter_attr_val in query_shorthands[node][attr]:
                predicates.append('contains({attr}, "{filter_attr_val}")'.format(**locals()))
        queries.append("//{node}[{pred}]".format(node=node, pred=" or ".join(predicates)))

    queries.extend(
        [
            '//table[.//tr[contains(@class, "navbox-title")]]',
            '//table[.//img[contains(@srcset, "Disambig-dark.svg")]]',
            '//table[.//img[contains(@srcset, "Exquisite-kfind.png")]]',
            '//tr[.//a[@title="Portaalicoon"]]',
            "//comment()",
            '//p[./span[@class="geo microformat"]][preceding-sibling::h1]',
            '//span[contains(@class, "haudio")]/parent::*',
        ]
    )
    for node in root.xpath("|".join(queries)):
        utils.remove_node(node)


def strip_tags(root):
    """strip tags but keep all content/text/tail"""
    tag_list = ["a"]
    etree.strip_tags(root, *tag_list)


def strip_attributes(root):
    attributes = [
        "cellpadding",
        "cellspacing",
        "align",
        "size",
        # https://uk.wikipedia.org/wiki/%D0%A1%D0%B0%D0%BD-%D0%91%D0%B0%D1%80%D1%82%D0%BE%D0%BB%D0%BE%D0%BC%D0%B5%D0%BE-%D0%92%D0%B0%D0%BB%D1%8C-%D0%9A%D0%B0%D0%B2%D0%B0%D1%80%D0%BD%D1%8C%D1%8F
        "border",
        "bgcolor",
        # https://en.wikipedia.org/wiki/Archery_at_the_1988_Summer_Olympics_%E2%80%93_Women%27s_individual
    ]
    xpath = "//*[{}]".format("|".join(["@" + attr for attr in attributes]))
    for node in root.xpath(xpath):
        for attr in attributes:
            if attr in node.attrib:
                del node.attrib[attr]
    for node in root.xpath("//*[not(self::td or self::th)]/@style"):
        if node.is_attribute:
            del node.getparent().attrib["style"]


def transform_width_and_height_attributes_to_style(root):
    attributes = ["width", "height"]
    for node in root.xpath("//*[{}]".format("|".join("@" + attr for attr in attributes))):
        for attr in attributes:
            if attr in node.attrib:
                value = node.get(attr)
                del node.attrib[attr]
                style = parseStyle(node.get("style"))
                if attr not in style.keys():
                    if value[-1:] == "%":
                        style.setProperty(attr, value)
                        node.attrib["style"] = ";".join([prop.cssText for prop in style])
                    elif value != "":
                        style.setProperty(attr, value + "px")
                        node.attrib["style"] = ";".join([prop.cssText for prop in style])


def strip_style_properties_except_width_and_height(root):
    """
    remove all style properties except for width and height
    scale px units to point units according to font relations:
      screen 12px --> print 8pt = 2/3
    :param root: dom tree
    :return:
    """
    scale_factor = 2 / 3.0
    unit = "pt"
    for node in root.xpath("//*[@style]"):
        old_style = parseStyle(node.get("style"))
        new_style = CSSStyleDeclaration()
        for p in old_style.getProperties("width", "height"):
            if p.value[-2:] == "px":
                value = str(scale_factor * float(re.sub(r"[^0-9.]", r"", p.value))) + unit
                new_style.setProperty(p.name, value)
        node.attrib["style"] = ";".join([prop.cssText for prop in new_style])


def grey_from_style_frag(frag):
    color = color3.parse_color(frag)
    if color is None:
        return frag
    else:
        grey = int(255 * color.red * 0.3 + 255 * color.green * 0.59 + 255 * color.blue * 0.11)
        return "rgb({g}, {g}, {g})".format(g=grey)


def convert_grayscale(root):
    for attr in ["color", "bgcolor"]:
        for node in root.xpath("//*[@{}]".format(attr)):
            node.set(attr, grey_from_style_frag(node.get(attr)))

    for node in root.xpath("//*[@style]"):
        new_style = []
        for style_frag in node.get("style", "").split(";"):
            if not style_frag.strip():
                continue
            try:
                attr, val = (s.strip() for s in style_frag.split(":"))
            except ValueError:
                continue
            if val == "transparent":
                continue
            new_val = map(grey_from_style_frag, val.split(" "))
            new_style.append(u"{attr}: {val}".format(attr=attr, val=u" ".join(new_val)))
        if new_style:
            node.set("style", "; ".join(new_style))


def add_soft_hyphens(root):
    # https://en.wikipedia.org/wiki/Arbutamine
    max_word_len = 50

    def handle_node_txt(node):
        for attr in ["text", "tail"]:
            txt = getattr(node, attr)
            if txt is None:
                continue
            words = txt.split(" ")
            found_long = False
            if txt:
                for i, word in enumerate(words):
                    word_len = len(word)
                    if word_len > max_word_len:
                        num_breaks = word_len / max_word_len
                        len_frag = word_len / (num_breaks + 1)
                        hyphenated = u"\u00ad".join(
                            [
                                word[frag_idx * len_frag : (frag_idx + 1) * len_frag]
                                for frag_idx in range(num_breaks + 1)
                            ]
                        )
                        words[i] = hyphenated
                        found_long = True
            if found_long:
                setattr(node, attr, " ".join(words))

    map(handle_node_txt, root.iterdescendants())


def remove_styles(root):
    styles = [
        "-moz-column-count",  # https://de.wikipedia.org/wiki/Decatur_County_%28Indiana%29
        "column-count",  # https://de.wikipedia.org/wiki/Decatur_County_%28Indiana%29
        "font",
        "font-size",
        "padding",  # https://en.wikipedia.org/wiki/A%26M_Records,_Inc._v._Napster,_Inc.
    ]

    _remove_styles = lambda node: utils.remove_node_styles(node, styles)

    predicate = " or ".join(['contains(@style, "{}")'.format(style) for style in styles])
    map(_remove_styles, root.xpath("//*[{}]".format(predicate)))


def clean(root):
    for node in root.xpath("//*[@_src]"):
        del node.attrib["_src"]


def remove_container(root):
    def has_siblings(node):
        return node.getnext() is not None or node.getprevious() is not None

    removable_container = ["div"]
    tags = [
        "ul",
        "ol",  # https://en.wikipedia.org/wiki/A-List_%28Conservative%29
        "table",  # https://en.wikipedia.org/wiki/Calosoma_striatius
    ]

    for node in root.xpath("|".join("//{}".format(tag) for tag in tags)):
        if has_siblings(node):
            continue
        check_node = node
        tails = []
        while not has_siblings(check_node) and (
            check_node.getparent().tag in removable_container or check_node == node
        ):
            tails.append(check_node.tail)
            check_node = check_node.getparent()
        if check_node != node:
            # FIXME move to domtools
            check_node.getparent().replace(check_node, node)
            node.tail = "".join(t for t in reversed(tails) if t)


def _combine_references(root):
    ref_nodes = root.xpath('//p[@class="pp_figure_ref"]')
    groups = []
    group = []
    for node in ref_nodes:
        if group:
            between = group[-1].getnext()
            if (
                between is not None
                and between.getnext() == node
                and between.tag == "div"
                and "pp_figure" in between.get("class")
            ):
                group.append(node)
            else:
                groups.append(group)
                group = [node]
        else:
            group.append(node)
    if group:
        groups.append(group)
    for group in groups:
        if len(group) == 1:
            continue
        txt = group[0].text + " - " + group[-1].text.strip().rsplit(" ", 1)[1]
        group[0].text = txt
        for node in group[1:]:
            utils.remove_node(node)


def add_figure_numbers(root):
    classes = [
        "pp_singlecol",
        # 'infobox',  # infoboxes are not referenced despite floating
        "pp_figure",
        "pp_twocol_span",
    ]
    pred = " or ".join('contains(@class, "{}")'.format(cls) for cls in classes)
    total_figures = 0
    for article in root.xpath("//article"):
        figure_num = 0
        for node in article.xpath(".//*[{}]".format(pred)):
            utils.remove_class(node, "infobox")
            figure_num += 1
            total_figures += 1
            cls = [c for c in classes if c in node.get("class")][0]
            nr = ".".join([article.get("pp_article_num"), str(figure_num)])
            caption_txt = "Figure {nr} ".format(nr=nr)
            reference = E.p({"class": "pp_figure_ref"}, u"\u21AA " + caption_txt)
            if cls == "pp_figure":
                caption = node.xpath('.//*[contains(@class, "thumbcaption")]')
                if caption:
                    node.addnext(reference)
                    caption = caption[0]
                    prefix = E.b(caption_txt)
                    caption.insert(0, prefix)
                    prefix.tail = caption.text
                    caption.text = None
                    utils.append_class(caption, "pp_figure_caption")
                    continue
            wrapper = utils.wrap_node(node, "div", {"class": cls})
            caption = E.div({"class": "pp_figure_caption"}, E.b(caption_txt))
            wrapper.append(caption)
            utils.remove_class(node, cls)
            wrapper.addnext(reference)
    _combine_references(root)


def move_caption(node):
    utils.append_class(node, "pp-table-caption")
    wrapper = E.div({"class": "pp-table"})
    try:
        node[0][0].text = node[0][0].text.replace(":", "")
        node[0].tail = ""
    except:
        print("Error at: " + etree.tostring(node))
    node_pos = node.getparent().index(node)
    nodelist = node.getparent().getchildren()
    indexpos = node_pos - 1
    while nodelist[indexpos].tag in ["p", "ul"]:
        if nodelist[indexpos].get("class") and "gallery" in nodelist[indexpos].get("class"):
            break
        else:
            indexpos -= 1
        # indexpos is the beef

    wrapper.append(node)
    if indexpos < 1:
        indexpos = 1
    nodelist[indexpos - 1].addnext(wrapper)
    for i in range(indexpos, node_pos):
        wrapper.append(nodelist[i])

    # add second caption to tables
    if wrapper[1].tag == "table":
        node2 = deepcopy(node)
        node2.tag = "caption"
        utils.append_class(node2, "following")
        wrapper[1].append(node2)


def apply_article_options(root, options=""):
    if "notext" in options:
        article = root.find(".//article")
        utils.append_class(article, "nodisplay")


def remove_figure_colon(root):
    for node in root.xpath(
        '//div[@class="thumbcaption"]/i[position()=1 and following-sibling::text()[starts-with(self::text(), ":") and position()=1]]'
    ):
        node.tail = ""


def rebuild_footnotes(root):
    for node in root.xpath('//sup[@class="reference"]'):
        p = re.compile(r"cite_ref-([A-Za-z0-9]+)_([0-9])-0")
        ref_id = p.sub(r"cite_note-\1-\2", node.get("id"))
        ref_nodes = root.xpath(
            '//ol[@class="references"]/li[@id="{}"]/span[@class="reference-text"]'.format(ref_id)
        )
        if len(ref_nodes) == 0:
            continue
        footnote = ref_nodes[0]
        footnote.text = footnote.text.strip()
        footnote.tail = node.tail
        parent = node.getparent()
        parent.insert(parent.index(node) + 1, footnote)
        parent.remove(node)

        # remove whitespace between footnote and last character
        if parent.text:
            parent.text = parent.text.rstrip()

    for node in root.xpath('//ol[@class="references"]'):
        utils.remove_node(node.getprevious())
        utils.remove_node(node)


def rewrite_links(root):
    for node in root.xpath("//a"):
        if node.get("href") and node.get("title"):
            link = "#article_{}".format(hashlib.md5(node.get("title").encode("utf-8")).hexdigest())
            node.set("href", link)


def markup_maps(root):
    target_node = "//div[{}]"
    conditions = [
        'contains(@class, "thumb")',
        'not(contains(@class, "thumbinner"))',
        'not(contains(@class, "thumbcaption"))',
        'not(contains(@class, "thumbimage"))',
        './/div[contains(@style, "relative") and .//div[contains(@style, "absolute")]]',
    ]
    '//div[@class="mw-parser-output"]//div[contains(@style, "relative") and .//div[contains(@style, "absolute")]]'
    for node in root.xpath(target_node.format(" and ".join(conditions))):
        utils.append_class(node, "map")

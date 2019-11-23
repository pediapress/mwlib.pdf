#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-

import hashlib

from lxml.builder import ElementMaker
from mwlib.log import Log

log = Log("mwlib.pdf.generators.contributors")
E = ElementMaker()


def generate_toc_list_item(title, displaytitle=None):
    if not displaytitle:
        displaytitle = title
    item = E.li()
    link_url = "#article_{}".format(hashlib.md5(title.encode("utf-8")).hexdigest())
    link = E.a(href=link_url)
    link.append(E.span(displaytitle, {"class": "article-title"}))
    item.append(link)
    return item


def generate_toc(env):
    items = env.metabook.items

    toc = E.article(id="table_of_contents")
    toc.append(E.h1(_("Contents")))

    if items[0].__class__.__name__ == "article":
        toc.append(E.h2(_("Articles")))

    start = 1
    article_toc = E.ol({"class": "contents", "start": str(start)})
    for item in items:
        if item.__class__.__name__ == "chapter":
            toc.append(article_toc)
            article_toc = E.ol({"class": "contents", "start": str(start)})
            toc.append(E.h2(item.title))
            for sub_item in item.items:
                article_toc.append(generate_toc_list_item(sub_item.title, sub_item.displaytitle))
                start += 1
            toc.append(article_toc)
            article_toc = E.ol({"class": "contents", "start": str(start)})
        else:
            article_toc.append(generate_toc_list_item(item.title, item.displaytitle))
            start += 1
    toc.append(article_toc)

    toc.append(E.h2(_("Appendix")))
    appendix_toc = E.ol({"class": "contents", "start": str(start)})
    appendix_toc.append(generate_toc_list_item(_("Article Sources and Contributors")))
    appendix_toc.append(generate_toc_list_item(_("Image Sources, Licenses and Contributors")))
    toc.append(appendix_toc)
    return toc

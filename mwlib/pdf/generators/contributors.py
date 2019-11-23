#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-

import re

from lxml.builder import ElementMaker
from mwlib.log import Log

from mwlib.pdf.htmlfilters.misc import hash_anchor

log = Log("mwlib.pdf.generators.contributors")
E = ElementMaker()


def generate_article_contributors(articles):
    title = _("Article Sources and Contributors")
    node = E.article(
        {"class": "contributors", "data-pp-footer-text": _("Appendix")},
        E.h1(title, hash_anchor(title)),
    )
    contributors = E.div({"class": ""})
    for article in articles:
        contributors.append(
            E.p(
                E.strong({"class": "title"}, article.title, " "),
                E.span({"class": "label"}, _("Source:"), " "),
                E.span({"class": "url"}, article.url, " "),
                E.span({"class": "label"}, _("Contributors:"), " "),
                E.span({"class": "contributors"}, filter_anon_ip_edits(article.authors),),
            )
        )
    node.append(contributors)
    return node


def generate_image_contributors(img_meta_info):
    title = _("Image Sources, Licenses and Contributors")
    node = E.article(
        {"class": "contributors", "data-pp-footer-text": _("Appendix")},
        E.h1(title, hash_anchor(title)),
    )
    contributors = E.div({"class": ""})
    for _id, title, url, license, authors, display, occurences in sorted(img_meta_info.values()):
        if not display:
            continue
        if not license:
            license = _("unknown")
        contributors.append(
            E.p(
                E.strong({"class": "title"}, title, " "),
                E.span({"class": "label"}, _("Source:"), " "),
                E.span({"class": "url"}, url, " "),
                E.span({"class": "label"}, _("License:"), " "),
                E.span({"class": "url"}, license, " "),
                E.span({"class": "label"}, _("Contributors:"), " "),
                E.span({"class": "contributors"}, filter_anon_ip_edits(authors), ", "),
                E.a(
                    {"class": "img_reference", "href": "#image_{}_{}".format(_id, occurences),},
                    _("see page"),
                ),
            )
        )
    node.append(contributors)
    return node


def filter_anon_ip_edits(authors):
    if authors:
        authors_text = ", ".join([a for a in authors if a != "ANONIPEDITS:0"])
        authors_text = re.sub(
            u"ANONIPEDITS:(?P<num>\d+)", u"\g<num> %s" % _(u"anonymous edits"), authors_text
        )
    else:
        authors_text = "-"
    return authors_text

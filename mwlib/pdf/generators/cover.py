import os

from lxml.builder import ElementMaker
from mwlib.log import Log
from pycountry import languages

log = Log("mwlib.pdf.generators.front_matter")
E = ElementMaker()


def generate_cover_page(env, lang):
    site_name = env.wiki.siteinfo["general"].get("sitename")
    title = env.metabook.title or _("Wiki Articles")
    subtitle = env.metabook.subtitle or _("A collection from {}".format(site_name))
    editor = env.metabook.editor or "ckepper"
    article_count = get_article_count(env.metabook.items)
    img_path = os.path.join(os.path.dirname(__file__), "..", "images")

    wikipedia_logo = E.img(
        {
            "src": "{}".format(os.path.join(img_path, "Wikipedia_wordmark.svg")),
            "class": "wikipedia_logo",
        }
    )
    pediapress_logo = E.img(
        {
            "src": "{}".format(os.path.join(img_path, "pediapress_square_bw.svg")),
            "class": "pediapress_logo",
        }
    )

    # title page
    title_page = E.section(
        {"id": "title_page"}, E.h1(title), E.h2(subtitle), E.div({"class": "horizontal-line"}),
    )
    info_line = E.ul({"class": "info_line"})
    if editor:
        info_line.append(E.li(_("Made by {}").format(editor)))
    if lang:
        info_line.append(E.li(languages.get(alpha_2=lang[:2]).name))
    info_line.append(E.li(_("{} articles").format(article_count)))
    info_line.append(E.li({"id": "total_pages"}, _(" pages")))
    title_page.append(info_line)
    title_page.append(wikipedia_logo)
    title_page.append(pediapress_logo)
    return title_page


def get_article_count(items):
    articles = 0
    for item in items:
        if item.__class__.__name__ == "chapter":
            articles += get_article_count(item.items)
        elif item.__class__.__name__ == "article":
            articles += 1
    return articles

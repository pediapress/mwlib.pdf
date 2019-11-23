from mwlib.log import Log

from .htmlfilters import filter_tree, misc

log = Log("mwlib.pdf.collection")


class Article(object):
    settings = dict(  # FIXME: that might need to be configurable on a per wiki base
        svg_image_scale_factor=1, pixel_image_scale_factor=1
    )

    def __init__(self, title="", html="", idx=1, env=None):
        self.title = title
        self.html = html
        self.idx = idx
        self.language = "en"  # FIXME
        self.env = env  # FIXME this is a shit interface
        self.dom = None

    def parse(self):
        filter_tree(self)
        return self.dom

    @classmethod
    def from_wiki_item(cls, item, env, idx):
        title = item.title
        data = item.wiki.getHTML(title, item.revision)
        try:
            html = data["text"]["*"]
        except KeyError:
            log.warning("Skipping missing article {}".format(title))
        article = cls(title=title, html=html, idx=idx, env=env)
        article.wiki = item.wiki
        article.url = article.wiki.getURL(item.title, item.revision)
        if item.displaytitle is not None:
            article.caption = item.displaytitle
        source = article.wiki.getSource(item.title, item.revision)
        if source:
            article.wiki_url = source.url or ""
        else:
            article.wiki_url = None
        article.authors = article.wiki.getAuthors(item.title, revision=item.revision)
        article.dom = misc.parse(article.html)
        return article

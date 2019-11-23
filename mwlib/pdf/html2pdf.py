#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gettext
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib

import lxml
import sass
from lxml import etree
from lxml.builder import ElementMaker
from mwlib.log import Log
from mwlib.writer.licensechecker import LicenseChecker

from . import htmlfilters
from . import linuxmem
from . import utils
from .collection import Article
from .config import gutter_width_pt, column_width_pt, page_margins
from .generators import contributors, table_of_contents, cover

log = Log("mwlib.pdf.html2pdf")

E = ElementMaker()
file_regex = re.compile(r"((File|Datei):[^?\n]*)")

current_dir = os.path.abspath(os.path.dirname(__file__))
css_dir = os.path.join(current_dir, "css")
scss_file = os.path.join(css_dir, "base.scss")
js_file = os.path.join(current_dir, "js", "base.js")


class PrincePdfWriter(object):
    boxid_regex = re.compile(".*? boxid: (?P<boxid>\d+)$")
    width_regex = re.compile("^msg\|out\|width: (?P<width>(\.|\d)+)$")
    height_regex = re.compile("^msg\|out\|height: (?P<height>(\.|\d)+)$")

    def __init__(
        self, env, out_fn, debug=False, crop_marks=False, lang="en",
    ):
        """
        Initialize HTML renderer
        :param env: environment with full metabook
        :param out_fn: output filename
        :param debug: debug mode
        :param crop_marks: render crop-marks
        """
        self.pdf_output_filename = out_fn
        self.lang = lang
        self.init_l10n(lang)
        self.crop_marks = crop_marks
        self.css_file = self._compile_sass()
        self.js_file = js_file
        self.debug = debug
        self.articles = []
        self.env = env
        if self.env is not None:
            self.book = self.env.metabook
            self.imgDB = env.images
            self.image_metadata = dict()
            self.img_count = 0

        try:
            strict_server = self.env.wiki.siteinfo["general"]["server"] in [u"//de.wikipedia.org"]
        except:
            strict_server = False
        if strict_server:
            self.license_checker = LicenseChecker(image_db=self.imgDB, filter_type="whitelist")
        else:
            self.license_checker = LicenseChecker(image_db=self.imgDB, filter_type="blacklist")
        self.license_checker.readLicensesCSV()

    def init_l10n(self, lang):
        log.info('Using "{}" for localization'.format(lang))
        localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "locale")
        translation = gettext.NullTranslations()
        if lang:
            try:
                translation = gettext.translation("mwlib.pdf", localedir, [lang])
            except IOError as exc:
                log.warn(str(exc))
        translation.install(unicode=True)

    def render_zip(self):
        """
        Renders Zip-File
        """
        start_time = time.time()
        filtered_html = []
        article_idx = 0

        # build Article List and DOM tree
        for n, item in enumerate(self.env.metabook.walk()):
            if item.type == "chapter":
                log.warning("chapter skipped")
                continue
            elif item.type == "article":
                article_idx += 1
                log.info("Article {}".format(item.title.encode("utf-8")))
                article = Article.from_wiki_item(item, self.env, article_idx)
                self._write_image_metadata(article.dom)
                self.articles.append(article)
                filtered_html.append(article.parse())
        root = self._render_front_matter()
        body = root.find("body")
        articles = E.section({"id": "articles"})
        for article_dom in filtered_html:
            for item in article_dom.find("body").getchildren():
                articles.append(item)
        body.append(articles)
        appendix = E.section({"id": "appendix"})
        appendix.append(contributors.generate_article_contributors(self.articles))
        appendix.append(contributors.generate_image_contributors(self.image_metadata))
        body.append(appendix)
        self._tag_nodes(root)

        # render DOM tree
        if self.debug:
            utils.append_class(root.find("body"), "debug")
            self._dump_html(root, "debug.html")

        # 1st render process
        render_log_filename = self._render_cmd(root, save_pdf_file=False)
        self._post_width_hook(root, render_log_filename)
        if self.debug:
            self._dump_html(root, "debug_final.html")
        # 2nd render process
        self._render_cmd(root, use_js=False)
        log.info(
            "rendering {} finished in {:.2f}".format(
                self.pdf_output_filename, time.time() - start_time
            )
        )

    def _render_cmd(self, root, save_pdf_file=True, use_js=True):
        """
        Render root tree with PrinceXML
        """
        mem_start = linuxmem.memory()
        pdf_filename = self.pdf_output_filename if save_pdf_file else os.devnull
        cmd = [
            "prince",
            "-",
            "-o",
            pdf_filename,
            "--media",
            "print",
            "-s",
            self.css_file,
            "--no-network",
            "--server",
        ]
        if use_js and self.js_file:
            cmd.extend(["--script", self.js_file])

        stdout_fd, stdout_filename = tempfile.mkstemp(prefix="render_out_", suffix=".log")
        log.info("running cmd: {} (stdout: {}) ".format(cmd, stdout_filename))
        p = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=stdout_fd, stderr=subprocess.STDOUT
        )
        p.communicate(utils.tree_to_string(root))
        mem_end = linuxmem.memory()
        log.info("MEMORY before {0:.2f}MB after {1:.2f}MB rendering".format(mem_start, mem_end))
        return stdout_filename

    def _post_width_hook(self, root, render_log_filename):
        """
        Resize elements based on box sizes determined in previous render process
        """
        self._parse_render_output(root, render_log_filename)
        htmlfilters.sizetools.fix_nested_widths(root)
        htmlfilters.sizetools.resize_tables(root)
        htmlfilters.sizetools.resize_overwide_tables(root)

    def _compile_sass(self):
        """
        compile css from scss
        """
        self._write_css_config()
        css_fn = os.path.splitext(scss_file)[0] + ".css"
        source_map_fn = css_fn + ".map"
        compiled_css, source_map = sass.compile(
            filename=scss_file, source_map_filename=source_map_fn
        )
        with open(css_fn, "w") as css_file:
            css_file.write(compiled_css)
        with open(source_map_fn, "w") as map_file:
            map_file.write(source_map)

        log.info("compiled sass {} -> {}".format(scss_file, css_fn))
        return css_fn

    def _write_css_config(self):
        with open(os.path.join(css_dir, "_config.scss"), "w") as fn:
            scss_config = [
                "$gutter-width: {}pt;".format(gutter_width_pt),
                "$base-column-width: {}pt;".format(column_width_pt),
                "@page {",
                "   size: a4;",
                "   margin: {};".format(" ".join([str(p) + "pt" for p in page_margins])),
                "   padding: 0;",
                "}",
            ]
            fn.write("\n".join(scss_config))

    def _dump_html(self, root, filename="debug.html"):
        """
        Dump HTML content of root tree into a file
        :param root: DOM-Tree of the document
        :param filename: output filename
        """
        head = root.xpath("//head")[0]
        head.append(E.link(rel="stylesheet", type="text/css", href=self.css_file))
        html_filename = os.path.join(os.path.dirname(self.pdf_output_filename), filename)
        with open(html_filename, "w") as f:
            f.write(utils.tree_to_string(root))
        log.info("wrote HTML {}".format(html_filename))

    def _render_front_matter(self):
        """
        Generate "front matter" pages
        """
        body = E.body()
        root = E.html(E.head(), body)
        if len(self.env.metabook.items) == 1:
            return root

        body.append(cover.generate_cover_page(self.env, self.lang))
        front_matter = E.section(id="front_matter")
        front_matter.append(table_of_contents.generate_toc(self.env))
        body.append(front_matter)
        return root

    def _convert_colorspace(self, colorspace=None):
        """
        Convert Colorspace to CMYK for Print Output
        :param colorspace:
        :return:
        """
        if colorspace == "cmyk":
            tmp_out_fn = tempfile.mkstemp(suffix=".pdf")[1]
            cmd = [
                "ps2pdf",
                "-sProcessColorModel=DeviceCMYK",
                "-dHaveTransparency=/false",
                "-sColorConversionStrategy=CMYK",
                "-dAutoRotatePages=/None",
                "-dPDFSETTINGS=/prepress",  # increase image quality
                self.pdf_output_filename,  # srce
                tmp_out_fn,  # target
            ]
            print("\n".join(["-" * 40, "CONVERTING TO CMYK", " ".join(cmd)]))
            ret = subprocess.call(cmd)
            if ret == 0:
                shutil.move(tmp_out_fn, self.pdf_output_filename)

    def _tag_nodes(self, root):
        for idx, node in enumerate(root.iter()):
            try:
                node.set("boxid", str(idx))
            except TypeError:
                if isinstance(node, lxml.etree._Comment):
                    pass
                else:
                    log.error("Setting boxid on node {} failed".format(node.tag))

    def _parse_render_output(self, root, render_log_filename):
        """
        add width and height in pt to root tree boxes based on render log
        """
        widths, heights = [], []
        id2width, id2height = {}, {}
        boxid = 0
        with open(render_log_filename) as f:
            for line in f:
                boxid_res = self.boxid_regex.match(line)
                if boxid_res:
                    boxid = int(boxid_res.group("boxid"))
                    if len(widths):
                        id2width[boxid - 1] = max(widths or [0])
                    if len(heights):
                        id2height[boxid - 1] = sum(heights or [0])
                    widths, heights = [], []
                width = self.width_regex.match(line)
                height = self.height_regex.match(line)
                if width:
                    width = float(width.group("width"))
                    widths.append(width)
                if height:
                    height = float(height.group("height"))
                    heights.append(height)
        id2width[boxid] = max(widths or [0])
        id2height[boxid] = sum(heights or [0])

        for node in root.iterdescendants():
            _id = int(node.get("boxid") or -1)
            if _id > -1:
                node.set("box_width", "{:.2f}".format(id2width.get(_id, 0)))
                node.set("box_height", "{:.2f}".format(id2height.get(_id, 0)))
                del node.attrib["boxid"]

    def _write_image_metadata(self, body):
        """
        write image metadata and tag images
        """
        for link in body.xpath("//a[img]"):
            img_name = link.attrib.get("title")
            if img_name is None or not self.imgDB.getContributors(img_name):
                match = file_regex.findall(link.attrib.get("href"))
                if not match:
                    continue
                img_name = urllib.unquote(match[0][0]).decode("utf-8")

            if not self.image_metadata.get(img_name):
                self.img_count += 1
                url = self.imgDB.getDescriptionURL(img_name) or self.imgDB.getURL(img_name)
                if url:
                    url = unicode(urllib.unquote(url.encode("utf-8")), "utf-8")
                else:
                    url = ""
                license_name = self.license_checker.getLicenseDisplayName(img_name)
                display = self.license_checker.displayImage(img_name)
                if not display:
                    log.debug("remove image {}".format(img_name))
                contributor_list = self.imgDB.getContributors(img_name)
                occurrences = 1
                self.image_metadata[img_name] = (
                    self.img_count,
                    img_name,
                    url,
                    license_name,
                    contributor_list,
                    display,
                    occurrences,
                )
            else:
                occurrences = self.image_metadata[img_name][6] + 1
                metadata = list(self.image_metadata[img_name])
                metadata[6] = occurrences
                self.image_metadata[img_name] = tuple(metadata)

            for img in link.iter("img"):
                if self.image_metadata[img_name][5] is False:
                    utils.append_class(img, "remove")
                img.getparent().attrib["name"] = "image_{}_{}".format(
                    self.image_metadata[img_name][0], occurrences
                )

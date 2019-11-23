#!/usr/bin/env python

import hashlib
import os
import re
import shutil
import subprocess
import tempfile

from PIL import Image
from lxml import etree
from mwlib.log import Log

from mwlib.pdf import utils

log = Log("mwlib.pdf.html2pdf")


def clean_tex(tex_src):
    tex_src = tex_src.lstrip().encode("utf-8")  # mwlib
    return " " + tex_src + " "


def clean_math_source(self, node):
    color = False
    source = node.caption
    source = re.compile("\n+").sub("\n", source.strip())
    if not color:  # remove color for b&w books
        source = re.compile("\\\\color\{.*?\}").sub("", source)
    source = " " + source + " "
    cmd = ["texvc_tex", source.encode("utf-8")]

    try:
        sub = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except OSError:
        print "error with texvc_tex. cmd:", cmd
        return None
    (source, error) = sub.communicate()
    source = re.compile(" +").sub(" ", source)
    parmodeTags = ["align", "alignat"]  # tags that force switch to paragraph and not math mode
    parmodeTag = None
    for pt in parmodeTags:
        if source.find("begin{%s}" % pt) > -1:
            parmodeTag = pt
    if parmodeTag is not None:
        source = source.replace("begin{%s}" % parmodeTag, "begin{%s*}" % parmodeTag)
        source = source.replace("end{%s}" % parmodeTag, "end{%s*}" % parmodeTag)
        return source
    else:
        return "$" + source + " $"


def extract_tex(node):
    tex_src = node.get("alt")
    return clean_tex(tex_src)


def iter_math(root):
    for math_img in root.xpath(
        '//img[@class="tex"]|//img[@class="mwe-math-fallback-image-inline"]'
    ):
        yield math_img, extract_tex(math_img)


def math_img_size(node):
    img = Image.open(node.get("src"))
    return img.size


def transform2mathml(root):
    for math_node, tex_src in iter_math(root):
        cmd = ["blahtex", "--texvc-compatible-commands", "--mathml"]
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE
        )

        (result, error) = p.communicate(tex_src)
        try:
            math = etree.HTML(result)
        except etree.XMLSyntaxError:
            log.error("Math conversion failed for src: {}".format(etree.tostring(math)))
            print "ERROR: math conversion failed"
            return
        math_ml = math.xpath(".//mathml/markup")
        if len(math_ml) > 0:
            math_ml = math_ml[0]
        else:
            log.error("Math empty after conversion. src: {}".format(etree.tostring(math)))
            return
        math_ml.tag = "math"
        math_node.getparent().replace(math_node, math_ml)


def transform2svg(root):
    math_form_dir = os.path.join(os.getcwd(), "math_formulas")
    if not os.path.exists(math_form_dir):
        os.makedirs(math_form_dir)
    cur_dir = os.getcwd()
    for math_node, tex_src in iter_math(root):
        tex_src = tex_src.replace(r"\definecolor{bggrey}{RGB}{234,234,234}\pagecolor{bggrey}", "")
        tex_src = tex_src.replace(r"\definecolor{bgblue}{RGB}{65,193,232}\pagecolor{bgblue}", "")

        for ancestor in math_node.iterancestors():
            if ancestor.tag == "th":
                tex_src = r"\color{white}" + tex_src

        fn = hashlib.md5(tex_src).hexdigest()

        # exit if file exists
        if not os.path.isfile(os.path.join(math_form_dir, fn + ".svg")):
            tex_doc = "\n".join(
                [
                    r"\nonstopmode",
                    r"\documentclass{article}",
                    r"\usepackage{cancel}",
                    r"\usepackage{amsmath}",
                    r"\usepackage{color}" r"\usepackage{amssymb}",
                    r"\usepackage{amsthm}",
                    r"\pagestyle{empty}",
                    r"\begin{document}",
                    r"\begin{math}",
                    r"{}".format(tex_src),
                    r"\end{math}",
                    r"\end{document}",
                ]
            )

            tempdir = tempfile.mkdtemp()
            os.chdir(tempdir)
            with open(os.path.join(tempdir, fn + ".tex"), "w") as f:
                f.write(tex_doc)
            p = subprocess.Popen(
                ["xelatex", "-interaction", "batchmode", "-no-pdf", fn + ".tex"],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            (result, error) = p.communicate()
            if not error:
                p = subprocess.Popen(
                    ["dvisvgm", "--exact", "--no-fonts", fn + ".xdv"],
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                (result, error) = p.communicate()
                shutil.move(fn + ".svg", math_form_dir)
            os.chdir(cur_dir)
            if os.path.isdir(tempdir):
                shutil.rmtree(tempdir)

        math_file = os.path.relpath(os.path.join(math_form_dir, fn + ".svg"))
        if os.name == "nt":
            math_file = math_file.replace("\\", "/")
        math_node.set("src", math_file)


def remove_mathml(root):
    results = root.xpath("//math")
    for node in results:
        utils.remove_node(node)

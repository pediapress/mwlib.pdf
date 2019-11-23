#! /usr/bin/env python

import locale
import os
import sys
import traceback

from mwlib.log import Log

import mwlib
from mwlib.pdf import html2pdf

reload(sys)
sys.setdefaultencoding("UTF8")
log = Log("mwlib.pdf.writer")


def patch_logging(output_filename):
    fn = os.path.join(os.path.dirname(output_filename), "render.log")
    mwlib.utils.start_logging(fn)


def writer(env, output, status_callback, debug=True, lang=None, x=False):
    if not lang:
        _locale = locale.getlocale(locale.LC_NUMERIC)
        if _locale:
            lang = _locale[0]
    crop_marks = False
    if not x:
        patch_logging(output)
    renderer = html2pdf.PrincePdfWriter(env, output, debug=debug, crop_marks=crop_marks, lang=lang)

    try:
        renderer.render_zip()
    except Exception:
        traceback.print_exc()
    else:
        log.info("rendering {} finished".format(output))


writer.description = "HTML writer"
writer.content_type = "application/pdf"
writer.file_extension = "pdf"

writer.options = {
    "lang": {"help": "language of book and its containing text", "param": "LANG"},
    "debug": {"help": "turn debug mode on",},
    "x": {"help": "turn off forced file logging"},
}

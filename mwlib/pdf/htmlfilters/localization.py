#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-


def body_add_localized_strings(root, localized_strings):
    if localized_strings is not None:
        for body in root.xpath("//body"):
            for key, value in localized_strings.iteritems():
                body.attrib["data-" + key] = value

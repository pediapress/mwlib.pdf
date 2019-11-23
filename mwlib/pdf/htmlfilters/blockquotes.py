#!/usr/bin/env python


def only_bq_siblings(node):
    siblings = []
    for flag in [True, False]:
        for sib in node.itersiblings(preceding=flag):
            if sib.tag == "blockquote":
                siblings.append(sib)
            else:
                return False
    return siblings


def remove_container(root):
    for bq in root.xpath("//blockquote[not(ancestor::table)]"):
        while True:
            siblings = only_bq_siblings(bq)
            if siblings is False:
                break
            siblings.append(bq)
            parent = bq.getparent()
            greatparent = parent.getparent()
            if len(siblings) == 1:
                greatparent.replace(parent, siblings[0])
            else:
                for sib in siblings:
                    parent.addnext(sib)
                greatparent.remove(parent)

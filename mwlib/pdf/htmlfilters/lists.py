#!/usr/bin/env python


def mark_inline(root):
    pred = "[not(ancestor::ul|ancestor::ol|ancestor::table)]"
    lsts = root.xpath("//ul{pred}|//ol{pred}".format(pred=pred))
    for lst in lsts:
        cls = lst.get("class", "")
        lst.set("class", "pp_compact_lst " + cls)


def merge_single_element_lists(root):
    def next_mergeable(lst):
        nxt = lst.getnext()
        return nxt is not None and nxt.tag == lst.tag and len(nxt.getchildren()) == 1

    for lst in root.xpath("//ul|//ol"):
        if len(lst.getchildren()) != 1:
            continue
        while next_mergeable(lst):
            nxt = lst.getnext()
            lst.append(nxt.getchildren()[0])
            nxt.getparent().remove(nxt)

#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-


def render_table_row_permutations(root):
    table = root.xpath(".//table")[0]
    body = root.xpath(".//body")[0]

    for row_idx, row in enumerate(table.getiterator(tag="tr")):
        copy_table = table.__copy__()
        for idx, row in enumerate(copy_table.getiterator(tag="tr")):
            if idx == row_idx:
                row.getparent().remove(row)
                break
        body.append(copy_table)

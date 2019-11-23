#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-
from collections import OrderedDict

em2px = 7.2  # 1em = 16px for regular font size. 45% font-size -> 7.2
CSS_DPI = 96.0
PPI = 72.0
IN_2_CM = 2.54
in2cm = 2.54
cm2in = 1 / 2.54
cm2px = 1 / cm2in * 96
px2pt = 72.0 / 96.0
pt2px = 96 / 72.0
px2in = 1 / 96.0
pt2mm = 25.4 / 72.0

page_width_pt = 595
page_height_pt = 842

column_count = 12

gutter_width_pt = 16.0

page_margins = [40, 40, 60, 40]

column_width_pt = (
    (page_width_pt - page_margins[1] - page_margins[3]) - (column_count - 1) * gutter_width_pt
) / column_count

columns = OrderedDict()
for number in range(column_count):
    columns["col-{}".format(number + 1)] = (
        column_width_pt * (number + 1) + gutter_width_pt * number
    )

tolerated_over_width = columns["col-{}".format(column_count)] * 1.1

h_tags = lambda low, high: ["h{}".format(i) for i in range(low, high + 1)]


table_no_break_max_lines = 3

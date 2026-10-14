# -*- coding: utf-8 -*-
t = open("_live_page_1012.html", encoding="utf-8", errors="replace").read()
print(t[:1000])
print("----MIDDLE----")
print(t[60000:61500])
print("----TRADE SEARCH----")
import re
for needle in ["MASTER TRADE", "apexTradeTable", "FUTURES INTELLIGENCE", "/ES", "E-Mini"]:
    print(needle, "count:", t.count(needle))

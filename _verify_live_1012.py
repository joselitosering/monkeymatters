# -*- coding: utf-8 -*-
import re
t = open("_live_page_1012.html", encoding="utf-8", errors="replace").read()
print("length:", len(t))
visible = re.sub(r"<!--.*?-->", "", t, flags=re.DOTALL)
stray = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", visible)))
print("stray tokens:", stray)
print("PENDING in visible:", "PENDING" in visible)

checks = [
    "SPX cash (FMP, live)",
    "Schwab refresh token stale",
    "Columbus Day",
    "EPS Est. $5.93",
    "GTCR/Elliott",
    "Record call volume hit TLT",
    "MIXED — INDEX STRENGTH",
]
for c in checks:
    print(repr(c), "->", "FOUND" if c in t else "MISSING")

i = t.find('id="apexTradeTable"')
print(t[i:i+200] if i != -1 else "trade table id not found")
tbody_i = t.find("<tbody>", i)
print(t[tbody_i:tbody_i+400])

# -*- coding: utf-8 -*-
ROOT = r"D:\Apps\DevOps\Github\monkeymatters"
with open(ROOT + r"\_sim_rendered.html", encoding="utf-8") as f:
    html = f.read()

out = open(ROOT + r"\_spotcheck_log.txt", "w", encoding="utf-8")

for needle in (
    "Schwab's /ES futures feed returned",
    "Schwab's /NQ futures feed failed",
    "Gap vs Settle",
    "E-Mini S&amp;P 500",
    "E-Mini Nasdaq-100",
    "MASTER TRADE IDEAS",
    "apexTradeTable",
):
    idx = html.find(needle)
    out.write("FIND %r -> idx=%d\n" % (needle, idx))
    if idx != -1:
        out.write("  CTX: %r\n\n" % html[max(0, idx-150):idx+300])

out.close()
print("done")

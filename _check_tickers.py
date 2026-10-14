# -*- coding: utf-8 -*-
ROOT = r"D:\Apps\DevOps\Github\monkeymatters"
with open(ROOT + r"\_live_page_1007.html", encoding="utf-8") as f:
    html = f.read()

tickers = ["MAT</strong>", "SWKS</strong>", "FLUT</strong>", "STZ</strong>",
           "CAT</strong>", ">DE</strong>", "Worthington Steel", ">PR</strong>",
           "GOLD (GC)</strong>", ">TLT</strong>", ">BTC</strong>", ">QQQ</strong>",
           "Russell 2000)</strong>"]

out = open(ROOT + r"\_check_tickers_out.txt", "w", encoding="utf-8")
for t in tickers:
    out.write("%s -> %d\n" % (t, html.count(t)))
out.close()
print("done")

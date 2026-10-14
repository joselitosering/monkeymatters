# -*- coding: utf-8 -*-
import re

ROOT = r"D:\Apps\DevOps\Github\monkeymatters"

with open(ROOT + r"\_live_page_1007.html", encoding="utf-8") as f:
    html = f.read()

out = open(ROOT + r"\_verify_live_1007_log.txt", "w", encoding="utf-8")
out.write("HTML length: %d\n" % len(html))

visible = re.sub(r"<!--.*?-->", "", html, flags=re.S)

stray_tokens = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", visible)))
out.write("STRAY TOKENS IN VISIBLE CONTENT (%d unique): %s\n" % (len(stray_tokens), stray_tokens))

pending_count = visible.count("PENDING")
out.write("PENDING occurrences in visible content: %d\n" % pending_count)

checks = [
    "7,801.77",
    "27,538.69",
    "5.300%",
    "third consecutive session",
    "third straight session",
    "80.3% foreign",
    "Worthington Steel",
    "3,283",
    "Levi Strauss",
    "PepsiCo",
]
for c in checks:
    out.write("CHECK %r -> count=%d\n" % (c, visible.count(c)))

# Trade table row count
trade_rows = html.count('class="t-pri"')
out.write("Trade rows (t-pri count): %d\n" % trade_rows)

out.close()
print("DONE")

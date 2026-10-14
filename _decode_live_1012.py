# -*- coding: utf-8 -*-
import base64, re
b64 = open("_live_page_1012_b64.txt", encoding="ascii").read().strip().replace("\n", "")
raw = base64.b64decode(b64)
t = raw.decode("utf-8")
open("_live_page_1012_clean.html", "w", encoding="utf-8").write(t)
print("decoded length:", len(t))

visible = re.sub(r"<!--.*?-->", "", t, flags=re.DOTALL)
stray = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", visible)))
print("stray tokens:", stray)
print("PENDING in visible:", "PENDING" in visible)

checks = [
    "MIXED — INDEX STRENGTH",
    "HOUTHI ESCALATION RISK — OIL/MIDEAST",
    "SPX cash (FMP, live)",
    "Schwab refresh token stale",
    "N/A — Schwab feed down",
    "Joe’s live OAuth",
    "EPS Est. $5.93",
    "GTCR/Elliott",
]
for c in checks:
    print(repr(c), "->", "FOUND" if c in t else "MISSING")

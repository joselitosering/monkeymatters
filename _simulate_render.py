# -*- coding: utf-8 -*-
import sys
import json
import datetime
import re

ROOT = r"D:\Apps\DevOps\Github\monkeymatters"
sys.path.insert(0, ROOT + r"\scripts")

import fetch_mmm_data as fmd  # noqa: E402

with open(ROOT + r"\data\daily\2026-10-06.json", encoding="utf-8") as f:
    data = json.load(f)

with open(ROOT + r"\data\daily\2026-10-06.insert.json", encoding="utf-8") as f:
    insert = json.load(f)

with open(ROOT + r"\template\mmm_template.html", encoding="utf-8") as f:
    template = f.read()

quotes = data["quotes"]
schwab = data["schwab_futures"]

kpi = fmd.build_kpi_tokens(quotes, schwab)

now = datetime.datetime.now()
html = fmd.render(template, now, kpi, insert, schwab)

out = open(ROOT + r"\_sim_render_log.txt", "w", encoding="utf-8")
out.write("HTML length: %d\n" % len(html))

try:
    fmd.validate(html)
    out.write("validate(): PASSED\n")
except Exception as e:
    out.write("validate(): FAILED: %s\n" % e)

# Strip HTML comments to check only VISIBLE content for stray tokens / PENDING
visible = re.sub(r"<!--.*?-->", "", html, flags=re.S)

stray_tokens = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", visible)))
out.write("STRAY TOKENS IN VISIBLE CONTENT (%d unique): %s\n" % (len(stray_tokens), stray_tokens))

pending_count = visible.count("PENDING")
out.write("PENDING occurrences in visible content: %d\n" % pending_count)
if pending_count:
    for m in re.finditer("PENDING", visible):
        s = max(0, m.start() - 80)
        e = min(len(visible), m.start() + 80)
        out.write("  CTX: %r\n" % visible[s:e])

# Save rendered html for inspection / later diff
with open(ROOT + r"\_sim_rendered.html", "w", encoding="utf-8") as f:
    f.write(html)

out.close()
print("SIM DONE")

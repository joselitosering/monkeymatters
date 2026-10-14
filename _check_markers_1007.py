# -*- coding: utf-8 -*-
import json
import sys

ROOT = r"D:\Apps\DevOps\Github\monkeymatters"

with open(ROOT + r"\template\mmm_template.html", encoding="utf-8") as f:
    template = f.read()

with open(ROOT + r"\data\daily\2026-10-07.insert.json", encoding="utf-8") as f:
    insert = json.load(f)

sections = insert["INJECTED_SECTIONS"]
out = open(ROOT + r"\_check_markers_1007_out.txt", "w", encoding="utf-8")
out.write("Total markers: %d\n" % len(sections))
bad = 0
for i, marker in enumerate(sections.keys()):
    c = template.count(marker)
    status = "OK" if c == 1 else "FAIL"
    if c != 1:
        bad += 1
    out.write("%d %s count=%d %r\n" % (i, status, c, marker[:60]))
out.write("BAD MARKERS: %d\n" % bad)
out.close()
print("DONE, bad=", bad)

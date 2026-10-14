# -*- coding: utf-8 -*-
import re
import subprocess

ROOT = r"D:\Apps\DevOps\Github\monkeymatters"

result = subprocess.run(
    ["gh", "api", "repos/joselitosering/monkeymatters/contents/shadowmonkey/mmm-daily/2026-10-06.html",
     "-H", "Accept: application/vnd.github.raw"],
    cwd=ROOT, capture_output=True,
)
html = result.stdout.decode("utf-8")

out = open(ROOT + r"\_verify_live_log.txt", "w", encoding="utf-8")
out.write("returncode: %d stderr: %s\n" % (result.returncode, result.stderr.decode("utf-8", "replace")[:500]))
out.write("LENGTH: %d\n" % len(html))
out.write("startswith DOCTYPE: %s\n" % html.startswith("<!DOCTYPE html>"))

visible = re.sub(r"<!--.*?-->", "", html, flags=re.S)
stray = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", visible)))
out.write("STRAY TOKENS (%d): %s\n" % (len(stray), stray))
out.write("PENDING count: %d\n" % visible.count("PENDING"))

m = re.search(r'<tbody>(.*?)</tbody>', html, re.S)
tbody = m.group(1) if m else ""
out.write("TRADE ROWS <tr> count: %d\n" % tbody.count("<tr>"))

for label, needle in (
    ("ES_CA", "Schwab's /ES futures feed returned"),
    ("NQ_CA", "Schwab's /NQ futures feed failed"),
    ("ECON_CA", "Today's own calendar is thin"),
    ("EARNINGS_CA", "A genuinely quiet single-name day"),
):
    out.write("%s present: %s\n" % (label, needle in html))

with open(ROOT + r"\_live_page_clean.html", "w", encoding="utf-8") as f2:
    f2.write(html)

out.close()
print("done")

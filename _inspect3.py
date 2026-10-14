import re

path = r"D:\Apps\DevOps\Github\monkeymatters\template\mmm_template.html"
with open(path, encoding="utf-8") as f:
    t = f.read()

out = open(r"D:\Apps\DevOps\Github\monkeymatters\_inspect3_out.txt", "w", encoding="utf-8")

# Find the /ES card-hd marker
idx = t.find('card-hd">')
# find all card-hd occurrences containing "/ES" or "/NQ"
for m in re.finditer(r'<div class="card-hd">[^<]*?(/ES|/NQ)[^<]*?</div>', t):
    out.write("CARD-HD MATCH: %r at %d\n" % (m.group(0), m.start()))

out.write("\n\n")

# Now find full block from card-hd through end of its .ca div, for /ES and /NQ
for label in ("/ES", "/NQ"):
    pattern = re.compile(r'<div class="card-hd">[^<]*?' + re.escape(label) + r'[^<]*?</div>')
    m = pattern.search(t)
    start = m.start()
    # find the next '<div class="ca">' after start, then find its matching close by counting divs
    ca_start = t.find('<div class="ca">', start)
    # walk forward counting div open/close tags to find matching close for this div
    depth = 0
    i = ca_start
    tag_re = re.compile(r'<div\b[^>]*>|</div>')
    pos = ca_start
    end = None
    for tm in tag_re.finditer(t, ca_start):
        tag = tm.group(0)
        if tag.startswith('</div>'):
            depth -= 1
        else:
            depth += 1
        if depth == 0:
            end = tm.end()
            break
    block = t[start:end]
    out.write("=" * 40 + " BLOCK FOR %s " % label + "=" * 40 + "\n")
    out.write("start=%d end=%d length=%d\n" % (start, end, len(block)))
    out.write("COUNT IN TEMPLATE: %d\n" % t.count(block))
    out.write(block)
    out.write("\n\n")

out.close()
print("done")

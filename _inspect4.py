import re

path = r"D:\Apps\DevOps\Github\monkeymatters\template\mmm_template.html"
with open(path, encoding="utf-8") as f:
    t = f.read()

out = open(r"D:\Apps\DevOps\Github\monkeymatters\_inspect4_out.txt", "w", encoding="utf-8")

# search for any comment containing "trade" case-insensitively
for m in re.finditer(r'<!--.*?-->', t, re.DOTALL):
    s = m.group(0)
    if 'trade' in s.lower() or 'trd' in s.lower():
        out.write("COMMENT: %r at %d count=%d\n\n" % (s, m.start(), t.count(s)))

# also search for table classes that might hold trade ideas
for m in re.finditer(r'<table[^>]*class="[^"]*"', t):
    out.write("TABLE: %r at %d\n" % (m.group(0), m.start()))

out.write("\n\n")
# search raw occurrences of word 'trade' (case-insens) with context
for m in re.finditer(r'trade', t, re.IGNORECASE):
    s = max(0, m.start()-60)
    e = min(len(t), m.start()+60)
    out.write("CTX @%d: %r\n" % (m.start(), t[s:e]))

out.close()
print("done")

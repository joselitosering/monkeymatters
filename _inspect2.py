import re

path = r"D:\Apps\DevOps\Github\monkeymatters\template\mmm_template.html"
with open(path, encoding="utf-8") as f:
    t = f.read()

out = open(r"D:\Apps\DevOps\Github\monkeymatters\_inspect2_out.txt", "w", encoding="utf-8")

for m in re.finditer(r'class="ca"', t):
    start = max(0, m.start() - 400)
    end = min(len(t), m.start() + 2200)
    out.write("=" * 80 + "\n")
    out.write("MATCH AT %d\n" % m.start())
    out.write(t[start:end])
    out.write("\n\n")

out.close()
print("done")

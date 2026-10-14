import re

path = r"D:\Apps\DevOps\Github\monkeymatters\template\mmm_template.html"
with open(path, encoding="utf-8") as f:
    t = f.read()

print("TEMPLATE LENGTH:", len(t))
print()

# Find all INJECT comments
for m in re.finditer(r"<!--\s*INJECT:.*?-->", t, re.DOTALL):
    s = m.group(0)
    print(repr(s))
    print("COUNT:", t.count(s))
    print("---")

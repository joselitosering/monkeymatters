import json

for name in ("_content.json", "_injected_content.json"):
    path = r"D:\Apps\DevOps\Github\monkeymatters\%s" % name
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    print(name, "OK", len(d), "keys:", list(d.keys()))

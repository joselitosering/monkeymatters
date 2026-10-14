# -*- coding: utf-8 -*-
import json, re
from pathlib import Path

ROOT = Path(r"D:\Apps\DevOps\Github\monkeymatters")
tpl = (ROOT / "template" / "mmm_template.html").read_text(encoding="utf-8")
data = json.loads((ROOT / "data" / "daily" / "2026-10-12.insert.json").read_text(encoding="utf-8"))

injected = data.pop("INJECTED_SECTIONS")
rendered = tpl
for marker, repl in injected.items():
    cnt = rendered.count(marker)
    if cnt != 1:
        raise SystemExit(f"MARKER COUNT {cnt} (expected 1) for marker starting: {marker[:70]!r}")
    rendered = rendered.replace(marker, repl)

for key, val in data.items():
    tok = "{{%s}}" % key
    rendered = rendered.replace(tok, str(val))

# Strip HTML comments to check only VISIBLE content
visible = re.sub(r"<!--.*?-->", "", rendered, flags=re.DOTALL)

stray_tokens = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", visible)))
pending = "PENDING" in visible

print("rendered length:", len(rendered))
print("stray {{TOKENS}} in visible content:", stray_tokens)
print("PENDING present in visible content:", pending)

out = ROOT / "_sim_rendered_1012.html"
out.write_text(rendered, encoding="utf-8")
print("wrote", out)

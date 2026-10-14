# -*- coding: utf-8 -*-
import json
import re

ROOT = r"D:\Apps\DevOps\Github\monkeymatters"
TEMPLATE_PATH = ROOT + r"\template\mmm_template.html"
CONTENT_PATH = ROOT + r"\_content.json"
INJ_PATH = ROOT + r"\_injected_content.json"
OUT_PATH = ROOT + r"\data\daily\2026-10-06.insert.json"
LOG_PATH = ROOT + r"\_build_insert_log.txt"

log = open(LOG_PATH, "w", encoding="utf-8")


def say(*a):
    s = " ".join(str(x) for x in a)
    log.write(s + "\n")


with open(TEMPLATE_PATH, encoding="utf-8") as f:
    template = f.read()

with open(CONTENT_PATH, encoding="utf-8") as f:
    content = json.load(f)["top_level"]

with open(INJ_PATH, encoding="utf-8") as f:
    inj = json.load(f)

sections = {}
errors = []


def require_unique(marker, label):
    n = template.count(marker)
    if n != 1:
        errors.append("MARKER NOT UNIQUE (%d occurrences): %s -- %r" % (n, label, marker[:120]))
        say("FAIL", label, "count=", n)
    else:
        say("OK", label, "count=1 len=", len(marker))
    return marker


def find_balanced_div(text, start_idx):
    tag_re = re.compile(r"<div\b[^>]*>|</div>")
    depth = 0
    end = None
    for tm in tag_re.finditer(text, start_idx):
        tag = tm.group(0)
        if tag.startswith("</div>"):
            depth -= 1
        else:
            depth += 1
        if depth == 0:
            end = tm.end()
            break
    return end


# Only comments that are themselves an actual INJECT directive (the big
# documentation header comment at the top of the file also mentions these
# keywords in prose, so we require the comment to START with "<!-- INJECT:").
all_comments = list(re.finditer(r"<!--.*?-->", template, re.DOTALL))
real_injects = [m for m in all_comments if m.group(0).lstrip().startswith("<!-- INJECT:")]
say("real INJECT comments found:", len(real_injects))
for m in real_injects:
    say("  @", m.start(), repr(m.group(0)[:70]))


# ---- 1. Simple INJECT-comment markers (whole comment replaced by rows) ----
simple_map = {
    "BBM SIGNAL ROWS": "BBM_ROWS",
    "INJECT: ALERTS": "ALERTS",
    "INJECT: EVENTS": "EVENTS",
    "INJECT: ACTIONABLES": "ACTIONABLES",
    "REGIME DETAILS": "REGIME_DETAILS",
    "INJECT: SECTORS": "SECTORS",
    "INJECT: SPOTLIGHT": "SPOTLIGHT",
    "OPTIONS IDEAS": "OPTIONS_IDEAS",
    "INJECT: MONEY FLOW": "MONEY_FLOW",
    "UNUSUAL OPTIONS": "UNUSUAL_OPTIONS",
    "S06 ECON CALENDAR": "ECON_CALENDAR_ROWS",
    "S06 EARNINGS WATCH": "EARNINGS_ROWS",
    "S07 GAINERS": "GAINERS_ROWS",
    "S07 DECLINERS": "DECLINERS_ROWS",
}

econ_comment = None
earnings_comment = None

for keyword, content_key in simple_map.items():
    matches = [m for m in real_injects if keyword in m.group(0)]
    if len(matches) != 1:
        errors.append("KEYWORD MATCH COUNT != 1 for %s: found %d" % (keyword, len(matches)))
        say("FAIL keyword", keyword, "matches=", len(matches))
        continue
    marker = matches[0].group(0)
    require_unique(marker, content_key)
    sections[marker] = inj[content_key]
    if keyword == "S06 ECON CALENDAR":
        econ_comment = matches[0]
    if keyword == "S06 EARNINGS WATCH":
        earnings_comment = matches[0]

# ---- 2. TRADE_ROWS (the 20-row master trade table comment) ----
trade_marker = "<!-- INJECT UP TO 20 TRADE ROWS. Column order: #, Symbol, Type, Direction, Setup, Entry, Stop, Target, R:R, Notes, Priority -->"
require_unique(trade_marker, "TRADE_ROWS")
sections[trade_marker] = inj["TRADE_ROWS"]

say("Simple + trade markers done. sections so far:", len(sections))


# ---- 3. /ES and /NQ big blocks (card-hd through end of that card's .ca div) ----
def extract_card_block(label):
    pat = re.compile(r'<div class="card-hd">[^<]*?' + re.escape(label) + r'[^<]*?</div>')
    m = pat.search(template)
    if not m:
        errors.append("CARD-HD NOT FOUND for %s" % label)
        return None
    start = m.start()
    ca_start = template.find('<div class="ca">', start)
    end = find_balanced_div(template, ca_start)
    return template[start:end]


def fill_tokens(block, values):
    out = block
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


for label, content_key in (("/ES", "ES_CA"), ("/NQ", "NQ_CA")):
    block = extract_card_block(label)
    if block is None:
        continue
    require_unique(block, content_key + " (full card block)")
    vals = inj[content_key]
    filled = fill_tokens(block, vals)
    sections[block] = filled
    say(label, "block len=", len(block), "filled len=", len(filled))

# ---- 4. Econ Calendar + Earnings Watch bare .ca divs (anchored to the real
#         INJECT comment position found above, not a generic text search,
#         since the keyword text also appears in the top-of-file header). ----
def extract_ca_after(comment_match, label):
    if comment_match is None:
        errors.append("NO ANCHOR COMMENT for %s" % label)
        return None
    ca_start = template.find('<div class="ca">', comment_match.end())
    end = find_balanced_div(template, ca_start)
    return template[ca_start:end]


for comment_match, content_key, label in (
    (econ_comment, "ECON_CA", "ECON_CA"),
    (earnings_comment, "EARNINGS_CA", "EARNINGS_CA"),
):
    block = extract_ca_after(comment_match, label)
    if block is None:
        continue
    require_unique(block, content_key + " (bare ca div)")
    vals = inj[content_key]
    filled = fill_tokens(block, vals)
    sections[block] = filled
    say(label, "-> ca block len=", len(block), "filled len=", len(filled))

say("TOTAL SECTIONS:", len(sections))
say("TOTAL ERRORS:", len(errors))
for e in errors:
    say("ERROR:", e)


if errors:
    say("ABORTING — fix errors before writing insert.json")
    log.close()
    raise SystemExit(1)

final = dict(content)
final["INJECTED_SECTIONS"] = sections

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

say("WROTE", OUT_PATH, "bytes=", len(json.dumps(final, ensure_ascii=False)))
log.close()
print("BUILD OK - see _build_insert_log.txt")

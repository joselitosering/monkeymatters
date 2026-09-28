P=r"D:\Apps\DevOps\Github\monkeymatters\scripts\fetch_mmm_data.py"
py=open(P,encoding="utf-8").read(); n0=len(py)

old='def build_kpi_tokens(quotes: dict, schwab: dict) -> dict:'
assert py.count(old)==1
new='''CNN_FNG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

# CNN's own rating buckets, mapped to our six-step severity scale.
_FNG_SEV = {
    "extreme fear": "sv-bear2", "fear": "sv-bear", "neutral": "sv-neut",
    "greed": "sv-lean-bull", "extreme greed": "sv-bull",
}


def fetch_fear_greed() -> dict | None:
    """CNN's own internal JSON API (the same one their front-end widget
    calls) -- confirmed live and unauthenticated 2026-09-02. Returns None
    on any failure; the KPI tile falls back to its prior PENDING behavior
    rather than blocking the whole run over one third-party call.
    """
    try:
        req = urllib.request.Request(CNN_FNG_URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.cnn.com/markets/fear-and-greed",
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())["fear_and_greed"]
        score = round(d["score"])
        rating = d["rating"].lower()
        prev_close = round(d["previous_close"])
        delta = score - prev_close
        return {
            "val": str(score),
            "label": f"{rating.title()} ({delta:+d} vs prior close)",
            "sev": _FNG_SEV.get(rating, "sv-neut"),
        }
    except Exception as e:
        print(f"WARN: Fear & Greed fetch failed: {e}", file=sys.stderr)
        return None


def build_kpi_tokens(quotes: dict, schwab: dict) -> dict:'''
assert py.count(new)==0
py=py.replace(old,new,1)

old='''    t["VIX_SEV"] = vix_severity(vix)'''
assert py.count(old)==1
new='''    t["VIX_SEV"] = vix_severity(vix)

    fng = fetch_fear_greed()
    if fng:
        t["FNG_VAL"] = fng["val"]
        t["FNG_LABEL"] = fng["label"] + " -- CNN Fear & Greed, live"
        t["FNG_SEV"] = fng["sev"]'''
assert py.count(old)==1
py=py.replace(old,new,1)

open(P,"w",encoding="utf-8",newline="\n").write(py)
print(n0,"->",len(py),"written")

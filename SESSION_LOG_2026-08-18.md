# SESSION LOG — 2026-08-18 — Daily MMM: from broken assumption to validated pipeline
*Retrospective, not a reference doc. For methodology lessons, not file paths
(those live in MMM_STATUS.md). Written so the pattern that worked here gets
reused, not just the code.*

## What actually happened, in order

Started as a status check on a claimed-but-unverified "armed and live"
Claude scheduled task. Ended with: a working GitHub Actions data pipeline
(15s, validated on real infrastructure), real Schwab futures data, a repo
reorganized around one clear public folder, and a weekly pipeline scoped
honestly instead of half-built. In between: five real bugs, found only
by actually running things, not by reasoning about them.

## The one pattern that did all the work

**Every fix this session came from running the real thing, not from
reading about it or assuming it was fine.** Concretely:

- The "armed and live" scheduled task claim was never independently
  verified — it turned out the whole daily pipeline had actually been
  built by hand, interactively, every night. Found by checking git commit
  timestamps against the claimed trigger time, not by trusting the doc
  that made the claim.
- FMP's MCP tool endpoint names (`index-quote`, etc.) looked like they'd
  be real URL paths. They aren't — confirmed by hitting the raw REST API
  directly and reading the actual 404, not by re-reading FMP's docs a
  second time.
- Schwab's "password rejected" was diagnosed as a redirect_uri mismatch
  from *behavioral evidence* (two different valid passwords, both
  rejected, both working everywhere else) before ever looking at a
  config value — the pattern pointed at the cause before the file did.
- `sanitize.py` failing on itself was resolved by reading its own
  source, not by assuming the flagged content was a real leak and
  panicking or redacting further.
- The UTC/Pacific commit-message drift was caught by checking the local
  clock against the commit's own timestamp when something looked
  slightly off ("2026-08-19"?) — resisting the urge to either dismiss it
  as noise or over-react to it as a serious bug before checking.

None of these were guessable in advance. All of them were fast to fix
once actually observed. The lesson isn't "be more careful" — it's
specifically: **build the smallest thing that can be run for real, run
it, then build the next piece** — which is also just this project's own
existing "one bug per fix cycle" principle, validated again here.

## Where that discipline slipped, worth naming honestly

- Spent real effort on a big-bang "one LLM call fills the whole
  template" design before discovering (from the template's own
  positional, non-unique tokens) that it was fragile — should have
  read the template's full structure before designing the fill
  mechanism, not after.
- Attempted a full-file byte-for-byte transfer via base64 through chat
  tool calls before recognizing that was consuming enormous effort for
  a purely mechanical step — plain-text chunking was faster and safer,
  and should have been the first instinct, not the second.
- Wired Anthropic API billing into the first pipeline design without
  confirming Joe's cost preference first — a "confirm spec before
  coding" miss that cost a full rebuild once he corrected it.

## What to repeat, deliberately, next time

1. Grep/search for existing obsolete references *every time* something
   gets moved or deleted — this caught real bugs in `mmm_sync.py` and
   `pages-deploy.yml`'s own comments that would otherwise have shipped broken.
2. Validate on the *real* target infrastructure before trusting a local
   proxy for it — local Desktop Commander testing caught the sanitize.py
   and .env-fallback issues; only the actual GitHub Actions run caught
   the runner-duration number and confirmed the PAT/push mechanism for real.
3. When a "should work" claim can't be verified from available tools,
   say so plainly instead of assuming it either way — this is what
   surfaced that the original scheduled-task architecture was never
   actually load-bearing.

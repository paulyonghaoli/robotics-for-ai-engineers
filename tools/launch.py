"""Flip the site from soft launch (unindexed) to public, or back.

    python tools/launch.py --status
    python tools/launch.py --go        # allow indexing
    python tools/launch.py --unlaunch  # restore the noindex guards

Two guards keep the site out of search results during soft launch:
`docs/robots.txt` (disallow all) and a `noindex, nofollow` meta tag
injected by `overrides/main.html`. This script toggles both together so
they can't drift out of sync.

It does NOT change the GitHub repo's visibility — that stays a deliberate
manual decision.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROBOTS = ROOT / "docs" / "robots.txt"
OVERRIDE = ROOT / "overrides" / "main.html"

ROBOTS_BLOCKED = "User-agent: *\nDisallow: /\n"
ROBOTS_OPEN = (
    "User-agent: *\n"
    "Allow: /\n\n"
    "Sitemap: https://robotics-for-ai-engineers.paullimale.workers.dev/sitemap.xml\n"
)

META_LINE = '  <meta name="robots" content="noindex, nofollow">'
OVERRIDE_TEMPLATE = """{{% extends "base.html" %}}

{{#
  Soft-launch guard. `python tools/launch.py --go` removes the noindex tag;
  `--unlaunch` restores it. Do not edit by hand — the script keeps this in
  sync with docs/robots.txt.
#}}
{{% block extrahead %}}
{meta}
{{% endblock %}}
"""


def is_blocked() -> bool:
    # Match the actual meta tag, not the word "noindex" — the template's own
    # explanatory comment mentions it, which made a substring check always
    # report "blocked".
    return 'content="noindex' in OVERRIDE.read_text(encoding="utf-8")


def apply(blocked: bool) -> None:
    ROBOTS.write_text(ROBOTS_BLOCKED if blocked else ROBOTS_OPEN, encoding="utf-8")
    meta = META_LINE if blocked else "  {# indexing allowed #}"
    OVERRIDE.write_text(OVERRIDE_TEMPLATE.format(meta=meta), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--status", action="store_true")
    g.add_argument("--go", action="store_true", help="allow search indexing")
    g.add_argument("--unlaunch", action="store_true", help="restore noindex")
    args = ap.parse_args()

    if args.status:
        state = "SOFT LAUNCH (not indexed)" if is_blocked() else "PUBLIC (indexed)"
        print(f"site indexing: {state}")
        rule = ROBOTS.read_text(encoding="utf-8").strip().splitlines()[1]
        print(f"  {ROBOTS.relative_to(ROOT)}: {rule}")
        return 0

    apply(blocked=bool(args.unlaunch))
    state = "restored to SOFT LAUNCH" if args.unlaunch else "OPENED to search engines"
    print("site indexing:", state)
    print("\nnext:")
    print("  python tools/verify.py && git add -A && git commit && git push")
    if args.go:
        print("\nreminder: this does not touch GitHub repo visibility.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

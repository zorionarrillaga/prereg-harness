#!/usr/bin/env python3
"""design_shape_check.py — every DERIVED constraint must name the shape it excludes (L026).

━━ THE DEFECT THIS EXISTS FOR ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C5 (2026-08-12) was designed, pre-registered and killed in one evening. Every link in its
constraint chain was correct:

    F115 says k=1  =>  so it is a daily side-caller  =>  so W = L by construction
    =>  so the only metric is directional accuracy  =>  measured ~50%, killed.

Sound at every step, and the conclusion was about a shape NOBODY DECIDED TO TEST: at a 1:1
payoff breakeven accuracy is 57.5%, but at 3:1 it is 28.7%. The whole cut-losers/run-winners
space — what an elaborated strategy IS — was never in scope, and no document in the chain
contains the sentence "this excludes stop-and-target rules."

A constraint the author CHOSE is visible and gets argued. A constraint that arrived by
IMPLICATION is invisible, because it feels like a finding. **Every `=>` is a place a degree of
freedom was silently spent.**

━━ WHAT THIS CHECKS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each derived-constraint marker, the SAME block must also name an alternative the constraint
EXCLUDES. It fails on ABSENCE, so it cannot be satisfied by being read, agreed with, or
remembered — only by the sentence existing.

⚠ ITS OWN LIMIT, so it is not over-trusted: it enforces that an excluded alternative was NAMED.
It cannot judge whether the right one was named, and a lazy author can satisfy it with a
throwaway. It converts an invisible omission into a visible sentence — which is exactly what was
missing in the C5 chain — and nothing more.

Exit 0 = every derived constraint names an exclusion. Exit 1 = at least one does not.
"""
import argparse, re, sys

# A constraint that ARRIVED (by implication) rather than one that was CHOSEN.
DERIVED = re.compile(
    r"(⇒|=>|\btherefore\b|\bso it (?:must|is)\b|\bforced by\b|\bit follows\b|\bhence\b)",
    re.I)

# The author naming what the constraint rules out.
EXCLUDES = re.compile(
    r"(\bexclud\w+|\brules? out\b|\bnot in scope\b|\bout of scope\b|\bthis forecloses\b|"
    r"\bat the cost of\b|\bnever in scope\b|\bprecludes?\b|\bgives up\b|\bforgo\w*\b|"
    r"\balternative shape\b|\bthe shape (?:this|it) excludes\b)", re.I)


def blocks(text):
    """Paragraph-ish blocks: a derived constraint and its exclusion must sit together."""
    out, cur = [], []
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip():
            cur.append((i, line))
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def check(path):
    text = open(path, encoding="utf-8").read()
    bad, total = [], 0
    for blk in blocks(text):
        body = "\n".join(l for _, l in blk)
        if not DERIVED.search(body):
            continue
        total += 1
        if not EXCLUDES.search(body):
            ln = blk[0][0]
            first = next((l.strip() for _, l in blk if DERIVED.search(l)), blk[0][1].strip())
            bad.append((ln, first[:110]))
    return total, bad


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    fail = False
    for p in a.paths:
        total, bad = check(p)
        if not bad:
            if not a.quiet:
                print(f"✓ {p}: {total} derived constraint(s), all name an exclusion")
            continue
        fail = True
        print(f"\n⛔ {p}: {len(bad)} of {total} derived constraint(s) name NO excluded alternative")
        for ln, snip in bad:
            print(f"   L{ln}: {snip}")
    if fail:
        print("\n  Each block above spends a degree of freedom without saying so. Add the sentence")
        print("  naming what the constraint EXCLUDES — the shape it silently rules out (L026).")
        print("  ⚠ Naming an exclusion is not a defence of it. It makes the choice arguable.")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())

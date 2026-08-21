#!/usr/bin/env python3
"""factory_findings.py — THE EDGE FACTORY's findings ledger. What we KNOW, and how sure.

━━ THE GAP THIS FILLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`registry.jsonl` records every TEST (it is the multiplicity denominator). Nothing recorded what
the tests TAUGHT. By 2026-08-12 the factory's knowledge lived in ten unindexed `research/factory/`
files, three refutation transcripts, a 570-line chronological status document, the
defect queue, commit messages and a memory index — so "what do we know about the placebo arm?"
had no answer short of re-reading the week. Findings were also being SILENTLY SUPERSEDED: the
same morning produced "uniform qualifies" and "uniform never qualified" in different files, both
present, neither marked.

━━ WHY A VERB AND NOT A HAND-EDITED INDEX ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`SESS-2026-06-01_stickiness_noun_vs_verb.md`: nouns rot, verbs stick. A hand-maintained
`FINDINGS.md` would be stale within two sessions, and staleness in a findings index is worse than
absence — it is a confident wrong answer. So the ledger is append-only JSONL written ONLY through
this file, and `FINDINGS.md` is DERIVED and regenerated. Editing the derived file is pointless by
construction; the banner says so.

━━ THE THREE REFUSALS, each from a defect that actually happened ━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. A `measured` finding with no `--repro` is REFUSED. "Do not quote from memory, re-run" is the
     project's own standing rule, and R1 found a claim marked REFUTED whose evidence was a
     throwaway heredoc that was never saved and could not be reproduced.
  2. A finding that supersedes another must NAME it (`--supersedes`), and the named one is flipped
     to SUPERSEDED in the same write. One transaction, or the index disagrees with itself — the
     exact `--settle wrote one store of two` bug from 2026-08-11.
  3. `status` is never inferred from recency. A newer row does not silently outrank an older one;
     someone must say what it replaces.

Verbs:
  add --claim S --kind K --status ST [--repro CMD] [--evidence P ...] [--supersedes F###] [--tag T ...]
  index                      regenerate research/factory/FINDINGS.md from the ledger
  show F###                  one finding in full
  search TERM                claims, tags and evidence paths
  supersede F### --by F###   flip a status after the fact (records who did it and when)
"""
import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "research", "factory", "findings.jsonl")
INDEX = os.path.join(ROOT, "research", "factory", "FINDINGS.md")

# What kind of thing a finding IS. The distinction is load-bearing: R1 returned TERMINAL partly
# because two ARGUED claims had been filed as if MEASURED.
KINDS = {
    "measured": "a number produced by a command that can be re-run",
    "argued": "reasoning over measured things — NOT itself measured",
    "refuted": "a claim we made and then killed; kept so it cannot be re-proposed",
    "process": "a defect in how we work, not in what we found",
    "decision": "a ratified choice and its scope",
}
STATUSES = ("LIVE", "SUPERSEDED", "REFUTED", "OPEN-QUESTION")


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _rows():
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER) as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _current():
    """Latest state per id — a `supersede` row overrides the original's status, nothing else."""
    by = {}
    for r in _rows():
        if r.get("op") == "supersede":
            if r["id"] in by:
                by[r["id"]]["status"] = "SUPERSEDED"
                by[r["id"]]["superseded_by"] = r["by"]
            continue
        by[r["id"]] = r
    return by


def _next_id():
    ids = [int(i[1:]) for i in _current() if i.startswith("F")]
    return f"F{max(ids) + 1 if ids else 1:03d}"


def _append(row):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def cmd_add(a):
    if a.kind not in KINDS:
        sys.exit(f"unknown --kind {a.kind!r}; one of {', '.join(KINDS)}")
    if a.status not in STATUSES:
        sys.exit(f"unknown --status {a.status!r}; one of {', '.join(STATUSES)}")
    # REFUSAL 1 — see the header.
    if a.kind == "measured" and not a.repro:
        sys.exit("REFUSED: a `measured` finding needs --repro (the command that reproduces it).\n"
                 "  A number nobody can re-run is a memory, and memories are what this ledger\n"
                 "  exists to replace. File it as --kind argued if it genuinely is one.")
    cur = _current()
    # REFUSAL 2 — supersession is one transaction.
    for old in a.supersedes:
        if old not in cur:
            sys.exit(f"REFUSED: --supersedes {old} does not exist. Name a real finding.")
    note = a.note
    if getattr(a, "note_file", None):
        if note:
            sys.exit("REFUSED: pass --note OR --note-file, never both — two sources for one "
                     "field is two rulers, and the silent loser would be unknowable later.")
        try:
            note = open(a.note_file, encoding="utf-8").read().strip()
        except OSError as e:
            sys.exit(f"REFUSED: --note-file {a.note_file} unreadable ({e}).")
        if not note:
            sys.exit(f"REFUSED: --note-file {a.note_file} is empty.")
    fid = _next_id()
    _append({"id": fid, "op": "add", "ts": _now(), "date": a.date or _now()[:10],
             "claim": a.claim, "kind": a.kind, "status": a.status, "repro": a.repro,
             "evidence": a.evidence, "tags": a.tags, "supersedes": a.supersedes,
             "note": note})
    for old in a.supersedes:
        _append({"id": old, "op": "supersede", "ts": _now(), "by": fid,
                 "why": f"superseded by {fid}"})
    print(f"{fid}  [{a.status}/{a.kind}]  {a.claim}")
    for old in a.supersedes:
        print(f"    ↳ {old} flipped to SUPERSEDED in the same write")
    return 0


def cmd_supersede(a):
    cur = _current()
    for i in (a.id, a.by):
        if i not in cur:
            sys.exit(f"REFUSED: {i} does not exist.")
    _append({"id": a.id, "op": "supersede", "ts": _now(), "by": a.by, "why": a.why or ""})
    print(f"{a.id} → SUPERSEDED by {a.by}")
    # A supersession changes what the library RENDERS (the row flips to SUPERSEDED), so it is
    return 0


def cmd_show(a):
    r = _current().get(a.id)
    if not r:
        sys.exit(f"no such finding: {a.id}")
    print(f"═══ {r['id']}  [{r['status']} / {r['kind']}]  {r['date']} ═══")
    print(f"  {r['claim']}")
    if r.get("note"):
        print(f"\n  {r['note']}")
    if r.get("repro"):
        print(f"\n  REPRODUCE: {r['repro']}")
    for p in r.get("evidence") or []:
        print(f"  evidence:  {p}")
    if r.get("supersedes"):
        print(f"  supersedes: {', '.join(r['supersedes'])}")
    if r.get("superseded_by"):
        print(f"  ⚠ SUPERSEDED BY: {r['superseded_by']}")
    if r.get("tags"):
        print(f"  tags: {', '.join(r['tags'])}")
    return 0


def cmd_search(a):
    t = a.term.lower()
    hits = [r for r in _current().values()
            if t in json.dumps(r, ensure_ascii=False).lower()]
    for r in sorted(hits, key=lambda x: x["id"]):
        print(f"  {r['id']}  [{r['status']:12s}/{r['kind']:8s}] {r['claim'][:100]}")
    print(f"\n  {len(hits)} finding(s)")
    return 0


ORDER = {"LIVE": 0, "OPEN-QUESTION": 1, "REFUTED": 2, "SUPERSEDED": 3}


def cmd_index(a):
    rows = sorted(_current().values(), key=lambda r: (ORDER.get(r["status"], 9), r["id"]))
    live = [r for r in rows if r["status"] == "LIVE"]
    L = ["# THE EDGE FACTORY — FINDINGS", "",
         "> **DERIVED FILE — DO NOT EDIT.** Regenerated by `python3 bin/factory_findings.py index`",
         "> from the append-only ledger `research/factory/findings.jsonl`. Edits here are lost on",
         "> the next write; record with `factory_findings.py add` instead.", "",
         f"_{len(rows)} findings · {len(live)} LIVE · generated {_now()}_", ""]
    L += ["## How to read this", "",
          "- **LIVE** — believed, and nothing has replaced it. **SUPERSEDED** — a later finding",
          "  replaced it; the row names which. **REFUTED** — we killed it ourselves; kept so it",
          "  cannot be quietly re-proposed. **OPEN-QUESTION** — named, not answered.",
          "- **measured** carries a command that reproduces it. **argued** does not, and must never",
          "  be quoted as if it did. An external refutation round went terminal partly on that confusion.", ""]
    for st in ("LIVE", "OPEN-QUESTION", "REFUTED", "SUPERSEDED"):
        grp = [r for r in rows if r["status"] == st]
        if not grp:
            continue
        L.append(f"## {st}  ({len(grp)})")
        L.append("")
        for r in grp:
            L.append(f"### {r['id']} · {r['claim']}")
            L.append("")
            L.append(f"`{r['kind']}` · {r['date']}"
                     + (f" · tags: {', '.join(r['tags'])}" if r.get("tags") else ""))
            L.append("")
            if r.get("note"):
                L += [r["note"], ""]
            if r.get("repro"):
                L += [f"**Reproduce:** `{r['repro']}`", ""]
            if r.get("evidence"):
                L += ["**Evidence:** " + " · ".join(f"`{p}`" for p in r["evidence"]), ""]
            if r.get("supersedes"):
                L += ["**Supersedes:** " + ", ".join(r["supersedes"]), ""]
            if r.get("superseded_by"):
                L += [f"**⚠ Superseded by:** {r['superseded_by']}", ""]
    with open(INDEX, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"wrote {os.path.relpath(INDEX, ROOT)} — {len(rows)} findings, {len(live)} LIVE")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--claim", required=True, help="one line, the finding itself")
    a.add_argument("--kind", required=True, help=" | ".join(f"{k}: {v}" for k, v in KINDS.items()))
    a.add_argument("--status", default="LIVE", help=" | ".join(STATUSES))
    a.add_argument("--repro", help="command that reproduces it — REQUIRED for --kind measured")
    a.add_argument("--evidence", nargs="*", default=[], help="repo-relative paths")
    a.add_argument("--tags", nargs="*", default=[])
    a.add_argument("--supersedes", nargs="*", default=[])
    a.add_argument("--note", help="the paragraph a one-line claim cannot carry")
    # F264: --note reaches here as a double-quoted SHELL argument, so any backtick-delimited
    # span — this repo's house style for a path, a flag or a status word — is run as a command
    # substitution and replaced by its empty output. It deleted a word from F260's note with no
    # error. The corruption happens BEFORE this process starts, so no validator here can see it;
    # the only real fix is an input path the shell never touches. This is that path.
    # ⚠ Rung 2, honestly: it makes a safe door available, it does not remove the unsafe one.
    a.add_argument("--note-file", dest="note_file", metavar="PATH",
                   help="read --note from a file instead (SHELL-SAFE: backticks in the prose "
                        "cannot be eaten by command substitution). Mutually exclusive with --note.")
    a.add_argument("--date", help="YYYY-MM-DD (defaults to today)")
    a.set_defaults(fn=cmd_add)
    s = sub.add_parser("supersede")
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.add_argument("--why")
    s.set_defaults(fn=cmd_supersede)
    sh = sub.add_parser("show")
    sh.add_argument("id")
    sh.set_defaults(fn=cmd_show)
    se = sub.add_parser("search")
    se.add_argument("term")
    se.set_defaults(fn=cmd_search)
    ix = sub.add_parser("index")
    ix.set_defaults(fn=cmd_index)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

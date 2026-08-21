#!/usr/bin/env python3
"""factory_registry.py — THE EDGE FACTORY's append-only, hash-chained test registry.

D048 / charter §4.1-§4.2: every hypothesis registration and every verdict is a row here. The row
count IS the multiplicity denominator; the hash chain makes silent deletion or rewrite DETECTABLE
(git history is rewritable by its author — the chain is the in-band tamper evidence); the sha256
of the registered spec file is the pre-registration FREEZE (the NEXUS device, adopted at R2
FOLD-9). A kill/null verdict WITHOUT its achieved MDE is REFUSED at the write — "no edge found"
must always be "no edge above X found" (charter §4.2).

Verbs:
  register --file F --kind K --name N [--payload JSON]    append a registration (spec sha256 frozen)
  verdict  --name N --stage S --outcome O [--mde X] [--payload JSON]
  round-close --name N [--payload JSON]                   close a Phase-2 round (budget counts these)
  verify                                                  walk + recompute the chain; exit 0/1
  count                                                   denominator counts by kind/outcome

Env seam: HARNESS_FACTORY_DIR (tests). Default: research/factory/ (git-tracked, NOT data/).
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FDIR = os.environ.get("HARNESS_FACTORY_DIR") or os.path.join(REPO, "research", "factory")
REG = os.path.join(FDIR, "registry.jsonl")
GENESIS = "edge-factory-genesis-D048"


def _canon(row):
    return json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _rows():
    if not os.path.exists(REG):
        return []
    out = []
    with open(REG, encoding="utf-8") as fh:
        for i, ln in enumerate(fh):
            ln = ln.strip()
            if ln:
                out.append((i + 1, json.loads(ln)))
    return out


def _append(kind, name, payload):
    rows = _rows()
    prev = rows[-1][1]["row_hash"] if rows else _hash(GENESIS)
    row = {"seq": len(rows) + 1,
           "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "kind": kind, "name": name, "prev": prev}
    for k, v in payload.items():
        if k not in row:
            row[k] = v
    row["row_hash"] = _hash(_canon({k: v for k, v in row.items() if k != "row_hash"}))
    os.makedirs(FDIR, exist_ok=True)
    with open(REG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"registry: +row #{row['seq']} {kind} '{name}' chain={row['row_hash'][:12]}")
    return 0


def cmd_register(a):
    if not os.path.exists(a.file):
        print(f"registry: REFUSED — spec file not found: {a.file}", file=sys.stderr)
        return 2
    with open(a.file, encoding="utf-8") as fh:
        spec_sha = _hash(fh.read())
    payload = json.loads(a.payload) if a.payload else {}
    payload.update({"file": os.path.relpath(os.path.abspath(a.file), REPO), "sha256": spec_sha})
    rc = _append(a.kind, a.name, payload)
    if a.kind == "prereg":
        # L025 (F037) — fires HERE because this is the moment a pre-registration is filed and the
        # question is still answerable. A prompt, not a refusal: this command cannot tell whether a
        # given spec has a free parameter. See the lesson's stickiness section for what stays naked.
        print("\n  ★ L025 — A PRE-REGISTERED FREE PARAMETER IS STILL A FREE PARAMETER.")
        print("    Fixing it by hash proves you did not choose it after seeing the result. It does")
        print("    NOT make one arbitrary value representative. Measured: a correctly hash-fixed")
        print("    BLOCK_MIN=5 still landed on the transform where the instrument looked LEAST")
        print("    biased, by ~2x (F037), and every number published off it was the optimistic end.")
        print("    ⇒ SWEEP each free parameter and report the MEDIAN across its range — never the")
        print("      friendliest value. If a sweep is unaffordable, say IN THE ARTIFACT that the")
        print("      verdict is conditional on one point and its representativeness is unmeasured.")
        print("    ⇒ And if an estimator's bias points at the conclusion you expect, CORRECT it and")
        print("      report BOTH ends of the bracket, so the verdict cannot rest on your own")
        print("      correction.  lessons/L025.md\n")

        # F118 + L026 — fire HERE for the same reason L025 does: this is the last moment before a
        # spec is frozen. Both are CONTENT-AWARE (they read the spec and stay silent when they do
        # not apply) rather than unconditional banners, because a prompt that always prints is
        # wallpaper and stops being read. Neither can block: cmd_register's return code is
        # untouched and the chain is already appended above.
        with open(a.file, encoding="utf-8") as fh:
            spec = fh.read()
        low = spec.lower()

        # (1) A hit-rate primary with no declared payoff. C5 was frozen TWICE through this exact
        # command carrying exactly this defect (F118).
        hitrate = any(t in low for t in ("hit rate", "hit-rate", "directional accuracy",
                                         "win rate", "win-rate"))
        payoff = any(t in low for t in ("r:r", "reward:risk", "reward-to-risk", "payoff",
                                        "take profit", "target", "expectancy", "w/l", "1:1",
                                        "2:1", "3:1"))
        if hitrate and not payoff:
            print("  ⛔ F118 — THIS SPEC'S METRIC LOOKS LIKE A HIT RATE AND IT DECLARES NO PAYOFF.")
            print("    Breakeven directional accuracy is (L+c)/(W+L): 57.5% at 1:1 but 28.7% at 3:1.")
            print("    A hit-rate screen is a CATEGORY ERROR for any rule that is not 1:1, and it")
            print("    cannot see the cut-losers/run-winners space at all. C5 was frozen through")
            print("    this very command twice carrying exactly this defect.")
            print("    ⇒ Pre-screen on EXPECTANCY AT A DECLARED R:R, or state in the spec why the")
            print("      rule really is 1:1 and what that excludes.\n")

        # (2) L026 — every derived constraint must name the shape it excludes.
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import design_shape_check as dsc
            total, bad = dsc.check(a.file)
            if bad:
                print(f"  ⛔ L026 — {len(bad)} of {total} DERIVED constraint(s) in this spec name no")
                print("    excluded alternative. A constraint that arrived by implication is")
                print("    invisible, because it feels like a finding — every '⇒' spends a degree")
                print("    of freedom. Name what each rules OUT, or the shape gets chosen by the")
                print("    chain rather than by you (that is how C5 ended up 1:1).")
                for ln, snip in bad[:3]:
                    print(f"      L{ln}: {snip[:88]}")
                print("    verb: python3 bin/design_shape_check.py " + a.file + "\n")
            elif total:
                print(f"  ✓ L026 — {total} derived constraint(s), each names an exclusion.\n")
        except Exception as e:                      # never let an advisory break a registration
            print(f"  (L026 check unavailable: {e})\n")
    return rc


def cmd_verdict(a):
    payload = json.loads(a.payload) if a.payload else {}
    if a.mde is not None:
        payload["mde"] = a.mde
    elif a.outcome in ("killed", "null"):
        print("registry: REFUSED — a kill/null verdict without --mde violates §4.2: "
              "'no edge found' must always be 'no edge above X found'", file=sys.stderr)
        return 2
    # ★★★ A LICENCE IS THE ONE VERDICT THIS FILE MAY NOT SIMPLY BE TOLD (2026-08-12, F047/F048).
    #   Charter §4.4/§4.7: a green gate does not license the harness — only a fresh-context
    #   EXTERNAL seat does. Until today that rule lived in a docstring, a findings row and a
    #   printed disclaimer, i.e. three nouns. MEASURED by the F026 licensing seat: it wrote
    #   `--outcome licensed` from a plain shell in an isolated HARNESS_FACTORY_DIR — no seat, no
    #   evidence, no artifact, and no --mde, because the refusal above deliberately covers only
    #   kill/null. `edge_factory_gauge.py` then CONSUMES that row to suppress the phase cap.
    #   The charter said this about itself in advance: "Until they exist this constitution is a
    #   NOUN and says so." This is the verb.
    #
    #   ⚠ SCOPE — this ENFORCES ratified text, it does not author new policy. The requirement is
    #   D048's, already ratified; the external seat that specified this exact check is
    #   an external refutation seat's own licence condition #5, so it
    #   is externally specified rather than self-graded. It cannot license anything — it can only
    #   refuse — so the failure mode of a bug here is a licence that is harder to record, never
    #   one that is easier.
    if a.outcome == "licensed":
        ev = getattr(a, "evidence", None)
        if not ev:
            print("registry: REFUSED — a `licensed` verdict requires --evidence <path> naming the "
                  "external seat's refutation artifact. Charter §4.4/§4.7: the gate cannot "
                  "license itself, and a licence nobody can trace to a seat is a self-licence.",
                  file=sys.stderr)
            return 2
        if not os.path.exists(os.path.join(REPO, ev)) and not os.path.exists(ev):
            print(f"registry: REFUSED — --evidence '{ev}' does not exist on disk. A licence must "
                  "point at an artifact a later reader can actually open.", file=sys.stderr)
            return 2
        payload["evidence"] = ev
    payload.update({"stage": a.stage, "outcome": a.outcome})
    return _append("verdict", a.name, payload)


def cmd_round_close(a):
    payload = json.loads(a.payload) if a.payload else {}
    return _append("round-close", a.name, payload)


def cmd_verify(_a=None, quiet=False):
    prev = _hash(GENESIS)
    rows = _rows()
    for lineno, row in rows:
        body = {k: v for k, v in row.items() if k != "row_hash"}
        if body.get("prev") != prev:
            print(f"registry: CHAIN BROKEN at line {lineno} (seq {row.get('seq')}) — prev-hash mismatch")
            return 1
        if _hash(_canon(body)) != row.get("row_hash", ""):
            print(f"registry: CHAIN BROKEN at line {lineno} (seq {row.get('seq')}) — row-hash mismatch")
            return 1
        prev = row["row_hash"]
    if not quiet:
        print(f"registry: chain OK — {len(rows)} row(s)")
    return 0


def cmd_count(_a=None):
    rows = [r for _, r in _rows()]
    by_kind = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    outcomes = {}
    for r in rows:
        if r["kind"] == "verdict":
            key = f"{r.get('stage','?')}/{r.get('outcome','?')}"
            outcomes[key] = outcomes.get(key, 0) + 1
    print(f"registry: {len(rows)} row(s) total — THE multiplicity denominator")
    for k, v in sorted(by_kind.items()):
        print(f"  {k}: {v}")
    for k, v in sorted(outcomes.items()):
        print(f"  verdict {k}: {v}")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register")
    r.add_argument("--file", required=True)
    r.add_argument("--kind", required=True,
                   choices=["prereg", "fork-spec", "harness-gate", "data-report"])
    r.add_argument("--name", required=True)
    r.add_argument("--payload")
    v = sub.add_parser("verdict")
    v.add_argument("--name", required=True)
    v.add_argument("--stage", required=True,
                   choices=["fork", "train", "validation", "holdout", "shadow", "harness"])
    v.add_argument("--outcome", required=True, choices=["killed", "null", "survived", "licensed"])
    v.add_argument("--mde", type=float)
    # Required for --outcome licensed: the external seat's artifact. See cmd_verdict.
    v.add_argument("--evidence")
    v.add_argument("--payload")
    rc = sub.add_parser("round-close")
    rc.add_argument("--name", required=True)
    rc.add_argument("--payload")
    sub.add_parser("verify")
    sub.add_parser("count")
    a = p.parse_args()
    return {"register": cmd_register, "verdict": cmd_verdict, "round-close": cmd_round_close,
            "verify": cmd_verify, "count": cmd_count}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

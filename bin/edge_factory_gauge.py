#!/usr/bin/env python3
"""edge_factory_gauge.py — THE EDGE FACTORY's pace + integrity gauge (D048; charter §6; H32).

HEADLINE: candidates resolved this week · resolved/registered totals · survivors by stage ·
budget state. The headline is the PACE gauge only — the outcome-delta success criteria
(GOVERNANCE §3.2, per R2 FOLD-7) are: (a) a survivor whose holdout CI lower bound clears the
MUE, or (b) dormancy executed on schedule. Either is the mechanism working.

--healthcheck (wired as H61): exit 1 when
  · the registry hash-chain is broken (tampered/deleted rows), or
  · the ratified Phase-2 budget is EXHAUSTED and no dormancy record exists
    (research/factory/DORMANCY.md) — the verb behind §4.8 "the stopping rule outranks hope", or
  · Phases 0+1 have blown their ratified cap with no Phase-1 harness-gate row and no dormancy.
Exit 0 otherwise (including "factory not initialized" — no budget.json). Both exit values are
reachable and proven by fixtures in tests/test_factory_registry.sh.

Env seam: HARNESS_FACTORY_DIR (tests).
"""
import datetime
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FDIR = os.environ.get("HARNESS_FACTORY_DIR") or os.path.join(REPO, "research", "factory")
BUDGET = os.path.join(FDIR, "budget.json")
DORMANCY = os.path.join(FDIR, "DORMANCY.md")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import factory_registry as freg  # noqa: E402


def _load_budget():
    if not os.path.exists(BUDGET):
        return None
    with open(BUDGET, encoding="utf-8") as fh:
        return json.load(fh)


def _rows():
    return [r for _, r in freg._rows()]


def _iso_week(ts):
    try:
        d = datetime.datetime.fromisoformat(ts)
        return d.isocalendar()[:2]
    except Exception:
        return None


def report(healthcheck=False):
    b = _load_budget()
    if b is None:
        print("edge-factory: NOT INITIALIZED (no budget.json) — ratify D048 first")
        return 0

    chain_rc = freg.cmd_verify(quiet=True)
    rows = _rows() if chain_rc == 0 else []
    now = datetime.datetime.now().astimezone()
    this_week = now.isocalendar()[:2]

    regs = [r for r in rows if r["kind"] in ("prereg", "fork-spec")]
    verdicts = [r for r in rows if r["kind"] == "verdict"]
    resolved = [r for r in verdicts if r.get("outcome") in ("killed", "null", "survived")]
    resolved_wk = [r for r in resolved if _iso_week(r.get("ts", "")) == this_week]
    rounds_closed = len([r for r in rows if r["kind"] == "round-close"])
    # ★ THE LATEST VERDICT PER (name, stage) WINS — a survivor can be WITHDRAWN.
    # The first version counted every `survived` row forever, so appending the retraction of a
    # candidate left the headline still reading "survivors: fork:1". The registry is append-only
    # (a withdrawal is a NEW row, never an edit), which means a gauge that reads every row as
    # current cannot see a retraction at all — it can only ever overstate. Found on the first
    # real withdrawal: P0A-FORK-3 fired BRANCH C, its price-matched control refuted it, and the
    # headline went on reporting the survivor. Overstating survivors is the one direction this
    # gauge must never fail in.
    latest = {}
    for r in verdicts:
        latest[(r.get("name"), r.get("stage"))] = r          # rows are in append order
    survivors = {}
    for (name, stage), r in latest.items():
        if r.get("outcome") == "survived":
            survivors.setdefault(stage or "?", []).append(name)

    # budget state
    p2 = b.get("phase2_start")
    errors = []
    if chain_rc != 0:
        errors.append("registry hash-chain BROKEN — run: python3 bin/factory_registry.py verify")
    if p2:
        start = datetime.datetime.fromisoformat(p2).astimezone()
        elapsed_d = (now - start).days
        cap_d = int(b.get("phase2_budget_weeks", 8)) * 7
        left_d = cap_d - elapsed_d
        exhausted = (elapsed_d > cap_d) or (rounds_closed >= int(b.get("phase2_budget_rounds", 3)))
        budget_line = (f"Phase-2 clock RUNNING since {p2}: day {elapsed_d}/{cap_d} · "
                       f"rounds closed {rounds_closed}/{b.get('phase2_budget_rounds', 3)}")
        if exhausted:
            holdout_survivor = bool(survivors.get("holdout") or survivors.get("shadow"))
            if not holdout_survivor and not os.path.exists(DORMANCY):
                errors.append(
                    "BUDGET EXHAUSTED with no surviving candidate and NO DORMANCY RECORD — "
                    "the ratified stopping rule (D048 §5) requires the dormancy consequence to "
                    "execute NOW: write research/factory/DORMANCY.md (date · the per-family MDEs "
                    "achieved · 'trading track dormant, contracting sole track'). Extending the "
                    "budget requires a NEW ratification citing NEW evidence.")
            budget_line += " — EXHAUSTED"
    else:
        p01 = b.get("phase01_start")
        cap = int(b.get("phase01_cap_days", 14))
        gate_rows = [r for r in verdicts if r.get("stage") == "harness" and r.get("outcome") == "licensed"]
        elapsed = (now.date() - datetime.date.fromisoformat(p01)).days if p01 else 0
        budget_line = (f"Phase-2 clock NOT RUNNING (gate: {b.get('phase2_gate','?')}) · "
                       f"Phases 0+1 day {elapsed}/{cap}")
        if p01 and elapsed > cap and not gate_rows and not os.path.exists(DORMANCY):
            errors.append(
                f"Phases 0+1 blew their ratified {cap}-day cap with NO harness-gate row — the "
                "factory is stalled before it started. Finish the Phase-1 not-blind gate (an "
                "external seat licenses it, §4.4) or take the honest stop; silence is the one "
                "disallowed state.")

    print("═══ EDGE FACTORY — HEADLINE (pace gauge; success = MUE-clearing survivor OR on-schedule dormancy) ═══")
    print(f"  resolved this week: {len(resolved_wk)} · resolved total: {len(resolved)} / registered: {len(regs)}"
          f" · registry rows: {len(rows)} (THE denominator)")
    print(f"  survivors by stage: " + (", ".join(f"{k}:{len(v)}" for k, v in sorted(survivors.items())) or "none"))
    print(f"  {budget_line}")
    # ★ THE RATE FLOOR PRINTS ITS SEMANTICS (D055, 2026-08-13). A bare "≥2 signals/wk" is exactly
    #   the ambiguity the `rate-floor-semantics` entry was raised about — per-leg and portfolio-wide
    #   read the same on this line and differ by 8× for a multi-instrument candidate. The word is
    #   taken from budget.json, never hardcoded, so the gauge cannot drift from the ruling.
    # ⚠ `"".split()` is [], so the [0] below MUST be guarded — the `else ' (⚠ semantics
    #   UNRULED)' branch two lines down exists precisely for the absent key, and without
    #   this guard it was unreachable: the gauge raised IndexError instead of printing it.
    #   Found by running this repo's own registry test suite against a budget fixture that
    #   omits the key, which is the only configuration the private tree never had.
    _sem_words = (b.get("mue_min_signals_per_week_semantics") or "").split()
    _sem = _sem_words[0].rstrip(".,").lower() if _sem_words else ""
    print(f"  MUE (ratified): +{b.get('mue_r_net')}R/trade net · ≥{b.get('mue_min_signals_per_week')} signals/wk"
          f"{f' ({_sem}, per budget.json)' if _sem else ' (⚠ semantics UNRULED)'}"
          f" · dormancy record: {'PRESENT' if os.path.exists(DORMANCY) else 'none'}")
    if len(resolved_wk) == 0 and p2:
        print("  ⚠ zero candidates resolved this week with the budget running — the factory is "
              "stalled and this line is the swallowed-project tripwire")
    # ── PENDING DECISIONS — surfaced by a verb, never by anyone's memory ─────────────────────
    # An open question parked in a person's head is not parked, it is lost, and a row in a status
    # document reading "operator's call" is a noun that rots. So each entry carries a CHECK — a
    # command that exits 0 once the answer has been RECORDED durably — and an entry can only be
    # closed by the artifact existing, never by anyone deciding it was handled. Past its due date
    # it becomes an ERROR, which is the point: silence stops being an available state.
    pend_f = os.path.join(FDIR, "pending_decisions.json")
    if os.path.exists(pend_f):
        try:
            entries = json.load(open(pend_f)).get("pending", [])
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            entries = []
            errors.append(f"pending_decisions.json will not parse ({e}) — the register that "
                          f"carries the programme's open questions is unreadable, which is worse than "
                          f"any single question in it")
        open_rows = []
        for d in entries:
            chk = d.get("check")
            decided = False
            if chk:
                decided = subprocess.run(chk, shell=True, cwd=REPO,
                                         capture_output=True).returncode == 0
            if decided:
                continue
            due = d.get("due")
            overdue = bool(due and str(now.date()) >= due)
            open_rows.append((d, due, overdue))
            if overdue:
                errors.append(
                    f"DECISION OVERDUE ({d.get('id')}, due {due}): {d.get('question')} "
                    f"— options: {d.get('options', 'see the register')}. This is not a defect and "
                    f"nobody but the ratifying authority can clear it; it is red because it was DUE and is "
                    f"still unrecorded. Discharge: {d.get('discharged_when')}")
        if open_rows:
            print(f"\n  ── OPEN DECISIONS ({len(open_rows)}) — "
                  f"research/factory/pending_decisions.json ──")
            for d, due, overdue in open_rows:
                print(f"  {'✗ OVERDUE' if overdue else '·  pending'} [{d.get('id')}] due {due}"
                      f"\n       {d.get('question')}")
                if d.get("proposal"):
                    print(f"       proposal: {d['proposal']}")


    for e in errors:
        print(f"  ✗ {e}")
    if healthcheck:
        return 1 if errors else 0
    return 0


def overdue_decisions():
    """OVERDUE decisions only. Exit 1 if any, 0 if none. Deliberately wire-narrow.

    Separate from report() on purpose: this is what an unattended cron job calls every two
    minutes, so it must be cheap, read-only, and it must stay SILENT unless something is
    actually past its due date. A line that always prints is a line that stops being read —
    which is exactly how the status-table version of this register failed (F069).
    """
    f = os.path.join(FDIR, "pending_decisions.json")
    if not os.path.exists(f):
        return 0
    try:
        entries = json.load(open(f)).get("pending", [])
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("pending_decisions.json will not parse — the register is unreadable")
        return 1
    today = str(datetime.date.today())
    hit = []
    for d in entries:
        due = d.get("due")
        if not due or today < due:
            continue
        chk = d.get("check")
        if chk and subprocess.run(chk, shell=True, cwd=REPO,
                                  capture_output=True).returncode == 0:
            continue
        hit.append(d)
    for d in hit:
        print(f"OVERDUE [{d['id']}] due {d['due']} — {d.get('question','')}")
    return 1 if hit else 0


if __name__ == "__main__":
    if "--overdue-decisions" in sys.argv:
        sys.exit(overdue_decisions())
    sys.exit(report(healthcheck="--healthcheck" in sys.argv))

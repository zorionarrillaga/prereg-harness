#!/usr/bin/env python3
"""factory_data.py — THE EDGE FACTORY, Phase 0: the data foundation.

Charter §3-Phase-0: *"Extend the certified pipeline past 2024-03 and to the breadth set. Integrity
checks: depth, gaps, session structure, DST, weekend boundaries, agreement with our recorded
corpus on every overlapping day. GATE: a written data-integrity + cost-model report; any
instrument failing it is excluded; all failing ⇒ factory stops."*

Phase-0a returned **BRANCH B** (the tape/frame is the constraint, not the read), which makes the
BREADTH leg load-bearing and the depth leg secondary — the point is no longer "more US100 1m
days", it is "other instruments and other frames at all".

━━ WHY THIS IS NOT gym_context_fetch._ensure_duka ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
That decoder hardcodes `price / 1000` with a sanity band of `1000 < o < 100000`. It is correct
for US100 and SILENTLY WRONG for every FX major: EURUSD's raw 115348 decodes to 115.348, which
fails the band and returns [] — so FX looks like "no data" rather than "wrong divisor". Measured
2026-08-11: indices and metals are ÷1e3, FX majors ÷1e5. **The divisor is declared per instrument
here and every decoded day is checked against a declared plausibility band; a violation EXCLUDES
the instrument rather than guessing a scale.** A wrong scale is the worst possible failure — it
produces a complete, plausible-looking tape that is off by 100×, and every downstream R is fiction.

━━ WHAT THIS DATA IS, AND IS NOT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dukascopy **BID** 1-minute candles on their own CFD feed. NOT the broker's tape. It was certified once
against our one TRUE-COVERED day at 0.998 1m-return correlation, basis −2.45pt, level
reconstruction error 1.52/3.56/2.52pt — that residual rides as an explicit uncertainty band on
every backtest verdict, and **the cost model comes from our own broker evidence, never from here**
(charter §4.5). Vendor spread realism is irrelevant to us for the same reason.

Verbs:
  depth   --symbols A,B     how far back does each instrument actually serve?
  pull    --symbols A,B --from YYYY-MM-DD --to YYYY-MM-DD   bulk cache (polite, resumable)
  integrity --symbols A,B --from … --to …                   the Phase-0 gate report

Cache: data/factory/duka/<SYMBOL>/<YYYY-MM-DD>.json (gitignored — regenerable, bulky).
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import lzma
import os
import struct
import sys
import time
import urllib.request
import zoneinfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "factory", "duka")
ET = zoneinfo.ZoneInfo("America/New_York")      # ⚠ real tz, never a hardcoded −4 (DST)
UTC = dt.timezone.utc

# ── THE INSTRUMENT TABLE — divisor and plausibility band DECLARED, then verified per day ──
# `rth` is the instrument's own primary cash session in its own exchange timezone; it is what the
# session-structure check counts.
INSTRUMENTS = {
    "USATECHIDXUSD": dict(name="US100",  div=1e3, band=(1_000, 100_000), tz="America/New_York",
                          rth=("09:30", "16:00")),
    "USA500IDXUSD":  dict(name="US500",  div=1e3, band=(500, 50_000),    tz="America/New_York",
                          rth=("09:30", "16:00")),
    "USA30IDXUSD":   dict(name="US30",   div=1e3, band=(5_000, 200_000), tz="America/New_York",
                          rth=("09:30", "16:00")),
    "DEUIDXEUR":     dict(name="DE40",   div=1e3, band=(2_000, 100_000), tz="Europe/Berlin",
                          rth=("09:00", "17:30")),
    "GBRIDXGBP":     dict(name="UK100",  div=1e3, band=(2_000, 50_000),  tz="Europe/London",
                          rth=("08:00", "16:30")),
    "JPNIDXJPY":     dict(name="JP225",  div=1e3, band=(5_000, 200_000), tz="Asia/Tokyo",
                          rth=("09:00", "15:00")),
    "XAUUSD":        dict(name="GOLD",   div=1e3, band=(200, 20_000),    tz="America/New_York",
                          rth=("08:20", "13:30")),
    "XAGUSD":        dict(name="SILVER", div=1e3, band=(2, 500),         tz="America/New_York",
                          rth=("08:25", "13:25")),
    "EURUSD":        dict(name="EURUSD", div=1e5, band=(0.5, 2.5),       tz="America/New_York",
                          rth=("08:00", "17:00")),
    "GBPUSD":        dict(name="GBPUSD", div=1e5, band=(0.8, 3.0),       tz="America/New_York",
                          rth=("08:00", "17:00")),
    "AUDUSD":        dict(name="AUDUSD", div=1e5, band=(0.4, 1.5),       tz="America/New_York",
                          rth=("08:00", "17:00")),
    "USDCAD":        dict(name="USDCAD", div=1e5, band=(0.8, 2.5),       tz="America/New_York",
                          rth=("08:00", "17:00")),
    "USDJPY":        dict(name="USDJPY", div=1e3, band=(50, 400),        tz="America/New_York",
                          rth=("08:00", "17:00")),
}
BREADTH = ["USATECHIDXUSD", "USA500IDXUSD", "USA30IDXUSD", "DEUIDXEUR",
           "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]


# ── fetch + decode ────────────────────────────────────────────────────────────────────────
ROW_SCHEMA = "ohlcv-1"   # bump when the cached ROW dict changes shape; resume re-fetches on mismatch


def _path(sym, d):
    return os.path.join(CACHE, sym, f"{d.isoformat()}.json")


def fetch_day(sym, d, tries=4, force=False):
    """One vendor day → {'rows': [...], 'status': ...}, cached forever (a past day never changes).

    status: ok · empty (weekend/holiday) · http · scale (band violation → the instrument is
    suspect, NOT the day) · decode."""
    p = _path(sym, d)
    if os.path.exists(p) and not force:
        # A cache entry that will not parse is NOT a cache hit. Any pre-existing truncated file
        # (written before the atomic-write fix below) would otherwise raise here and abort the
        # whole pull, with no way to recover but to find and delete the file by hand. Treat it
        # as missing and re-fetch — the resume path heals itself instead of poisoning.
        try:
            with open(p) as fh:
                blob = json.load(fh)
            if blob.get("status") != "ok" or blob.get("schema") == ROW_SCHEMA:
                return blob
            # stale row schema — fall through and re-fetch (see cmd_pull's resume note)
        except (json.JSONDecodeError, UnicodeDecodeError):
            os.remove(p)
    spec = INSTRUMENTS[sym]
    # ⚠ THE MONTH IS 0-INDEXED. The classic Dukascopy trap: a wrong month returns REAL data for
    # the WRONG day and nothing errors anywhere.
    url = (f"https://datafeed.dukascopy.com/datafeed/{sym}/"
           f"{d.year}/{d.month - 1:02d}/{d.day:02d}/BID_candles_min_1.bi5")
    raw, err = None, None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = lzma.decompress(urllib.request.urlopen(req, timeout=30).read())
            break
        except lzma.LZMAError:
            raw, err = b"", None          # zero-length body = no data for that day
            break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:60]}"
            time.sleep(1.5 * (t + 1))     # polite backoff; the feed 503s under burst
    out = {"symbol": sym, "date": d.isoformat()}
    if raw is None:
        out.update(status="http", why=err, rows=[])
        return out                        # NOT cached — a transient must stay retryable
    day0 = int(dt.datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp())
    rows, lo_b, hi_b = [], *spec["band"]
    for i in range(len(raw) // 24):
        s, o, c, low, high, vol = struct.unpack(">IIIIIf", raw[i * 24:(i + 1) * 24])
        o, c, low, high = (x / spec["div"] for x in (o, c, low, high))
        if not (lo_b <= o <= hi_b):
            out.update(status="scale", why=f"open {o} outside declared band {spec['band']}",
                       rows=[])
            return out                    # NOT cached — the instrument is suspect, not the day
        if not (low <= o <= high and low <= c <= high):
            out.update(status="decode", why=f"OHLC inconsistent at row {i}", rows=[])
            return out
        # ⚠ VOLUME WAS BEING DISCARDED. The 6th field of the bi5 candle record was unpacked into
        # `_v` and dropped when the row was built, so every cached day carried OHLC only. That is
        # invisible until something needs it — and the first thing that did was a VWAP-reversion
        # candidate, whose ONLY claim to differ from the TWAP rule that already died as
        # entry-price arithmetic (F003) is that its target is a real VWAP. A volume-less tape
        # silently collapses that candidate back into the dead one under a new name.
        #
        # ⚠ IT IS BID-SIDE VENDOR VOLUME, NOT EXCHANGE VOLUME. The URL is BID_candles_min_1.bi5,
        # so this is Dukascopy's own bid-book activity proxy, not consolidated tape volume. A
        # VWAP built on it is a vendor-bid-VWAP. It is a legitimate, reproducible reference
        # series; it is NOT the VWAP a published result or a TradingView chart was built on, and
        # no cross-source VWAP claim may be made from it. Recorded, not assumed away.
        rows.append({"time": day0 + s, "open": round(o, 5), "high": round(high, 5),
                     "low": round(low, 5), "close": round(c, 5), "volume": round(vol, 4)})
    out.update(status="ok" if rows else "empty", rows=rows, schema=ROW_SCHEMA)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    # ⚠ ATOMIC — write to a temp file in the same directory, then rename. A direct
    # `open(p, "w")` leaves a TRUNCATED file at the real path if the process dies mid-write
    # (power loss, hard kill; ordinary sleep merely suspends and is safe). That file then
    # satisfies the `os.path.exists` resume check above, so the day counts as cached forever
    # while `json.load` raises on it — turning a crash into a permanently poisoned cache entry
    # that the resume path can never heal. `os.replace` is atomic on POSIX: the reader sees the
    # old file or the complete new one, never a partial.
    tmp = f"{p}.tmp.{os.getpid()}"
    with open(tmp, "w") as fh:
        json.dump(out, fh)
    os.replace(tmp, p)
    return out


def weekdays(a, b):
    d, out = a, []
    while d <= b:
        if d.weekday() < 5:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


# ── verbs ─────────────────────────────────────────────────────────────────────────────────
def cmd_depth(a):
    """How far back does each instrument ACTUALLY serve? One probe date per year, walking back.

    ⚠ THE DEFECT THIS VERSION FIXES, found by running it: the first version stopped at the first
    non-ok year and reported that as the depth floor — but the feed 503s under burst, so a
    THROTTLE was being recorded as "the vendor has no data that far back". XAUUSD and EURUSD each
    reported a 1-year floor for exactly that reason, while the indices (probed first, before the
    throttle bit) reported 13-15 years. A transient is not a bound. Now: `http` is INCONCLUSIVE
    and retried on a second probe date; only a genuine `empty` counts as a miss, and TWO
    consecutive real misses are required before declaring the floor."""
    syms = a.symbols.split(",") if a.symbols else BREADTH
    print(f"depth probe — 2 probe dates/year, http=inconclusive (never a floor), "
          f"2 consecutive empty years = floor\n")
    for sym in syms:
        hits, misses, inconclusive, floor_year = [], 0, [], None
        for year in range(2026, 2003, -1):
            got = None
            for probe in (dt.date(year, 1, 15), dt.date(year, 6, 15)):
                while probe.weekday() >= 5:
                    probe += dt.timedelta(days=1)
                r = fetch_day(sym, probe, tries=5)
                if r["status"] == "ok" and len(r["rows"]) > 600:
                    got = "ok"
                    break
                if r["status"] == "http":
                    got = got or "http"
                elif r["status"] in ("empty", "scale", "decode"):
                    got = r["status"]
                time.sleep(1.0)
            if got == "ok":
                hits.append(year)
                misses = 0
            elif got == "http":
                inconclusive.append(year)   # ⚠ NOT a miss — the vendor throttled, not answered
                misses = 0
            else:
                misses += 1
                if misses >= 2:
                    floor_year = year + 2
                    break
            time.sleep(0.5)
        floor = min(hits) if hits else None
        span = f"{floor}→2026 ({2026 - floor + 1}y of probed coverage)" if floor else "NONE"
        note = f" · inconclusive years (throttled, NOT a bound): {inconclusive}" if inconclusive else ""
        print(f"  {sym:16s} {INSTRUMENTS[sym]['name']:7s} {span}"
              f"{'  floor confirmed by 2 empty years' if floor_year else '  probe range exhausted'}"
              f"{note}", flush=True)
    return 0


def cmd_pull(a):
    syms = a.symbols.split(",") if a.symbols else BREADTH
    lo = dt.date.fromisoformat(a.start)
    hi = dt.date.fromisoformat(a.end)
    days = weekdays(lo, hi)
    print(f"pull: {len(syms)} instrument(s) × {len(days)} weekdays "
          f"({lo}→{hi}) = {len(syms) * len(days)} vendor days")
    for sym in syms:
        # ⚠ RESUME IS SCHEMA-AWARE, NOT MERELY EXISTENCE-AWARE. A day cached under an older row
        # schema is NOT a cache hit: the 2026-08-12 volume fix means every file written before it
        # carries OHLC only, and a corpus where SOME days can compute VWAP and others cannot is
        # worse than one where none can — the days that drop out are not random, so any rule
        # needing volume silently selects on cache age. Keying the resume on the schema tag makes
        # the heal automatic for this bump and for every future one, with nobody remembering to
        # pass --force. `stale` is reported separately from `missing` so a re-fetch of 700 already
        # -present days is never mistaken for the feed serving duplicates.
        todo, stale = [], 0
        for d in days:
            p = _path(sym, d)
            if not os.path.exists(p):
                todo.append(d)
                continue
            try:
                blob = json.load(open(p))
            except (json.JSONDecodeError, UnicodeDecodeError):
                todo.append(d)
                continue
            if blob.get("status") == "ok" and blob.get("schema") != ROW_SCHEMA:
                todo.append(d)
                stale += 1
        if stale:
            print(f"  {sym:16s} ↻ {stale} day(s) cached under an older row schema → re-fetching")
        got = {"ok": 0, "empty": 0, "http": 0, "scale": 0, "decode": 0}
        t0 = time.time()
        with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
            for r in ex.map(lambda d: fetch_day(sym, d), todo):
                got[r["status"]] = got.get(r["status"], 0) + 1
        cached = len(days) - len(todo)
        print(f"  {sym:16s} cached {cached:4d} · fetched {len(todo):4d} → "
              f"{got} in {time.time() - t0:.0f}s")
        if got.get("scale"):
            print(f"     ⚠ SCALE VIOLATION on {sym} — instrument SUSPECT, excluded from the gate")
    return 0


def _rth_count(rows, spec):
    tz = zoneinfo.ZoneInfo(spec["tz"])
    h0, m0 = (int(x) for x in spec["rth"][0].split(":"))
    h1, m1 = (int(x) for x in spec["rth"][1].split(":"))
    lo, hi = dt.time(h0, m0), dt.time(h1, m1)
    return sum(1 for b in rows
               if lo <= dt.datetime.fromtimestamp(b["time"], tz).time() < hi)


def cmd_integrity(a):
    """The Phase-0 gate report, per instrument."""
    syms = a.symbols.split(",") if a.symbols else BREADTH
    lo, hi = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    days = weekdays(lo, hi)
    out = {}
    for sym in syms:
        spec = INSTRUMENTS[sym]
        stat = {"expected_weekdays": len(days), "present": 0, "empty": 0, "missing": 0,
                "full_1440": 0, "rth_full": 0, "rth_counts": [], "gaps_total": 0,
                "gap_days": 0, "weekend_rows": 0, "scale_violation": 0,
                "flat_all": 0, "bars_all": 0, "flat_rth": 0, "bars_rth": 0,
                "dst_days": [], "first": None, "last": None}
        expect_rth = None
        for d in days:
            p = _path(sym, d)
            if not os.path.exists(p):
                stat["missing"] += 1
                continue
            r = json.load(open(p))
            if r["status"] == "scale":
                stat["scale_violation"] += 1
                continue
            rows = r.get("rows", [])
            if not rows:
                stat["empty"] += 1
                continue
            stat["present"] += 1
            stat["first"] = stat["first"] or d.isoformat()
            stat["last"] = d.isoformat()
            if len(rows) == 1440:
                stat["full_1440"] += 1
            # gaps: a complete 1m day has consecutive 60s stamps
            g = sum(1 for i in range(1, len(rows))
                    if rows[i]["time"] - rows[i - 1]["time"] != 60)
            stat["gaps_total"] += g
            stat["gap_days"] += 1 if g else 0
            # ── WEEKEND BOUNDARY ──────────────────────────────────────────────────────────
            # ⚠ THE GL-42 TRAP, AGAIN, AND IT NEARLY PRODUCED A FALSE "EXCLUDED". A Dukascopy
            # day file is a UTC day: the file dated Monday spans Mon 00:00–23:59 UTC, which in
            # ET is SUNDAY 20:00 → Monday 19:59. Testing `weekday() >= 5` therefore flagged 2640
            # perfectly good Sunday-evening bars as weekend rows and excluded US100 outright.
            # That was our own calendar convention, not vendor error. The real weekend for a CFD
            # is the market's closed window — Fri 17:00 ET through Sun 17:00 ET — so that is what
            # is tested. Match the window before blaming the source.
            for b in rows:
                e = dt.datetime.fromtimestamp(b["time"], ET)
                wd, t = e.weekday(), e.time()
                if (wd == 4 and t >= dt.time(17, 0)) or wd == 5 or \
                   (wd == 6 and t < dt.time(17, 0)):
                    stat["weekend_rows"] += 1
            # ── FLAT BARS — the finding the weekend heuristic was distracting from ──────────
            # A 1m bar with high == low had no range at all. Outside hours that is the vendor
            # PADDING a closed market to a full 1440-row day; inside RTH it is implausible for a
            # liquid index and marks gap-filling. Measured on US100: 13.7% overall, 6.26% INSIDE
            # 09:30-16:00 ET. A backtest that walks padded bars trades a market that was shut, and
            # a stop "touched" on a filled bar never happened. Phase 2 must exclude them, so the
            # gate has to see them.
            itz = zoneinfo.ZoneInfo(spec["tz"])
            h0, m0 = (int(x) for x in spec["rth"][0].split(":"))
            h1, m1 = (int(x) for x in spec["rth"][1].split(":"))
            for b in rows:
                flat = b["high"] == b["low"]
                stat["bars_all"] += 1
                stat["flat_all"] += flat
                e = dt.datetime.fromtimestamp(b["time"], itz)
                if e.weekday() < 5 and dt.time(h0, m0) <= e.time() < dt.time(h1, m1):
                    stat["bars_rth"] += 1
                    stat["flat_rth"] += flat
            n = _rth_count(rows, spec)
            stat["rth_counts"].append(n)
            expect_rth = expect_rth or n
            # DST: the session's UTC OFFSET changes across the year. A day whose local RTH count
            # matches while its UTC start shifts is the proof the tz math is real, not hardcoded.
            # ★ Read in the INSTRUMENT's own tz — DE40 shifts on Europe/Berlin's dates, not ET's.
            off = dt.datetime.fromtimestamp(
                rows[0]["time"], zoneinfo.ZoneInfo(spec["tz"])).utcoffset()
            stat["dst_days"].append(off.total_seconds() / 3600)
        rc = sorted(stat["rth_counts"])
        stat["rth_median"] = rc[len(rc) // 2] if rc else 0
        stat["rth_full"] = sum(1 for n in rc if n >= stat["rth_median"])
        stat["utc_offsets_seen"] = sorted(set(stat.pop("dst_days")))
        stat.pop("rth_counts")
        out[sym] = stat
    if a.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"═══ PHASE 0 — DATA INTEGRITY ({lo} → {hi}, {len(days)} weekdays) ═══")
    for sym, s in out.items():
        spec = INSTRUMENTS[sym]
        # ★ THE GATE. Weekend rows are NOT a criterion — a Dukascopy file is a UTC day, so
        # legitimate Sunday-evening/Friday-evening ET bars appear by calendar convention, and
        # testing them excluded US100 outright on the first run. The criteria that bound what a
        # backtest can claim: the scale decoded, the days are actually there, and the RTH tape is
        # not substantially padded.
        flat_rth_pct = 100 * s["flat_rth"] / s["bars_rth"] if s["bars_rth"] else 0.0
        s["flat_rth_pct"] = round(flat_rth_pct, 2)
        s["flat_all_pct"] = round(100 * s["flat_all"] / s["bars_all"], 2) if s["bars_all"] else 0.0
        fails = []
        if s["scale_violation"]:
            fails.append("scale")
        if s["present"] < 0.9 * s["expected_weekdays"]:
            fails.append("coverage")
        if flat_rth_pct > 15:
            fails.append("padded-RTH")
        verdict = "EXCLUDED(" + ",".join(fails) + ")" if fails else "PASS"
        print(f"  {spec['name']:7s} {sym:16s} {verdict}")
        print(f"     days present {s['present']}/{s['expected_weekdays']} "
              f"(empty {s['empty']} · missing {s['missing']}) · 1440-bar days {s['full_1440']}")
        print(f"     RTH {spec['rth'][0]}-{spec['rth'][1]} {spec['tz']}: median {s['rth_median']}"
              f" min · gaps {s['gaps_total']} across {s['gap_days']} day(s)"
              f" · scale violations {s['scale_violation']}")
        print(f"     FLAT bars (high==low): {s['flat_all_pct']}% overall · "
              f"{s['flat_rth_pct']}% INSIDE RTH  ← Phase 2 must exclude these"
              f"   [weekend-window rows {s['weekend_rows']}, informational only]")
        print(f"     UTC offsets seen: {s['utc_offsets_seen']}"
              f"  (>1 value = the DST boundary is really crossed)")
    return 0


# ── THE THIRD INTEGRITY LEG IS NOT IN THIS REPO ──────────────────────────────────────
# The private tree carries an `agree` verb that scores this vendor tape against the
# author's own independently recorded bars and against live broker quotes, day by day.
# It is omitted here because it reads a private session corpus that cannot ship, and a
# verb that silently finds zero overlapping days would report "no disagreement" — which
# is the flattering reading of "no measurement". If you run this loader against your own
# vendor cache, that agreement check is yours to write; do not skip it.

def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("depth"); d.add_argument("--symbols")
    pl = sub.add_parser("pull")
    pl.add_argument("--symbols"); pl.add_argument("--from", dest="start", required=True)
    pl.add_argument("--to", dest="end", required=True); pl.add_argument("--workers", type=int, default=4)
    it = sub.add_parser("integrity")
    it.add_argument("--symbols"); it.add_argument("--from", dest="start", required=True)
    it.add_argument("--to", dest="end", required=True); it.add_argument("--json", action="store_true")
    a = p.parse_args()
    return {"depth": cmd_depth, "pull": cmd_pull, "integrity": cmd_integrity}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

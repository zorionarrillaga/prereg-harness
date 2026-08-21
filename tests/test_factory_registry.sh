#!/usr/bin/env bash
# test_factory_registry.sh — the EDGE FACTORY verbs prove they can return BOTH values (D048, H32).
# Chain: append/verify OK · tamper detected. Gauge --healthcheck: healthy 0 · broken chain 1 ·
# budget-exhausted-no-dormancy 1 · dormancy present 0. MDE refusal at the write.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HARNESS_FACTORY_DIR="$TMP/factory"
PASS=0; FAIL=0
chk() { # chk <desc> <want_rc> <got_rc>
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "✗ $1 (want rc=$2 got rc=$3)"; fi
}

mkdir -p "$HARNESS_FACTORY_DIR"
echo "spec: ORB-20 fork test, frozen" > "$TMP/spec.md"

# 1. register + verify OK
python3 "$REPO/bin/factory_registry.py" register --file "$TMP/spec.md" --kind fork-spec --name orb20 >/dev/null
python3 "$REPO/bin/factory_registry.py" verify >/dev/null; chk "chain verifies after register" 0 $?

# 2. kill verdict WITHOUT --mde is REFUSED
python3 "$REPO/bin/factory_registry.py" verdict --name orb20 --stage fork --outcome killed 2>/dev/null
chk "kill verdict without MDE refused" 2 $?

# 3. kill verdict WITH --mde accepted; chain still OK
python3 "$REPO/bin/factory_registry.py" verdict --name orb20 --stage fork --outcome killed --mde 0.22 >/dev/null
python3 "$REPO/bin/factory_registry.py" verify >/dev/null; chk "chain verifies after verdict" 0 $?

# 4. TAMPER a row -> verify FAILS (the mutation the chain exists to catch); restore -> OK
cp "$HARNESS_FACTORY_DIR/registry.jsonl" "$TMP/reg.bak"
sed -i '' 's/"outcome": "killed"/"outcome": "survived"/' "$HARNESS_FACTORY_DIR/registry.jsonl" 2>/dev/null \
  || sed -i 's/"outcome": "killed"/"outcome": "survived"/' "$HARNESS_FACTORY_DIR/registry.jsonl"
python3 "$REPO/bin/factory_registry.py" verify >/dev/null; chk "tampered row breaks the chain" 1 $?
python3 "$REPO/bin/edge_factory_gauge.py" --healthcheck >/dev/null
cat > "$HARNESS_FACTORY_DIR/budget.json" <<'EOF'
{"d_record":"D048","phase01_start":"2026-08-11","phase01_cap_days":14,"phase2_start":null,
 "phase2_gate":"test","phase2_budget_weeks":8,"phase2_budget_rounds":3,
 "mue_r_net":0.15,"mue_min_signals_per_week":2}
EOF
python3 "$REPO/bin/edge_factory_gauge.py" --healthcheck >/dev/null
chk "gauge ERRORS on broken chain" 1 $?
cp "$TMP/reg.bak" "$HARNESS_FACTORY_DIR/registry.jsonl"

# 5. healthy fixture -> gauge 0 (phase2 not started, inside phase01 cap window is not asserted:
#    phase01_start is in the past in real time, so pin it to today)
python3 - "$HARNESS_FACTORY_DIR/budget.json" <<'EOF'
import json, sys, datetime
p = sys.argv[1]; b = json.load(open(p))
b["phase01_start"] = datetime.date.today().isoformat()
json.dump(b, open(p, "w"))
EOF
python3 "$REPO/bin/edge_factory_gauge.py" --healthcheck >/dev/null
chk "gauge CLEAN on healthy state" 0 $?

# 6. budget EXHAUSTED (phase2 started 10 weeks ago), no dormancy -> 1
python3 - "$HARNESS_FACTORY_DIR/budget.json" <<'EOF'
import json, sys, datetime
p = sys.argv[1]; b = json.load(open(p))
b["phase2_start"] = (datetime.datetime.now().astimezone() - datetime.timedelta(weeks=10)).isoformat(timespec="seconds")
json.dump(b, open(p, "w"))
EOF
python3 "$REPO/bin/edge_factory_gauge.py" --healthcheck >/dev/null
chk "gauge ERRORS on exhausted budget w/o dormancy" 1 $?

# 7. dormancy record present -> 0 (the stopping rule EXECUTED is a success state)
echo "dormancy executed (test)" > "$HARNESS_FACTORY_DIR/DORMANCY.md"
python3 "$REPO/bin/edge_factory_gauge.py" --healthcheck >/dev/null
chk "gauge CLEAN once dormancy record exists" 0 $?

# 8. OMITTED IN THIS EXTRACTION. The private tree asserts here that a `dormant_pending_live`
#    obligation is not counted as debt while dormant and WAKES once live fills post-date its
#    stamp. That property belongs to an obligation ledger (`owed_check.py`) which is not part
#    of this harness, and a test whose subject is absent can only ever report the absence.
#    Deleted rather than skipped: a skipped test still prints, and a printed skip is how a
#    suite starts lying about its coverage.

# 9. A SURVIVOR CAN BE WITHDRAWN, and the gauge must stop reporting it. The registry is
#    append-only, so a retraction is a NEW verdict row on the same (name, stage) — a gauge that
#    reads every row as current can only ever OVERSTATE survivors, which is the one direction it
#    must never fail in. Both values proven: reported while it stands, gone once withdrawn.
python3 "$REPO/bin/factory_registry.py" register --file "$TMP/spec.md" --kind prereg --name wd >/dev/null
python3 "$REPO/bin/factory_registry.py" verdict --name wd --stage fork --outcome survived >/dev/null
python3 "$REPO/bin/edge_factory_gauge.py" | grep -q "survivors by stage: fork:1"
chk "gauge REPORTS a standing survivor" 0 $?
python3 "$REPO/bin/factory_registry.py" verdict --name wd --stage fork --outcome killed --mde 0.7 >/dev/null
python3 "$REPO/bin/edge_factory_gauge.py" | grep -q "survivors by stage: none"
chk "gauge DROPS a withdrawn survivor (latest verdict per name+stage wins)" 0 $?

echo "test_factory_registry: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]

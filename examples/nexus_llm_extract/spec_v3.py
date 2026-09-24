"""FORGE3 spec schema v3 (BP#43 §18.2, BP#41 mod §2.7, BP#42 mod ADDENDUM §2.6).

Required fields:
- bound_quad.{strategy_id, executor_id, fill_model_id, bracket_policy_id,
              risk_model_id, quad_hash}
- parity_status: one of {parity_validated, sim_upper_bound, sim_upper_bound_under_prior}
- paper_refs: list of arxiv ids / paper numbers contributing to primitives in this spec
- paper_lineage_hash: deterministic hash over sorted(paper_refs); surrogate feature
- n_trials_field: sweep size that produced this spec (multiple-testing accounting)

The `risk_model_id` slot was added 2026-04-25 (BP#47 roadmap §2c, PM-10
extension). Specs predating PM-10 default to `UNDECLARED_RISK_MODEL_v0`
on read, so `from_dict` is forward- AND backward-compatible with stamped
artefacts on disk that lack the field.

Any spec missing any of these fails `forge3 lint --require-quad` at write time.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

SPEC_SCHEMA_VERSION = "v3"


class ParityStatus(str, Enum):
    # Bound quad honest; HonestSim-under-live-data parity confirmed.
    PARITY_VALIDATED = "parity_validated"
    # Bound quad honest; HonestSim number, live parity NOT yet confirmed.
    SIM_UPPER_BOUND = "sim_upper_bound"
    # Bound quad honest but FillModel bucket is PRIOR_ONLY, not FITTED.
    SIM_UPPER_BOUND_UNDER_PRIOR = "sim_upper_bound_under_prior"
    # FillModel calibrated against live Rithmic SIM fills via the
    # CALIBRATION_PROBE artifact (BP#43 §17.5). Tier strictly between
    # SIM_UPPER_BOUND_UNDER_PRIOR and PARITY_VALIDATED — bucket-empirical
    # SIM fills are a massive upgrade over a synthesized prior, but they
    # are not live-money fills. The "_RITHMIC_SIM" suffix is structural,
    # not cosmetic; future calibrated tiers will declare their venue+tier
    # explicitly (e.g. CALIBRATED_BOUND_QUAD_RITHMIC_LIVE).
    CALIBRATED_BOUND_QUAD_RITHMIC_SIM = "calibrated_bound_quad_rithmic_sim"


class SpecSchemaError(ValueError):
    """Raised when a spec dict violates schema v3."""


UNDECLARED_RISK_MODEL = "UNDECLARED_RISK_MODEL_v0"


@dataclass(frozen=True)
class BoundQuadRef:
    strategy_id: str
    executor_id: str
    fill_model_id: str
    bracket_policy_id: str
    quad_hash: str  # 16-hex from honest_sim.BoundQuad
    # PM-10 5th slot (BP#47 §2c). Defaults to sentinel for back-compat with
    # specs stamped before 2026-04-25.
    risk_model_id: str = UNDECLARED_RISK_MODEL

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BoundQuadRef":
        required = {
            "strategy_id", "executor_id", "fill_model_id",
            "bracket_policy_id", "quad_hash",
        }
        missing = required - set(d.keys())
        if missing:
            raise SpecSchemaError(f"bound_quad missing fields: {sorted(missing)}")
        for k in required:
            v = d[k]
            if not isinstance(v, str) or not v or v == "?":
                raise SpecSchemaError(
                    f"bound_quad.{k} must be non-empty str, got {v!r}"
                )
        kwargs = {k: d[k] for k in required}
        # Optional 5th slot — older specs default to sentinel.
        rm = d.get("risk_model_id", UNDECLARED_RISK_MODEL)
        if not isinstance(rm, str) or not rm:
            raise SpecSchemaError(
                f"bound_quad.risk_model_id must be non-empty str, got {rm!r}"
            )
        kwargs["risk_model_id"] = rm
        return cls(**kwargs)


def compute_paper_lineage_hash(paper_refs: List[str]) -> str:
    """Deterministic hash over sorted paper_refs. 16-hex."""
    canonical = "\x1f".join(sorted(str(r) for r in paper_refs))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


@dataclass
class SpecV3:
    schema_version: str
    spec_id: str
    bound_quad: BoundQuadRef
    parity_status: ParityStatus
    paper_refs: List[str]
    paper_lineage_hash: str
    n_trials_field: int
    # Strategy parameters + primitives (grammar-emitted; opaque to schema).
    primitives: Dict[str, Any] = field(default_factory=dict)
    # Gate verdicts (filled by validator; empty on seed-time spec).
    gate_verdicts: Dict[str, Any] = field(default_factory=dict)
    # Metadata — cycle id, timestamps, grammar mutation lineage, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != SPEC_SCHEMA_VERSION:
            raise SpecSchemaError(
                f"schema_version must be {SPEC_SCHEMA_VERSION!r}, got "
                f"{self.schema_version!r}"
            )
        if not self.spec_id:
            raise SpecSchemaError("spec_id must be non-empty")
        if not isinstance(self.parity_status, ParityStatus):
            raise SpecSchemaError(
                f"parity_status must be ParityStatus, got {type(self.parity_status)}"
            )
        if not self.paper_refs:
            raise SpecSchemaError(
                "paper_refs must be non-empty (BP#41 mod §2.7 — every primitive "
                "traceable to source paper)"
            )
        expected_hash = compute_paper_lineage_hash(self.paper_refs)
        if self.paper_lineage_hash != expected_hash:
            raise SpecSchemaError(
                f"paper_lineage_hash mismatch: stored {self.paper_lineage_hash!r}, "
                f"computed {expected_hash!r}"
            )
        if self.n_trials_field < 1:
            raise SpecSchemaError(
                f"n_trials_field must be >= 1 (multiple-testing accounting "
                f"per BP#42 mod ADDENDUM §2.6), got {self.n_trials_field}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "spec_id": self.spec_id,
            "bound_quad": self.bound_quad.to_dict(),
            "parity_status": self.parity_status.value,
            "paper_refs": list(self.paper_refs),
            "paper_lineage_hash": self.paper_lineage_hash,
            "n_trials_field": self.n_trials_field,
            "primitives": self.primitives,
            "gate_verdicts": self.gate_verdicts,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpecV3":
        required = {
            "schema_version", "spec_id", "bound_quad", "parity_status",
            "paper_refs", "paper_lineage_hash", "n_trials_field",
        }
        missing = required - set(d.keys())
        if missing:
            raise SpecSchemaError(f"spec missing required fields: {sorted(missing)}")
        try:
            status = ParityStatus(d["parity_status"])
        except ValueError as e:
            raise SpecSchemaError(f"invalid parity_status: {e}") from e
        return cls(
            schema_version=d["schema_version"],
            spec_id=d["spec_id"],
            bound_quad=BoundQuadRef.from_dict(d["bound_quad"]),
            parity_status=status,
            paper_refs=list(d["paper_refs"]),
            paper_lineage_hash=d["paper_lineage_hash"],
            n_trials_field=int(d["n_trials_field"]),
            primitives=dict(d.get("primitives", {})),
            gate_verdicts=dict(d.get("gate_verdicts", {})),
            metadata=dict(d.get("metadata", {})),
        )


def load_spec(path: str) -> SpecV3:
    with open(path, "r", encoding="utf-8") as f:
        return SpecV3.from_dict(json.load(f))


def dump_spec(spec: SpecV3, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec.to_dict(), f, indent=2, sort_keys=True)
        f.write("\n")

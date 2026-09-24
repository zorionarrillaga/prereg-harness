#!/usr/bin/env python3
"""Translate a research target into Sharpe, sample-size and power geometry.

This is a cheap pre-search check. It touches no market outcomes and certifies no edge. Its job is
to expose targets that require implausible standardized edge or more independent observations than
the planned holdout can provide.

All inputs are in R-multiples. The confidence interval calculation uses a normal approximation and
the effective-sample fraction must be reduced when observations are clustered or dependent.
"""
import argparse
import math
from statistics import NormalDist


def annualized_sharpe(edge_r: float, signals_per_week: float, sd_r: float) -> float:
    """Independence upper bound for annualized Sharpe."""
    return edge_r / sd_r * math.sqrt(signals_per_week * 52.0)


def z_for_two_sided_confidence(confidence: float) -> float:
    return NormalDist().inv_cdf(0.5 + confidence / 2.0)


def z_for_power(power: float) -> float:
    return NormalDist().inv_cdf(power)


def required_effect(
    threshold_r: float,
    sd_r: float,
    n_effective: float,
    confidence: float,
    power: float,
) -> float:
    """True edge needed for the CI lower bound to clear threshold with requested power."""
    z = z_for_two_sided_confidence(confidence) + z_for_power(power)
    return threshold_r + z * sd_r / math.sqrt(n_effective)


def required_n(
    true_edge_r: float,
    threshold_r: float,
    sd_r: float,
    confidence: float,
    power: float,
) -> int:
    """Effective observations needed to clear threshold with requested power."""
    gap = true_edge_r - threshold_r
    if gap <= 0:
        raise ValueError("true edge must exceed the threshold")
    z = z_for_two_sided_confidence(confidence) + z_for_power(power)
    return math.ceil((z * sd_r / gap) ** 2)


def positive(parser, name, value):
    if value <= 0:
        parser.error(f"{name} must be greater than zero")


def probability(parser, name, value):
    if not 0 < value < 1:
        parser.error(f"{name} must be between zero and one")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge-r", type=float, default=0.15,
                        help="candidate mean net R per trade (default: 0.15)")
    parser.add_argument("--signals-per-week", type=float, default=2.0)
    parser.add_argument("--sd-r", type=float, default=1.0,
                        help="per-trade standard deviation in R (default: 1.0)")
    parser.add_argument("--holdout-weeks", type=float, default=30.0)
    parser.add_argument("--effective-fraction", type=float, default=1.0,
                        help="independent-equivalent fraction after clustering (default: 1.0)")
    parser.add_argument("--mue-r", type=float, default=0.15,
                        help="minimum useful net effect in R/trade (default: 0.15)")
    parser.add_argument("--power-target-r", type=float, default=0.30,
                        help="true edge whose required sample size is calculated (default: 0.30)")
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--power", type=float, default=0.80)
    args = parser.parse_args()

    for name in ("edge_r", "signals_per_week", "sd_r", "holdout_weeks", "mue_r"):
        positive(parser, name.replace("_", "-"), getattr(args, name))
    if not 0 < args.effective_fraction <= 1:
        parser.error("effective-fraction must be greater than zero and at most one")
    probability(parser, "confidence", args.confidence)
    probability(parser, "power", args.power)
    if args.power_target_r <= args.mue_r:
        parser.error("power-target-r must exceed mue-r")

    n_raw = args.signals_per_week * args.holdout_weeks
    n_effective = n_raw * args.effective_fraction
    sharpe = annualized_sharpe(args.edge_r, args.signals_per_week, args.sd_r)
    ic_like = args.edge_r / args.sd_r
    needed_edge = required_effect(
        args.mue_r, args.sd_r, n_effective, args.confidence, args.power
    )
    needed_n = required_n(
        args.power_target_r, args.mue_r, args.sd_r, args.confidence, args.power
    )
    needed_rate = needed_n / (args.holdout_weeks * args.effective_fraction)

    print("RESEARCH TARGET ARITHMETIC — pre-search, no market outcomes touched")
    print(f"candidate edge             {args.edge_r:+.3f} R/trade net")
    print(f"frequency                  {args.signals_per_week:.2f} signals/week")
    print(f"per-trade dispersion       {args.sd_r:.3f} R")
    print(f"standardized edge          {ic_like:.3f} per trade")
    print(f"annualized Sharpe          {sharpe:.2f}  (independence upper bound)")
    print()
    print(f"holdout                    {args.holdout_weeks:.1f} weeks x "
          f"{args.signals_per_week:.2f}/week = {n_raw:.1f} observations")
    print(f"effective fraction         {args.effective_fraction:.2f}")
    print(f"effective observations     {n_effective:.1f}")
    print(f"minimum useful effect      {args.mue_r:+.3f} R/trade")
    print(f"true edge required         {needed_edge:+.3f} R/trade for "
          f"{args.power:.0%} power to put the {args.confidence:.0%} CI lower bound above the MUE")
    print()
    print(f"when the true edge is      {args.power_target_r:+.3f} R/trade")
    print(f"and the CI must clear      {args.mue_r:+.3f} R/trade")
    print(f"effective n required       {needed_n}")
    print(f"raw signals/week required  {needed_rate:.2f} over {args.holdout_weeks:.1f} weeks")
    print()
    print("BOUND: normal approximation; dependence belongs in --effective-fraction. This")
    print("arithmetic can reject an infeasible search. It cannot validate a strategy.")


if __name__ == "__main__":
    main()

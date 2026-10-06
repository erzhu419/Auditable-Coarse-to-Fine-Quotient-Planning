"""Independent source/target replication of the unchanged V276 learner."""

from fractions import Fraction as F
import random

from .online_factor_repair_v276 import (
    ARMS, PHASES, SOURCE_PAIRS, SOURCE_FIT, SOURCE_AUDIT, OPERATORS,
    EPISODES_PER_PHASE, TRIALS_PER_EPISODE, COVERAGE_QUOTA, run_lifecycle,
)

SOURCE_SEEDS = tuple(27740100 + 100 * index for index in range(32))
SEEDS = tuple(27790100 + 100 * index for index in range(32))
BOOTSTRAP_DRAWS = 20_000
BOOTSTRAP_SEED = 27700001
CONTRASTS = (
    ("COVERED_REVISED", "PASSIVE_FIXED"),
    ("PASSIVE_REVISED", "PASSIVE_FIXED"),
    ("COVERED_FIXED", "PASSIVE_FIXED"),
    ("COVERED_REVISED", "COVERED_FIXED"),
    ("COVERED_REVISED", "PASSIVE_REVISED"),
)


def _percentile(ordered: list[float], probability: float) -> float:
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def paired_contrast(values: list[F]) -> dict:
    """Resample whole lifecycle differences, keeping the four-arm pairing."""
    rng = random.Random(BOOTSTRAP_SEED)
    floats = [float(value) for value in values]
    means = sorted(sum(rng.choices(floats, k=len(floats))) / len(floats) for _ in range(BOOTSTRAP_DRAWS))
    interval = [_percentile(means, 0.025), _percentile(means, 0.975)]
    return {
        "per_seed_regret_delta": list(map(str, values)),
        "mean_regret_delta": str(sum(values, F(0)) / len(values)),
        "ci95": interval,
        "improved_equal_worse": [sum(value < 0 for value in values), sum(value == 0 for value in values), sum(value > 0 for value in values)],
    }


def summarize(records: list[dict]) -> dict:
    summary = {}
    for arm in ARMS:
        totals = [record["totals"][arm] for record in records]
        summary[arm] = {
            "mean_executed_regret": str(sum((F(total["executed_regret"]) for total in totals), F(0)) / len(totals)),
            "mean_online_events": sum(sum(phase["executed_events"] for phase in total["phases"].values()) for total in totals) / len(totals),
            "mean_coverage_opportunities": sum(sum(phase["coverage_opportunities"] for phase in total["phases"].values()) for total in totals) / len(totals),
            "phases": {phase: str(sum((F(total["phases"][phase]["executed_regret"]) for total in totals), F(0)) / len(totals)) for phase in PHASES},
        }
    contrasts = {f"{left}_minus_{right}": paired_contrast([
        F(record["totals"][left]["executed_regret"]) - F(record["totals"][right]["executed_regret"])
        for record in records
    ]) for left, right in CONTRASTS}
    primary = contrasts["COVERED_REVISED_minus_PASSIVE_FIXED"]
    by_source = [{
        "source_seed": record["source_seed"], "seed": record["seed"],
        "initial_fields": record["initial_selection"]["selected_fields"],
        "totals": record["totals"],
        "primary_regret_delta": primary["per_seed_regret_delta"][index],
    } for index, record in enumerate(records)]
    source_rows = len(records) * len(SOURCE_PAIRS) * len(OPERATORS) * (SOURCE_FIT + SOURCE_AUDIT)
    online_events = sum(len(row["events"]) for record in records for arm in ARMS for row in record["arms"][arm])
    return {
        "summary": summary, "contrasts": contrasts, "by_source": by_source,
        "confirmation": "CONFIRMED_ON_COHORT" if primary["ci95"][1] < 0 else "NOT_CONFIRMED_ON_COHORT",
        "accounting": {"physical_source_observations": source_rows, "online_events_all_arms": online_events,
                       "start_opportunities_all_arms": len(records) * len(ARMS) * len(PHASES) * EPISODES_PER_PHASE * TRIALS_PER_EPISODE},
    }


def run_replication() -> dict:
    records = []
    for source_seed, seed in zip(SOURCE_SEEDS, SEEDS):
        records.append(run_lifecycle(source_seed, seed))
        print(f"completed {len(records)}/{len(SOURCE_SEEDS)} source_seed={source_seed} target_seed={seed}", flush=True)
    return {
        "schema": "acfqp.online_factor_confirmation.v277", "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "settings": {"source_seeds": SOURCE_SEEDS, "seeds": SEEDS, "arms": ARMS,
                     "phase_order": PHASES, "source_fit": SOURCE_FIT, "source_audit": SOURCE_AUDIT,
                     "episodes_per_phase": EPISODES_PER_PHASE, "trials_per_episode": TRIALS_PER_EPISODE,
                     "coverage_quota": COVERAGE_QUOTA, "algorithm": "unchanged V276 run_lifecycle",
                     "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap_seed": BOOTSTRAP_SEED,
                     "primary_endpoint": "whole lifecycle executed-policy regret including coverage cost",
                     "uncertainty_unit": "source lifecycle with paired arms"},
        "records": records, **summarize(records),
    }

"""Whole-model proposals and acceptance rules for the V78 learning trial.

Training excludes every episode numbered 4 modulo 5. Model construction and
assessment leave their inputs unchanged, so rejecting a proposal also rejects
its leaf-statistic changes. Decision acceptance concerns paired 32-step closed
loop utility on training-heldout roots; it is not a whole-game guarantee.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from math import fsum
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_lifelong_v77 import (
    Knowledge, POLICIES, _arrays, _fit, _predict, _refresh_leaves,
    _structure_changes,
)


QUERIES = ("reward", "risk_goal")
STRATA = ("old", "new")


def _prefix(records, checkpoint):
    records = list(records)
    if any(row["episode"] < 0 or row["episode"] >= checkpoint for row in records):
        raise ValueError("records must belong to the completed episode prefix")
    return records


def fit_candidate(records, checkpoint):
    """Fit one shared three-policy proposal; return ``(Knowledge, log)``.

    Operation counts belong to the returned log. The new model starts with
    empty prediction counts, allowing its training cost to be attributed once.
    """
    started = perf_counter()
    records = _prefix(records, checkpoint)
    counts = Counter(metadata_rows_read=len(records))
    trees, policy_logs = {}, {}
    for policy in POLICIES:
        training = [row for row in records
                    if row["policy"] == policy and row["episode"] % 5 != 4]
        if not training:
            raise ValueError(f"candidate has no training rows for {policy}")
        counts["training_rows_read"] += len(training)
        x, y = _arrays(training, counts)
        trees[policy] = _fit(x, y, counts)
        policy_logs[policy] = dict(training_rows=len(training),
            heldout_rows=sum(row["policy"] == policy and row["episode"] % 5 == 4
                             for row in records),
            nodes=len(trees[policy]["left"]),
            leaves=sum(node < 0 for node in trees[policy]["left"]))
    model = Knowledge("CANDIDATE", trees, checkpoint)
    return model, dict(checkpoint=checkpoint, policies=policy_logs,
                       counts=dict(counts), seconds=perf_counter() - started)


def refresh_fixed(incumbent, records, checkpoint):
    """Refresh training leaf means on a copy, preserving incumbent topology."""
    started = perf_counter()
    records = _prefix(records, checkpoint)
    counts = Counter(metadata_rows_read=len(records))
    trees = deepcopy(incumbent.trees)
    policy_logs = {}
    for policy in POLICIES:
        training = [row for row in records
                    if row["policy"] == policy and row["episode"] % 5 != 4]
        if not training:
            raise ValueError(f"fixed update has no training rows for {policy}")
        counts["training_rows_read"] += len(training)
        x, y = _arrays(training, counts)
        policy_logs[policy] = dict(training_rows=len(training),
            **_refresh_leaves(trees[policy], x, y, counts),
            **_structure_changes(incumbent.trees[policy], trees[policy]))
    model = Knowledge(incumbent.mode, trees, checkpoint)
    return model, dict(previous_checkpoint=incumbent.checkpoint,
        checkpoint=checkpoint, policies=policy_logs, counts=dict(counts),
        seconds=perf_counter() - started)


def mse_decision(incumbent, candidate, records, previous_checkpoint):
    """Compare complete models on old/new natural heldout vector MSE.

    Rows across policies receive equal weight. Neither the old model nor the
    proposal receives a leaf refresh or prediction-counter mutation here.
    The caller supplies natural-game records, excluding added rollout labels.
    """
    started = perf_counter()
    records = _prefix(records, candidate.checkpoint)
    counts = Counter(metadata_rows_read=len(records))
    losses, sizes, policy_sizes = {}, {}, {}
    for stratum in STRATA:
        heldout = [row for row in records if row["episode"] % 5 == 4
                   and (row["episode"] < previous_checkpoint) == (stratum == "old")]
        sizes[stratum] = len(heldout)
        counts["validation_rows_read"] += len(heldout)
        squared_error = dict(incumbent=0.0, candidate=0.0)
        policy_sizes[stratum] = {}
        for policy in POLICIES:
            rows = [row for row in heldout if row["policy"] == policy]
            policy_sizes[stratum][policy] = len(rows)
            if not rows:
                continue
            x, y = _arrays(rows, counts)
            for label, model in (("incumbent", incumbent), ("candidate", candidate)):
                error = _predict(model.trees[policy], x, counts) - y
                squared_error[label] += float(np.sum(error * error))
        losses[stratum] = {label: total / (3 * len(heldout)) if heldout else None
                            for label, total in squared_error.items()}
    accepted = bool(sizes["old"] and sizes["new"]
        and losses["new"]["candidate"] < losses["new"]["incumbent"]
        and losses["old"]["candidate"] <= losses["old"]["incumbent"] * 1.02 + 1e-12)
    return dict(previous_checkpoint=previous_checkpoint, checkpoint=candidate.checkpoint,
        validation_rows=sizes, validation_policy_rows=policy_sizes,
        validation_mse=losses, accepted=accepted, counts=dict(counts),
        seconds=perf_counter() - started)


def decision_acceptance(pairs):
    """Accept only new-query improvement with no observed old-query loss.

    Each row pairs incumbent and candidate continuation utility at one common
    root and seed. Both queries need old and new evidence. The new stratum must
    improve at least one query strictly; all four mean deltas must be nonnegative.
    """
    started = perf_counter()
    groups = {stratum: {query: [] for query in QUERIES} for stratum in STRATA}
    for row in pairs:
        groups[row["stratum"]][row["query"]].append(
            float(row["candidate_utility"]) - float(row["incumbent_utility"]))
    stats = {stratum: {query: dict(count=len(deltas),
        mean_delta=fsum(deltas) / len(deltas) if deltas else None)
        for query, deltas in queries.items()} for stratum, queries in groups.items()}
    complete = all(stats[s][q]["count"] for s in STRATA for q in QUERIES)
    accepted = bool(complete
        and all(stats[s][q]["mean_delta"] >= 0 for s in STRATA for q in QUERIES)
        and any(stats["new"][q]["mean_delta"] > 0 for q in QUERIES))
    return dict(strata=stats, complete_strata=bool(complete), accepted=accepted,
                pairs=sum(stats[s][q]["count"] for s in STRATA for q in QUERIES),
                seconds=perf_counter() - started)

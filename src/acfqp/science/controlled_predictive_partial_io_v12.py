"""Portable execution of the declared V12 policies and deterministic fallback."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .controlled_predictive_partial_v12 import BoardProfile, FrozenPolicy, Key, PartialCheckpoint
from .controlled_predictive_quotient_v1 import Query


SCHEMA = "controlled_predictive_partial_policy_v12"


def freeze_policy_payload(checkpoint: PartialCheckpoint, queries: Mapping[str, Query],
                          root: Key, metadata: dict | None = None) -> dict[str, Any]:
    names = tuple(queries)
    policies = checkpoint.frozen_policy.policies
    return {
        "schema": SCHEMA,
        "scope": "Execution of declared queries with a fixed greedy fallback",
        "fallback": "MAXIMUM_IMMEDIATE_MERGE_REWARD_THEN_ALPHABETICAL_ACTION",
        "metadata": metadata or {},
        "example_input": {"remaining_horizon": root[0], "board": list(root[1])},
        "queries": {name: asdict(queries[name]) for name in names},
        "budget": checkpoint.budget,
        "observed_row_count": len(checkpoint.known_rows),
        "root_intervals": {name: asdict(checkpoint.root_intervals[name]) for name in names},
        "active_policies": [
            {"horizon": key[0], "board": list(key[1]),
             "actions": {name: policies[name][key] for name in names}}
            for key, observed in sorted(checkpoint.profiles.items()) if observed.status == "ACTIVE"
        ],
        "known_terminals": [
            {"horizon": key[0], "board": list(key[1]), "status": observed.status}
            for key, observed in sorted(checkpoint.profiles.items()) if observed.status != "ACTIVE"
        ],
    }


def restore_policy_payload(payload: Mapping[str, Any]) -> FrozenPolicy:
    if payload["schema"] != SCHEMA:
        raise ValueError("not a V12 partial-policy artifact")
    policies = {name: {} for name in payload["queries"]}
    for record in payload["active_policies"]:
        key = (record["horizon"], tuple(record["board"]))
        for name in policies:
            policies[name][key] = record["actions"][name]
    terminals = {(record["horizon"], tuple(record["board"])):
                 BoardProfile(record["status"], (), (), 0)
                 for record in payload["known_terminals"]}
    return FrozenPolicy(policies, terminals)

"""Source empirical Q values used only to prioritize target acquisition ties."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
from time import perf_counter
from typing import Any, Mapping

from .controlled_predictive_encoder_v7 import Code, RuleEncoder, TrainingModel
from .controlled_predictive_encoder_v8 import fit_constraint_encoder
from .controlled_predictive_encoder_runtime_v8 import compile_encoded
from .controlled_predictive_encoder_runtime_v11 import profile, feature_work_summary
from .controlled_predictive_quotient_v1 import CompiledModel, FiniteModel, Outcome, Query, plan

Key = tuple[int, tuple[int, ...]]


@dataclass(frozen=True)
class SourcePriorBuild:
    encoder: RuleEncoder
    compiled: CompiledModel
    code_to_cell: dict[Code, int]
    q_by_query: dict[str, dict[Code, dict[str, float]]]
    queries: dict[str, Query]
    diagnostics: dict[str, Any]

    def make_priority(self, *, shuffled: bool = False) -> SourcePriority:
        return SourcePriority(self, shuffled=shuffled)


class SourcePriority:
    """One partial arm's source-code cache and priority lookup accounting."""

    def __init__(self, build: SourcePriorBuild, *, shuffled: bool = False):
        self.build = build
        self.shuffled = shuffled
        self._query_names = {query: name for name, query in build.queries.items()}
        self._codes: dict[Key, Code] = {}
        self._work: Counter = Counter()
        self._elapsed_seconds = 0.0

    def __call__(self, key: Key, query: Query) -> dict[str, float]:
        started = perf_counter()
        self._work["priority_callback_calls"] += 1
        if key in self._codes:
            code = self._codes[key]
            self._work["priority_code_cache_hits"] += 1
        else:
            self._work["priority_code_cache_misses"] += 1
            horizon, board = key
            group, features = profile(board, horizon, self._work)
            code = self.build.encoder._encode_profile(group, features, self._work)
            self._codes[key] = code
        name = self._query_names.get(query)
        values = self.build.q_by_query.get(name, {}).get(code, {})
        if name is None:
            self._work["missing_source_query_calls"] += 1
        elif not values:
            self._work["missing_source_code_calls"] += 1
        actions = tuple(sorted(code[2]))
        result = {action: values.get(action, 0.0) for action in actions}
        self._work["source_priority_action_values_returned"] += len(actions)
        self._work["missing_source_action_values"] += sum(action not in values for action in actions)
        if self.shuffled and actions:
            original = result
            result = {action: original[actions[(index + 1) % len(actions)]]
                      for index, action in enumerate(actions)}
            self._work["shuffled_priority_vectors_returned"] += 1
        self._elapsed_seconds += perf_counter() - started
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {
            "mode": "shuffled_source_priority" if self.shuffled else "source_priority",
            "cached_state_keys": len(self._codes),
            "work_counts": dict(self._work),
            "encoding_feature_work": feature_work_summary(self._work),
            "elapsed_seconds": self._elapsed_seconds,
            "timing_scope": "Already included in the caller's prior callback time; do not add twice.",
            "cache_scope": "One partial arm acquisition trajectory only; independent across arms and runs.",
            "information_scope": "Tie ordering only; these values are not target dynamics or target bounds.",
        }


def _source_union(training: tuple[TrainingModel, ...]) -> TrainingModel:
    layers, terminal, rows, boards = {}, {}, {}, {}
    roots = []
    for item in training:
        mapping = {state: len(layers) + offset for offset, state in enumerate(sorted(item.empirical.layers))}
        for state, renamed in mapping.items():
            layers[renamed] = item.empirical.layers[state]
            terminal[renamed] = item.empirical.terminal[state]
            boards[renamed] = item.boards[state]
        for (state, action), outcomes in item.empirical.rows.items():
            rows[mapping[state], action] = tuple(
                Outcome(outcome.probability, mapping[outcome.next_state], outcome.reward)
                for outcome in outcomes)
        roots.extend(mapping[root] for root in item.empirical.roots)
    return TrainingModel("declared_source_union", FiniteModel(layers, terminal, rows, tuple(roots)), boards)


def fit_source_prior(training: list[TrainingModel] | tuple[TrainingModel, ...],
                     queries: Mapping[str, Query]) -> SourcePriorBuild:
    """Fit and plan only caller-supplied source empirical data, without resampling."""
    started = perf_counter()
    training = tuple(training)
    fit_started = perf_counter()
    fitted = fit_constraint_encoder(training)
    fit_seconds = perf_counter() - fit_started
    union_started = perf_counter()
    union = _source_union(training)
    union_seconds = perf_counter() - union_started
    compile_started = perf_counter()
    compiled = compile_encoded(union.empirical, union.boards, fitted.encoder)
    compile_seconds = perf_counter() - compile_started
    q_by_query = {}
    query_diagnostics = {}
    for name, query in queries.items():
        plan_started = perf_counter()
        solution = plan(compiled.compiled, query)
        planning_seconds = perf_counter() - plan_started
        q_started = perf_counter()
        by_cell: dict[int, dict[str, float]] = {}
        q_counts: Counter = Counter()
        for (cell, action), row in sorted(compiled.compiled.rows.items()):
            by_cell.setdefault(cell, {})[action] = math.fsum(
                outcome.probability * (query.reward_weight * outcome.reward + solution.values[outcome.next_state])
                for outcome in row)
            q_counts["state_action_rows"] += 1
            q_counts["outcomes"] += len(row)
        q_by_query[name] = {code: by_cell[cell] for code, cell in compiled.code_to_cell.items() if cell in by_cell}
        query_diagnostics[name] = {
            "planning_seconds": planning_seconds, "planning_counts": solution.counts,
            "q_extraction_seconds": perf_counter() - q_started, "q_extraction_counts": dict(q_counts),
        }
    inventory_started = perf_counter()
    q_payload = [[name, [[code, sorted(actions.items())] for code, actions in sorted(values.items())]]
                 for name, values in q_by_query.items()]
    q_bytes = len(json.dumps(q_payload, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    inventory_seconds = perf_counter() - inventory_started
    diagnostics = {
        "source_model_names": [item.name for item in training],
        "source_model_count": len(training),
        "source_union_state_records": len(union.empirical.layers),
        "source_union_action_rows": len(union.empirical.rows),
        "source_union_successor_entries": sum(len(row) for row in union.empirical.rows.values()),
        "source_union_root_count": len(union.empirical.roots),
        "source_fit": fitted.diagnostics, "source_compile": compiled.diagnostics,
        "source_queries": query_diagnostics,
        "source_fit_seconds": fit_seconds, "source_union_seconds": union_seconds,
        "source_compile_seconds": compile_seconds,
        "source_query_planning_seconds": math.fsum(row["planning_seconds"] for row in query_diagnostics.values()),
        "source_q_extraction_seconds": math.fsum(row["q_extraction_seconds"] for row in query_diagnostics.values()),
        "q_table_compact_json_bytes": q_bytes, "q_inventory_serialization_seconds": inventory_seconds,
        "build_seconds": perf_counter() - started,
        "sampling_scope": "Input rows are caller-acquired source observations; this function performs no draws.",
        "state_union_rule": "Disjoint source state IDs; each source kernel and root retained before rule pooling.",
        "priority_scope": "Source Q is used only for exact acquisition ties; missing query/code/action returns zero.",
    }
    return SourcePriorBuild(fitted.encoder, compiled.compiled, compiled.code_to_cell,
                            q_by_query, dict(queries), diagnostics)

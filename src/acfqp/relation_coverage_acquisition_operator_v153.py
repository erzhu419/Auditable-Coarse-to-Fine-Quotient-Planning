"""Observation-derived relation coverage before generic path backtracking."""

from __future__ import annotations

from types import FunctionType
from typing import Any, Iterator

from acfqp import anonymous_relational_factor_bank_acquisition_v148 as v148
from acfqp import construction_k7_domain_registry_extension_v153 as domains
from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground


def _clone(function, namespace):
    clone = FunctionType(function.__code__, namespace, name=function.__name__, argdefs=function.__defaults__, closure=function.__closure__)
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _relation_from_initial_batches(adapter, observations):
    width = len(adapter.catalogue[0].fields)
    state_width = len(observations[0][2][0].pre)
    candidates = []
    for field in range(width):
        for coordinate in range(state_width):
            relation = {}
            valid = True
            for _state, key, batch, _successors in observations:
                value = adapter.catalogue[key].fields[field]
                deltas = {row.post[coordinate] - row.pre[coordinate] for row in batch}
                if len(deltas) != 1 or value in relation and relation[value] != next(iter(deltas)):
                    valid = False
                    break
                relation[value] = next(iter(deltas))
            values = tuple(relation.values())
            catalogue_support = {action.fields[field] for action in adapter.catalogue}
            if (
                valid
                and len(relation) == len(observations)
                and set(relation) == catalogue_support
                and len(set(values)) == len(values)
                and min(values) > 0
            ):
                candidates.append((-(max(values) - min(values)), field, coordinate, relation))
    if not candidates:
        raise ValueError("V153 raw initial observations exposed no positive relation coverage")
    _range, field, coordinate, relation = min(candidates)
    return field, coordinate, relation


def relation_coverage_then_path_stream_v153(adapter: Any) -> Iterator[tuple[Any, ...]]:
    initial = adapter.initial()
    transition_index = 0
    queried = set()
    observations = []
    for action in adapter.actions(initial):
        key = adapter.action_key(action)
        batch = ground._transition_batch(adapter, initial, key, transition_index)  # noqa: SLF001
        transition_index += len(batch)
        successors = tuple(outcome.next_state for outcome in adapter.kernel.step(initial, action))
        observations.append((initial, key, batch, successors))
        queried.add((initial, key))
        yield batch
    field, _coordinate, relation = _relation_from_initial_batches(adapter, observations)
    best = max(observations, key=lambda item: (relation[adapter.catalogue[item[1]].fields[field]], -item[1]))
    active = tuple(state for state in best[3] if adapter.active(state))
    current = min(active, key=adapter.encode) if active else None
    while current is not None and adapter.active(current):
        actions = tuple(adapter.actions(current))
        known = tuple(
            action
            for action in actions
            if adapter.catalogue[adapter.action_key(action)].fields[field] in relation
        )
        if not known:
            break
        action = max(
            known,
            key=lambda row: (
                relation[adapter.catalogue[adapter.action_key(row)].fields[field]],
                -adapter.action_key(row),
            ),
        )
        key = adapter.action_key(action)
        batch = ground._transition_batch(adapter, current, key, transition_index)  # noqa: SLF001
        transition_index += len(batch)
        queried.add((current, key))
        yield batch
        active = tuple(outcome.next_state for outcome in adapter.kernel.step(current, action) if adapter.active(outcome.next_state))
        current = min(active, key=adapter.encode) if active else None

    seen = set()

    def visit(state):
        nonlocal transition_index
        if state in seen:
            return
        seen.add(state)
        for action in adapter.actions(state):
            key = adapter.action_key(action)
            if (state, key) not in queried:
                batch = ground._transition_batch(adapter, state, key, transition_index)  # noqa: SLF001
                transition_index += len(batch)
                queried.add((state, key))
                yield batch
            for outcome in adapter.kernel.step(state, action):
                if adapter.active(outcome.next_state):
                    yield from visit(outcome.next_state)

    yield from visit(initial)


_RUN_GLOBALS = dict(v148.__dict__)
_RUN_GLOBALS["fair_witness_blind_path_first_stream_v129r1"] = relation_coverage_then_path_stream_v153
_RUN_ADAPTIVE = _clone(v148.acquire_matched_anonymous_relational_factor_bank_arms_v148, _RUN_GLOBALS)


def acquire_matched_relation_coverage_arms_v153(adapter, bank_raw, verification_raw, config):
    arms = _RUN_ADAPTIVE(adapter, bank_raw, verification_raw, config)
    wrapped = {}
    for name, arm in arms.items():
        source = arm["document"]
        payload = {
            **{key: value for key, value in source.items() if key not in {"schema", "acquisition_id", "fair_witness_blind_path_first_backtracking"}},
            "schema": "acfqp.relation_coverage_acquisition_arm.v153",
            "source_v148_acquisition_id": source["acquisition_id"],
            "fair_witness_blind_path_first_backtracking": False,
            "observation_derived_relation_coverage_then_path_backtracking": True,
            "initial_action_relation_support_exhausted_without_generation_witness": True,
            "relation_field_and_delta_coordinate_selected_by_exact_dependency_rule": True,
            "adaptive_action_choice_uses_only_previously_observed_anonymous_relation": True,
            "operator_changes_query_order_not_model_hypothesis_pool_or_stop_rule": True,
        }
        wrapped[name] = {
            **arm,
            "document": {
                **payload,
                "acquisition_id": domains.extension_content_id_v153(domains.CONSTRUCTION_K7_ACQUISITION_V153_DOMAIN, payload),
            },
        }
    return wrapped


__all__ = ("acquire_matched_relation_coverage_arms_v153", "relation_coverage_then_path_stream_v153")

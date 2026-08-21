"""Standalone generic model-epoch state and incremental receipts V125."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v125 as domains
from acfqp import generic_compiled_quotient_model_v123 as generic
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4, FlatRawTransitionV4
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class StandaloneGenericModelEpochV125Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise StandaloneGenericModelEpochV125Error(message)


def _deduplicate(rows: tuple[FlatRawTransitionV4, ...]) -> tuple[FlatRawTransitionV4, ...]:
    unique = {(row.pre, row.action.key, row.post): row for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def _raw_key(row: FlatRawTransitionV4) -> tuple[tuple[int, ...], int, tuple[int, ...]]:
    return row.pre, row.action.key, row.post


def _canonical_actions(candidate, catalogue):
    return tuple(
        FlatRawActionV4(
            action.key,
            tuple(action.fields[index] for index in candidate.layout.action_canonical_to_raw),
        )
        for action in catalogue
    )


def _model_document(
    candidate: PartialFactorCandidateV15,
    raw_keys,
    contexts,
    edges,
    terminal_memberships,
    checks: int,
) -> dict[str, Any]:
    historical = generic._model_document_v123(  # noqa: SLF001
        candidate, raw_keys, contexts, edges, terminal_memberships, checks
    )
    payload = {
        **{key: value for key, value in historical.items() if key != "quotient_graph_id"},
        "schema": "acfqp.standalone_generic_model_epoch.v125",
        "recursive_generic_program_compiler": True,
        "legacy_shape_specific_model_builder_called": False,
        "retained_v113_state_carrier_present": False,
    }
    return {
        **payload,
        "quotient_graph_id": domains.extension_content_id_v125(
            domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_STATE_V125_DOMAIN,
            payload,
        ),
    }


def compile_standalone_generic_model_v125(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    if type(candidate) is not PartialFactorCandidateV15 or type(observed_rows) is not tuple or not observed_rows or type(catalogue) is not tuple or not catalogue:
        _fail("V125 compiler inventory changed")
    rows = _deduplicate(observed_rows)
    edges, terminal, contexts, _accepting, checks = generic._project_rows_v123(candidate, rows, catalogue)  # noqa: SLF001
    return _model_document(candidate, frozenset(_raw_key(row) for row in rows), contexts, edges, terminal, checks)


def _state_payload(model, rules, raw_keys):
    inventory = [
        {"pre": list(pre), "action_key": action, "post": list(post)}
        for pre, action, post in sorted(raw_keys)
    ]
    return {
        "generic_model_epoch_id": model["quotient_graph_id"],
        "terminal_projection_rule": [dict(row) for row in rules],
        "raw_row_identity_count": len(raw_keys),
        "raw_row_identity_sha256": hashlib.sha256(canonical_json_bytes(inventory)).hexdigest(),
        "retained_v113_state_carrier_present": False,
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StandaloneGenericModelEpochStateV125:
    _issuer: object = field(repr=False, compare=False)
    candidate_id: str
    layout_id: str
    raw_keys: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]]
    contexts: frozenset[tuple[tuple[int, ...], int]]
    edges: frozenset[tuple[tuple[int, ...], int, tuple[int, ...]]]
    terminal_memberships: frozenset[tuple[tuple[int, ...], str]]
    accepting_values: tuple[tuple[int, tuple[int, ...]], ...]
    projected_program_checks: int
    model_bytes: bytes = field(repr=False)
    terminal_rules_bytes: bytes = field(repr=False)
    state_id: str

    @property
    def model(self) -> dict[str, Any]:
        return loads_canonical_json(self.model_bytes)

    @property
    def terminal_rules(self) -> tuple[dict[str, Any], ...]:
        value = loads_canonical_json(self.terminal_rules_bytes)
        if type(value) is not list:
            _fail("V125 terminal rule bytes changed")
        return tuple(value)


def verify_standalone_generic_model_state_v125(state, candidate, catalogue):
    if (
        type(state) is not StandaloneGenericModelEpochStateV125
        or state._issuer is not _ISSUER
        or type(candidate) is not PartialFactorCandidateV15
        or type(catalogue) is not tuple
        or not catalogue
        or state.candidate_id != candidate.public_document["candidate_id"]
        or state.layout_id != candidate.public_document["layout"]["layout_id"]
    ):
        _fail("V125 model-state authority changed")
    model = _model_document(candidate, state.raw_keys, state.contexts, state.edges, state.terminal_memberships, state.projected_program_checks)
    rules = generic._terminal_rules_v123(candidate, state.accepting_values, _canonical_actions(candidate, catalogue))  # noqa: SLF001
    payload = _state_payload(model, rules, state.raw_keys)
    expected = domains.extension_content_id_v125(
        domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_STATE_V125_DOMAIN,
        payload,
    )
    if canonical_json_bytes(model) != state.model_bytes or canonical_json_bytes(list(rules)) != state.terminal_rules_bytes or state.state_id != expected:
        _fail("V125 model-state reconstruction changed")
    return model, rules


def _make_state(candidate, catalogue, *, raw_keys, contexts, edges, terminal_memberships, accepting_values, projected_program_checks):
    model = _model_document(candidate, raw_keys, contexts, edges, terminal_memberships, projected_program_checks)
    rules = generic._terminal_rules_v123(candidate, accepting_values, _canonical_actions(candidate, catalogue))  # noqa: SLF001
    payload = _state_payload(model, rules, raw_keys)
    state = StandaloneGenericModelEpochStateV125(
        _ISSUER,
        candidate.public_document["candidate_id"],
        candidate.public_document["layout"]["layout_id"],
        raw_keys,
        contexts,
        edges,
        terminal_memberships,
        accepting_values,
        projected_program_checks,
        canonical_json_bytes(model),
        canonical_json_bytes(list(rules)),
        domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_STATE_V125_DOMAIN, payload),
    )
    verify_standalone_generic_model_state_v125(state, candidate, catalogue)
    return state


def initialize_standalone_generic_model_v125(candidate, observed_rows, catalogue):
    if type(candidate) is not PartialFactorCandidateV15 or type(observed_rows) is not tuple or not observed_rows or type(catalogue) is not tuple or not catalogue:
        _fail("V125 bootstrap inventory changed")
    rows = _deduplicate(observed_rows)
    edges, terminal, contexts, accepting, checks = generic._project_rows_v123(candidate, rows, catalogue)  # noqa: SLF001
    state = _make_state(
        candidate,
        catalogue,
        raw_keys=frozenset(_raw_key(row) for row in rows),
        contexts=contexts,
        edges=edges,
        terminal_memberships=terminal,
        accepting_values=accepting,
        projected_program_checks=checks,
    )
    writes = len(edges) + len(terminal) + len(contexts) + sum(len(values) for _target, values in accepting)
    payload = {
        "schema": "acfqp.standalone_generic_model_bootstrap.v125",
        "successor_state_id": state.state_id,
        "generic_model_epoch_id": state.model["quotient_graph_id"],
        "bootstrap_raw_identity_checks": len(observed_rows),
        "bootstrap_unique_raw_rows": len(rows),
        "bootstrap_projected_program_checks": checks,
        "bootstrap_projection_index_writes": writes,
        "bootstrap_compilation_events": len(observed_rows) + checks + writes,
        "retained_v113_state_carrier_present": False,
        "ground_transition_accessed_during_abstract_search": False,
        "model_used_as_safety_authority": False,
    }
    return state, {**payload, "bootstrap_receipt_id": domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_BOOTSTRAP_V125_DOMAIN, payload)}


def advance_standalone_generic_model_v125(state, candidate, new_rows, catalogue):
    previous_model, _rules = verify_standalone_generic_model_state_v125(state, candidate, catalogue)
    if type(new_rows) is not tuple:
        _fail("V125 delta inventory changed")
    unique_input = _deduplicate(new_rows)
    novel = tuple(row for row in unique_input if _raw_key(row) not in state.raw_keys)
    edges, terminal, contexts, accepting_delta, checks = generic._project_rows_v123(candidate, novel, catalogue)  # noqa: SLF001
    accepting: dict[int, set[int]] = defaultdict(set)
    for target, values in state.accepting_values:
        accepting[target].update(values)
    accepting_insertions = 0
    for target, values in accepting_delta:
        before = len(accepting[target])
        accepting[target].update(values)
        accepting_insertions += len(accepting[target]) - before
    next_state = _make_state(
        candidate,
        catalogue,
        raw_keys=state.raw_keys | frozenset(_raw_key(row) for row in novel),
        contexts=state.contexts | contexts,
        edges=state.edges | edges,
        terminal_memberships=state.terminal_memberships | terminal,
        accepting_values=tuple((target, tuple(sorted(values))) for target, values in sorted(accepting.items())),
        projected_program_checks=state.projected_program_checks + checks,
    )
    edge_inserts = len(next_state.edges) - len(state.edges)
    terminal_inserts = len(next_state.terminal_memberships) - len(state.terminal_memberships)
    context_inserts = len(next_state.contexts) - len(state.contexts)
    writes = edge_inserts + terminal_inserts + context_inserts + accepting_insertions
    payload = {
        "schema": "acfqp.standalone_generic_model_update.v125",
        "previous_successor_state_id": state.state_id,
        "current_successor_state_id": next_state.state_id,
        "previous_generic_model_epoch_id": previous_model["quotient_graph_id"],
        "current_generic_model_epoch_id": next_state.model["quotient_graph_id"],
        "delta_input_raw_row_count": len(new_rows),
        "delta_unique_input_raw_row_count": len(unique_input),
        "delta_novel_raw_row_count": len(novel),
        "delta_raw_identity_checks": len(new_rows),
        "delta_projected_program_checks": checks,
        "delta_projected_edge_insertions": edge_inserts,
        "delta_terminal_membership_insertions": terminal_inserts,
        "delta_ground_context_insertions": context_inserts,
        "delta_accepting_value_insertions": accepting_insertions,
        "delta_projection_index_writes": writes,
        "incremental_compilation_events": len(new_rows) + checks + writes,
        "model_identity_changed": previous_model["quotient_graph_id"] != next_state.model["quotient_graph_id"],
        "only_novel_certificate_local_rows_projected": True,
        "previous_compiled_rows_not_replayed": True,
        "retained_v113_state_carrier_present": False,
        "ground_transition_accessed_during_abstract_search": False,
        "model_used_as_safety_authority": False,
    }
    return next_state, {**payload, "update_receipt_id": domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_UPDATE_V125_DOMAIN, payload)}


def verify_standalone_generic_model_full_rebuild_v125(state, candidate, all_rows, catalogue, *, update_receipt: Mapping[str, Any] | None):
    model, rules = verify_standalone_generic_model_state_v125(state, candidate, catalogue)
    if type(all_rows) is not tuple or not all_rows:
        _fail("V125 full rebuild inventory changed")
    rows = _deduplicate(all_rows)
    full_model = compile_standalone_generic_model_v125(candidate, rows, catalogue)
    edges, terminal, contexts, accepting, checks = generic._project_rows_v123(candidate, rows, catalogue)  # noqa: SLF001
    full_rules = generic._terminal_rules_v123(candidate, accepting, _canonical_actions(candidate, catalogue))  # noqa: SLF001
    writes = len(edges) + len(terminal) + len(contexts) + sum(len(values) for _target, values in accepting)
    full_events = len(all_rows) + checks + writes
    if model != full_model or rules != full_rules or state.raw_keys != frozenset(_raw_key(row) for row in rows):
        _fail("V125 incremental state differs from full generic rebuild")
    incremental_events = full_events if update_receipt is None else update_receipt.get("incremental_compilation_events")
    if type(incremental_events) is not int or incremental_events < 0:
        _fail("V125 incremental accounting changed")
    payload = {
        "schema": "acfqp.standalone_generic_model_full_rebuild_match.v125",
        "successor_state_id": state.state_id,
        "generic_model_epoch_id": model["quotient_graph_id"],
        "update_receipt_id": None if update_receipt is None else update_receipt.get("update_receipt_id"),
        "incremental_compilation_events": incremental_events,
        "matched_full_rebuild_raw_identity_checks": len(all_rows),
        "matched_full_rebuild_projected_program_checks": checks,
        "matched_full_rebuild_projection_index_writes": writes,
        "matched_full_rebuild_compilation_events": full_events,
        "compilation_events_avoided_against_full_rebuild": full_events - incremental_events,
        "model_bytes_exactly_equal_full_generic_rebuild": True,
        "model_bytes_exactly_equal_full_v105_rebuild": True,
        "legacy_named_v105_match_field_is_sequence_compatibility_alias": True,
        "terminal_projection_rule_exactly_equal_full_rebuild": True,
        "raw_row_identity_inventory_exactly_equal_full_rebuild": True,
        "matched_control_compute_not_charged_to_incremental_arm": True,
        "retained_v113_state_carrier_present": False,
        "model_used_as_safety_authority": False,
    }
    return {**payload, "match_receipt_id": domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_MATCH_V125_DOMAIN, payload)}


__all__ = (
    "StandaloneGenericModelEpochStateV125",
    "advance_standalone_generic_model_v125",
    "compile_standalone_generic_model_v125",
    "initialize_standalone_generic_model_v125",
    "verify_standalone_generic_model_full_rebuild_v125",
    "verify_standalone_generic_model_state_v125",
)

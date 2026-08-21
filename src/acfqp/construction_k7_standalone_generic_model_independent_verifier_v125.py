"""Producer-free verification of the standalone V125 model carrier.

The verifier deliberately does not import the V125 producer, campaign core,
sequence, state carrier, or generic compiled-model producer.  It reconstructs
every V125 model epoch and receipt from the retained raw transition rows.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_cross_family_generic_compiler_independent_verifier_v124 as previous
from acfqp import construction_k7_generic_quotient_compiler_independent_verifier_v123r1 as generic
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "6ab13a2f2b29c0b342939c1b9923bdbcbb274140e09d67e003a456046984893d"
CAMPAIGN_BYTE_COUNT = 1_439_156
CAMPAIGN_SHA256 = "87534f14bacebf2870045244c22b3bbd23fc12f91e99ada08c9f0098ac5400f3"
PREREGISTRATION_ID = "4ca6082580322556781685581428cde138d7c4797cf41ebd4e825500d53d7c2c"
V124_CAMPAIGN_ID = previous.CAMPAIGN_ID
V124_VERIFICATION_ID = previous.VERIFICATION_ID
EXPECTED_FAMILY = "STOCHASTIC_INVENTORY_ASSEMBLY"
EXPECTED_SEEDS = (1_040_101, 1_040_102)
EXPECTED_EPISODES = (299, 300, 301)
VERIFICATION_ID = "e0668e1f61be2d158a75afc07e694755df1d64a1114474c234a018c7453c4982"
EXPECTED_CANONICAL_BYTE_COUNT = 3_809
EXPECTED_CANONICAL_SHA256 = "12bbd756138f1344b008ffc94fbeddadd7defa1f216699c5754c1fe805d126fb"


_DOMAINS = {
    "campaign": "acfqp:construction-k7-standalone-generic-model-campaign:v125",
    "occurrence": "acfqp:construction-k7-standalone-generic-model-occurrence:v125",
    "sequence": "acfqp:construction-k7-standalone-generic-model-sequence:v125",
    "state": "acfqp:construction-k7-standalone-generic-model-state:v125",
    "bootstrap": "acfqp:construction-k7-standalone-generic-model-bootstrap:v125",
    "update": "acfqp:construction-k7-standalone-generic-model-update:v125",
    "match": "acfqp:construction-k7-standalone-generic-model-match:v125",
    "verification": "acfqp:construction-k7-standalone-generic-model-verification:v125",
    "acquisition": "acfqp:construction-k7-generic-artifact-subprogram-partial-acquisition:v121",
    "strict": "acfqp:construction-k7-generic-artifact-subprogram-strict-control:v121",
    "v119_sequence": "acfqp:construction-k7-source-unseen-residual-genesis-authorized-branch-sequence:v119",
    "v113_sequence": "acfqp:construction-k7-incremental-abstract-successor-sequence:v113",
    "plan": "acfqp:generic-legality-conditioned-quotient-plan:v106",
    "ood": "acfqp:incompatible-schema-no-transfer-control:v99",
}


class ConstructionK7StandaloneGenericModelIndependentVerifierV125Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StandaloneGenericModelIndependentVerifierV125Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V125 {key} changed")


def _raw_key(row: Mapping[str, Any]) -> tuple[tuple[int, ...], int, tuple[int, ...]]:
    return (
        tuple(row["pre_vector"]),
        row["selected_action"]["action_key"],
        tuple(row["post_vector"]),
    )


def _project(
    rows: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    actions: Mapping[int, tuple[int, ...]],
) -> dict[str, Any]:
    unique = {_raw_key(row): row for row in rows}
    raw_rows = [unique[key] for key in sorted(unique)]
    layout = candidate["layout"]
    state_order = layout["state_canonical_to_raw"]
    action_order = layout["action_canonical_to_raw"]
    assignments = candidate["compiled_factor_assignments"]
    targets = tuple(row["target_column"] for row in assignments)
    edges: set[tuple[tuple[int, ...], int, tuple[int, ...]]] = set()
    terminal_memberships: set[tuple[tuple[int, ...], str]] = set()
    terminal_by_state: dict[tuple[int, ...], set[str]] = defaultdict(set)
    contexts: set[tuple[tuple[int, ...], int]] = set()
    accepting: dict[int, set[int]] = defaultdict(set)
    checks = 0
    for row in raw_rows:
        selected = row["selected_action"]
        action = tuple(selected["anonymous_fields"][index] for index in action_order)
        action_key = selected["action_key"]
        _require(actions.get(action_key) == action, "V125 raw/catalogue action join changed")
        pre_full = tuple(row["pre_vector"][index] for index in state_order)
        post_full = tuple(row["post_vector"][index] for index in state_order)
        pre = tuple(pre_full[index] for index in targets)
        post = tuple(post_full[index] for index in targets)
        support = generic._successors(assignments, pre, action)  # noqa: SLF001
        checks += len(support)
        _require(post in support, "V125 raw edge escaped compiled program")
        edges.add((pre, action_key, post))
        terminal_class = (
            "ACTIVE"
            if row["legal_action_keys_after"]
            else "ACCEPT"
            if row["terminal_acceptance_after"] is True
            else "REJECT"
        )
        terminal_memberships.add((post, terminal_class))
        terminal_by_state[post].add(terminal_class)
        contexts.add((tuple(row["pre_vector"]), action_key))
        if row["terminal_acceptance_after"] is True:
            for target in targets:
                accepting[target].add(post_full[target])
    edge_rows = [
        {"projected_pre": list(pre), "action_key": key, "projected_post": list(post)}
        for pre, key, post in sorted(edges)
    ]
    terminal_rows = [
        {"projected_state": list(state), "observed_terminal_classes": sorted(classes)}
        for state, classes in sorted(terminal_by_state.items())
    ]
    payload = {
        "schema": "acfqp.standalone_generic_model_epoch.v125",
        "partial_candidate_id": candidate["candidate_id"],
        "layout_id": layout["layout_id"],
        "projected_state_target_columns": list(targets),
        "quotiented_residual_target_columns": candidate["unknown_residual_target_columns"],
        "projected_state_width": len(targets),
        "projected_edge_rows": edge_rows,
        "projected_edge_count": len(edge_rows),
        "projected_terminal_rows": terminal_rows,
        "projected_terminal_state_count": len(terminal_rows),
        "source_ground_support_label_count": len(contexts),
        "source_raw_transition_row_count": len(raw_rows),
        "source_projected_edge_program_checks": checks,
        "source_projected_rows_sha256": hashlib.sha256(
            canonical_json_bytes({"edges": edge_rows, "terminal": terminal_rows})
        ).hexdigest(),
        "all_projected_edges_checked_by_compiled_factor_program": True,
        "residual_coordinates_deliberately_quotiented_not_imputed": True,
        "query_local_overlay_may_extend_graph_only_after_certificate_failure": True,
        "ground_transition_accessed_during_abstract_search": False,
        "quotient_graph_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_claimed": False,
        "recursive_generic_program_compiler": True,
        "legacy_shape_specific_model_builder_called": False,
        "retained_v113_state_carrier_present": False,
    }
    model = {**payload, "quotient_graph_id": _content_id(_DOMAINS["state"], payload)}
    rules = generic._terminal_rules(assignments, accepting, actions)  # noqa: SLF001
    inventory = [
        {"pre": list(pre), "action_key": key, "post": list(post)}
        for pre, key, post in sorted(unique)
    ]
    state_payload = {
        "generic_model_epoch_id": model["quotient_graph_id"],
        "terminal_projection_rule": [dict(rule) for rule in rules],
        "raw_row_identity_count": len(unique),
        "raw_row_identity_sha256": hashlib.sha256(canonical_json_bytes(inventory)).hexdigest(),
        "retained_v113_state_carrier_present": False,
    }
    return {
        "raw_keys": frozenset(unique),
        "model": model,
        "rules": rules,
        "state_id": _content_id(_DOMAINS["state"], state_payload),
        "edges": frozenset(edges),
        "terminal_memberships": frozenset(terminal_memberships),
        "contexts": frozenset(contexts),
        "accepting": {key: frozenset(values) for key, values in accepting.items()},
        "checks": checks,
    }


def _writes(facts: Mapping[str, Any]) -> int:
    return (
        len(facts["edges"])
        + len(facts["terminal_memberships"])
        + len(facts["contexts"])
        + sum(len(values) for values in facts["accepting"].values())
    )


def _bootstrap_receipt(rows: Sequence[Mapping[str, Any]], facts: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standalone_generic_model_bootstrap.v125",
        "successor_state_id": facts["state_id"],
        "generic_model_epoch_id": facts["model"]["quotient_graph_id"],
        "bootstrap_raw_identity_checks": len(rows),
        "bootstrap_unique_raw_rows": len(facts["raw_keys"]),
        "bootstrap_projected_program_checks": facts["checks"],
        "bootstrap_projection_index_writes": _writes(facts),
        "bootstrap_compilation_events": len(rows) + facts["checks"] + _writes(facts),
        "retained_v113_state_carrier_present": False,
        "ground_transition_accessed_during_abstract_search": False,
        "model_used_as_safety_authority": False,
    }
    return {**payload, "bootstrap_receipt_id": _content_id(_DOMAINS["bootstrap"], payload)}


def _update_receipt(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    input_rows: Sequence[Mapping[str, Any]],
    novel: Mapping[str, Any],
) -> dict[str, Any]:
    unique_input = {_raw_key(row) for row in input_rows}
    edge_inserts = len(after["edges"] - before["edges"])
    terminal_inserts = len(after["terminal_memberships"] - before["terminal_memberships"])
    context_inserts = len(after["contexts"] - before["contexts"])
    accepting_inserts = sum(
        len(values - before["accepting"].get(target, frozenset()))
        for target, values in after["accepting"].items()
    )
    writes = edge_inserts + terminal_inserts + context_inserts + accepting_inserts
    payload = {
        "schema": "acfqp.standalone_generic_model_update.v125",
        "previous_successor_state_id": before["state_id"],
        "current_successor_state_id": after["state_id"],
        "previous_generic_model_epoch_id": before["model"]["quotient_graph_id"],
        "current_generic_model_epoch_id": after["model"]["quotient_graph_id"],
        "delta_input_raw_row_count": len(input_rows),
        "delta_unique_input_raw_row_count": len(unique_input),
        "delta_novel_raw_row_count": len(novel["raw_keys"]),
        "delta_raw_identity_checks": len(input_rows),
        "delta_projected_program_checks": novel["checks"],
        "delta_projected_edge_insertions": edge_inserts,
        "delta_terminal_membership_insertions": terminal_inserts,
        "delta_ground_context_insertions": context_inserts,
        "delta_accepting_value_insertions": accepting_inserts,
        "delta_projection_index_writes": writes,
        "incremental_compilation_events": len(input_rows) + novel["checks"] + writes,
        "model_identity_changed": before["model"]["quotient_graph_id"] != after["model"]["quotient_graph_id"],
        "only_novel_certificate_local_rows_projected": True,
        "previous_compiled_rows_not_replayed": True,
        "retained_v113_state_carrier_present": False,
        "ground_transition_accessed_during_abstract_search": False,
        "model_used_as_safety_authority": False,
    }
    return {**payload, "update_receipt_id": _content_id(_DOMAINS["update"], payload)}


def _match_receipt(
    facts: Mapping[str, Any],
    all_rows: Sequence[Mapping[str, Any]],
    update: Mapping[str, Any] | None,
) -> dict[str, Any]:
    events = len(all_rows) + facts["checks"] + _writes(facts)
    incremental = events if update is None else update["incremental_compilation_events"]
    payload = {
        "schema": "acfqp.standalone_generic_model_full_rebuild_match.v125",
        "successor_state_id": facts["state_id"],
        "generic_model_epoch_id": facts["model"]["quotient_graph_id"],
        "update_receipt_id": None if update is None else update["update_receipt_id"],
        "incremental_compilation_events": incremental,
        "matched_full_rebuild_raw_identity_checks": len(all_rows),
        "matched_full_rebuild_projected_program_checks": facts["checks"],
        "matched_full_rebuild_projection_index_writes": _writes(facts),
        "matched_full_rebuild_compilation_events": events,
        "compilation_events_avoided_against_full_rebuild": events - incremental,
        "model_bytes_exactly_equal_full_generic_rebuild": True,
        "model_bytes_exactly_equal_full_v105_rebuild": True,
        "legacy_named_v105_match_field_is_sequence_compatibility_alias": True,
        "terminal_projection_rule_exactly_equal_full_rebuild": True,
        "raw_row_identity_inventory_exactly_equal_full_rebuild": True,
        "matched_control_compute_not_charged_to_incremental_arm": True,
        "retained_v113_state_carrier_present": False,
        "model_used_as_safety_authority": False,
    }
    return {**payload, "match_receipt_id": _content_id(_DOMAINS["match"], payload)}


def _verify_occurrence(row: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        row.get("schema") == "acfqp.standalone_generic_model_occurrence.v125"
        and row.get("target_family") == EXPECTED_FAMILY,
        "V125 occurrence family/schema changed",
    )
    _verify_id(row, "occurrence_id", _DOMAINS["occurrence"])
    acquisition = row["partial_prior_acquisition"]
    strict = row["strict_no_prior_complete_model_control"]
    _verify_id(acquisition, "acquisition_id", _DOMAINS["acquisition"])
    _verify_id(strict, "strict_control_id", _DOMAINS["strict"])
    candidate = acquisition["candidate"]
    _verify_id(candidate, "candidate_id", _DOMAINS["acquisition"])
    _require(
        acquisition["family"] == EXPECTED_FAMILY
        and acquisition["ground_support_labels"] == strict["ground_support_labels"]
        and acquisition["raw_transition_sha256"] == strict["raw_transition_sha256"]
        and bool(candidate["unknown_residual_target_columns"]),
        "V125 acquisition/control join changed",
    )
    sequence = row["standalone_generic_model_sequence"]
    _verify_id(sequence, "sequence_id", _DOMAINS["sequence"])
    v119 = sequence["generic_compiler_base_sequence"]
    _verify_id(v119, "sequence_id", _DOMAINS["v119_sequence"])
    base = v119["genesis_authorized_base_sequence"]
    _verify_id(base, "sequence_id", _DOMAINS["v113_sequence"])
    _require(
        row["standalone_generic_model_sequence_id"] == sequence["sequence_id"]
        and sequence["generic_compiler_base_sequence_id"] == v119["sequence_id"]
        and sequence["partial_candidate_id"] == candidate["candidate_id"]
        and v119["partial_candidate_id"] == candidate["candidate_id"]
        and base["partial_candidate_id"] == candidate["candidate_id"],
        "V125 sequence/candidate joins changed",
    )
    dependency = v119["program_branch_dependency_receipt"]
    _require(
        dependency["compiled_factor_assignments"] == candidate["compiled_factor_assignments"]
        and dependency["partial_candidate_id"] == candidate["candidate_id"],
        "V125 program dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in dependency["canonical_action_catalogue"]
    }
    persistent = base["persistent_exact_overlay_rows"]
    _require(
        hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == base["persistent_exact_overlay_sha256"],
        "V125 persistent raw evidence changed",
    )
    episode_keys = {
        _raw_key(raw)
        for episode in base["episodes"]
        for raw in episode["raw_incremental_transition_rows"]
    }
    current = {_raw_key(raw): raw for raw in persistent if _raw_key(raw) not in episode_keys}
    initial_rows = tuple(current.values())
    facts = _project(initial_rows, candidate, actions)
    _require(
        facts["model"] == base["quotient_models_before_each_episode"][0]
        and _bootstrap_receipt(initial_rows, facts) == base["bootstrap_receipt"]
        and _match_receipt(facts, initial_rows, None) == base["bootstrap_full_rebuild_match"],
        "V125 bootstrap state/receipt reconstruction changed",
    )
    rebuilt = []
    direct = memoized = path_checks = 0
    update_receipts = base["incremental_successor_update_receipts"]
    match_receipts = base["full_rebuild_match_receipts"]
    _require(
        len(base["episodes"]) == len(update_receipts) == len(match_receipts),
        "V125 episode/receipt cardinality changed",
    )
    for index, episode in enumerate(base["episodes"]):
        before = _project(tuple(current.values()), candidate, actions)
        _require(
            before["model"] == base["quotient_models_before_each_episode"][index]
            and before["state_id"] == update_receipts[index]["previous_successor_state_id"],
            "V125 before-model/state reconstruction changed",
        )
        rebuilt.append(before["model"])
        for plan_receipt in episode["abstract_plan_receipts"]:
            plan = plan_receipt["abstract_plan"]
            source = plan["planning_source"]
            if source in {"OBSERVATION_QUOTIENT_GRAPH", "COMPILED_FACTOR_PROGRAM_FALLBACK"}:
                _verify_id(plan, "legality_conditioned_quotient_plan_id", _DOMAINS["plan"])
                _require(
                    tuple(plan["embedded_projected_plan"]["terminal_projection_rule"]) == before["rules"],
                    "V125 terminal rules changed",
                )
                path_checks += generic._verify_plan(  # noqa: SLF001
                    plan,
                    plan_receipt["raw_state"],
                    candidate,
                    actions,
                    before["model"],
                    before["rules"],
                )
                if source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
                    direct += 1
                    _require(
                        plan["legacy_shape_specific_planner_execution_adapter_called"] is False,
                        "V125 legacy planner path changed",
                    )
            elif source == "COMPILED_FACTOR_PROGRAM_MEMOIZED":
                memoized += 1
                _require(
                    plan["source_compiled_factor_program_plan"]["legacy_shape_specific_planner_execution_adapter_called"] is False,
                    "V125 memoized plan source changed",
                )
            elif source == "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER":
                memoized += 1
                _require(
                    plan["cached_ordering_used_as_safety_authority"] is False
                    and plan["complete_ground_world_model_claimed"] is False
                    and plan["dependency_revalidation"]["current_quotient_graph_id"]
                    == before["model"]["quotient_graph_id"],
                    "V125 dependency-revalidated ordering changed",
                )
            else:
                _fail("V125 unknown planning source")
        delta_rows = tuple(episode["raw_incremental_transition_rows"])
        novel_rows = tuple(raw for raw in delta_rows if _raw_key(raw) not in current)
        novel = _project(novel_rows, candidate, actions) if novel_rows else {
            "raw_keys": frozenset(),
            "checks": 0,
        }
        for raw in delta_rows:
            current[_raw_key(raw)] = raw
        after = _project(tuple(current.values()), candidate, actions)
        expected_update = _update_receipt(before, after, delta_rows, novel)
        expected_match = _match_receipt(after, tuple(current.values()), expected_update)
        _require(
            after["model"] == base["quotient_models_after_each_episode"][index]
            and expected_update == update_receipts[index]
            and expected_match == match_receipts[index],
            "V125 update/model/full-match receipt reconstruction changed",
        )
        rebuilt.append(after["model"])
        _require(
            episode["success"] is True
            and episode["all_incremental_ground_queries_followed_failed_certificates"] is True
            and episode["planner_raw_transition_argument_present"] is False,
            "V125 episode/certificate discipline changed",
        )
    _require(len(current) == len(persistent), "V125 persistent inventory changed")
    checks = sum(model["source_projected_edge_program_checks"] for model in rebuilt)
    reconstruction = {
        "generic_model_epoch_reconstruction_count": len(rebuilt),
        "generic_model_program_support_checks": checks,
        "all_state_and_update_receipts_use_v125_domains": True,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": True,
    }
    _require(
        sequence["standalone_generic_model_reconstruction"] == reconstruction
        and sequence["direct_generic_factor_program_plan_count"] == direct
        and sequence["standalone_v125_state_carrier_verified"] is True
        and sequence["retained_v113_state_carrier_present"] is False
        and sequence["retained_v113_sequence_orchestration_present"] is True
        and sequence["legacy_shape_specific_model_builder_called"] is False,
        "V125 standalone sequence reconstruction/claims changed",
    )
    accounting = {
        "partial_prior_acquisition_labels": acquisition["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base["certificate_ground_support_labels_paid_once"],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": v119["actual_new_abstract_planning_compute_events"],
        "matched_uncached_planning_compute_events": v119["matched_uncached_abstract_planning_compute_events"],
        "planning_compute_events_avoided_against_uncached": v119["planning_compute_events_avoided_against_uncached"],
        "dependency_derivation_compute_events": v119["dependency_derivation_compute_events"],
        "standalone_model_epoch_reconstructions": len(rebuilt),
        "generic_model_program_support_checks": checks,
        "direct_generic_factor_program_plans": direct,
        "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    _require(
        row["accounting"] == accounting
        and row["registered_gate"]["passed"] is True
        and all(value is True for key, value in row["registered_gate"].items() if key != "passed")
        and row["registered_standalone_generic_model_verified"] is True
        and row["retained_v113_state_carrier_present"] is False
        and row["retained_v113_sequence_orchestration_present"] is True
        and row["legacy_shape_specific_model_builder_called"] is False
        and row["compiled_model_or_receipt_used_as_safety_authority"] is False
        and row["complete_ground_world_model_synthesized"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN",
        "V125 occurrence accounting/Gate changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "seed": row["seed"],
        "episode_count": len(base["episodes"]),
        "independently_rebuilt_v125_model_epoch_count": len(rebuilt),
        "independently_rebuilt_v125_receipt_count": 2 + 2 * len(base["episodes"]),
        "independent_plan_path_support_checks": path_checks,
        "memoized_plan_count": memoized,
        "accounting": accounting,
    }


def freeze_standalone_generic_model_verification_v125(
    campaign_raw: bytes,
    v124_campaign_raw: bytes,
    v124_verification_raw: bytes,
    v123r1_campaign_raw: bytes,
    v123r1_verification_raw: bytes,
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
    failed_v123_raw: bytes,
    v121r1_campaign_raw: bytes,
    v121_failed_campaign_raw: bytes,
    v121r1_verification_raw: bytes,
    source_campaign_bytes: Mapping[str, bytes],
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V125 frozen campaign identity or bytes changed",
    )
    _verify_id(campaign, "campaign_id", _DOMAINS["campaign"])
    _require(
        previous.freeze_cross_family_generic_compiler_verification_v124(
            v124_campaign_raw,
            v123r1_campaign_raw,
            v123r1_verification_raw,
            v122_campaign_raw,
            v122_verification_raw,
            failed_v123_raw,
            v121r1_campaign_raw,
            v121_failed_campaign_raw,
            v121r1_verification_raw,
            dict(source_campaign_bytes),
        )
        == v124_verification_raw,
        "V125 V124 producer-free predecessor changed",
    )
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v124_success_campaign_id"] == V124_CAMPAIGN_ID
        and campaign["v124_success_verification_id"] == V124_VERIFICATION_ID,
        "V125 predecessor joins changed",
    )
    rows = tuple(_verify_occurrence(row) for row in campaign["target_occurrences"])
    _require(
        tuple(row["seed"] for row in rows) == EXPECTED_SEEDS
        and all(row["episode_count"] == len(EXPECTED_EPISODES) for row in rows)
        and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows],
        "V125 occurrence identities changed",
    )
    ood = campaign["incompatible_schema_no_transfer_control"]
    ood_payload = {key: value for key, value in ood.items() if key != "control_id"}
    _require(
        ood["control_id"] == _content_id(_DOMAINS["ood"], ood_payload)
        and ood["strict_ood_no_transfer"] is True
        and ood["learned_structure_prior_delivered"] is False
        and ood["target_outcomes_accessed"] is False,
        "V125 strict OOD control changed",
    )
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(
        sample_labels_execution_steps_derivation_planning_and_model_checks_separate=True,
        sample_efficiency_improvement_claimed=False,
        scalar_cost_aggregation_performed=False,
    )
    _require(
        campaign["accounting"] == accounting
        and campaign["registered_gate"]
        == {
            "required_target_occurrence_count": 2,
            "passed_target_occurrence_count": 2,
            "standalone_v125_state_carrier_used_in_every_occurrence": True,
            "retained_v113_state_carrier_absent_in_every_occurrence": True,
            "all_receding_episodes_succeed": True,
            "strict_incompatible_schema_no_transfer_verified": True,
            "passed": True,
        }
        and campaign["registered_standalone_generic_model_verified"] is True
        and campaign["retained_v113_state_carrier_present"] is False
        and campaign["retained_v113_sequence_orchestration_present"] is True
        and campaign["legacy_shape_specific_model_builder_called"] is False
        and campaign["sample_efficiency_improvement_claimed"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V125 campaign accounting/Gate changed",
    )
    payload = {
        "schema": "acfqp.standalone_generic_model_verification.v125",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v124_predecessor_verification_id": V124_VERIFICATION_ID,
        "verified_family": EXPECTED_FAMILY,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_raw_transition_v125_model_epoch_reconstruction": True,
        "producer_free_v125_bootstrap_update_and_full_match_receipt_reconstruction": True,
        "producer_free_terminal_rule_and_plan_reconstruction": True,
        "registered_gate_independently_verified": True,
        "standalone_v125_state_carrier_verified": True,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": True,
        "legacy_shape_specific_model_builder_called": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "sample_efficiency_improvement_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": _content_id(_DOMAINS["verification"], payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V125 frozen verification changed",
        )
    return raw


__all__ = ("VERIFICATION_ID", "freeze_standalone_generic_model_verification_v125")

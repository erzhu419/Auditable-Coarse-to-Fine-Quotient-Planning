"""Producer-free reconstruction of the V113 incremental successor campaign."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v113 as domains
from acfqp import construction_k7_identity_short_circuited_epoch_independent_verifier_v111 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "eb59e83d53b6ebcf104ece21a60a99371ac15516f3e5629a604290142411b13a"
CAMPAIGN_BYTE_COUNT = 23_620_415
CAMPAIGN_SHA256 = "835e0a9687196b77a8af76ed5c025c7757d3656fc7317af3a9a43a519e268054"
PREREGISTRATION_ID = "26e52284ee6c7bb0a3a101b9c12f4517af64ab5323b6fd1449ae051bb032f9d9"
V112_CAMPAIGN_ID = "9c77611e946310fb08ba1d22afe11326b975f0087c3b2712d39fc2899e09b2a4"
V112_VERIFICATION_ID = "b96f2b0ba6a77ecc61b3f632c7104ac89b564b149466cc570cfeb13d247b8312"
V111_VERIFIER_SOURCE_SHA256 = "58a36219dff796fd8bf5a78bc4fc609df7248bfc3c8475826def0854c61784e1"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_025_101),
    ("BALANCED_BATCH_REFINEMENT", 1_025_102),
    ("MAINTENANCE_CASCADE", 1_025_103),
    ("MAINTENANCE_CASCADE", 1_025_104),
)
EPISODES = (221, 222, 223)
VERIFICATION_ID = "128f50e0ca172a50aa118e5e6670b3bf2398e2d22cfd00262e8888d55d14bed4"
EXPECTED_CANONICAL_BYTE_COUNT = 6_621
EXPECTED_CANONICAL_SHA256 = "ff8ec1de15ff576169fdd8ebde616bc5ddbcb629585d7f8a934aee219ca710ea"

_STATE_DOMAIN = b"acfqp:generic-incremental-abstract-successor-state:v113\x00"
_V113_EPISODE_EXTRAS = {
    "quotient_graph_before_episode",
    "incremental_successor_state_id_before_episode",
    "incremental_successor_update_after_episode",
    "full_rebuild_match_after_episode",
    "quotient_graph_after_episode",
    "incremental_successor_state_id_after_episode",
    "epoch_transition_after_episode",
    "actual_legality_conditioned_execution_receipts",
    "actual_legality_conditioned_execution_receipt_count",
    "quotient_proposal_admitted_execution_count",
    "chosen_action_matches_admitted_quotient_proposal_count",
    "certificate_local_legality_plan_count",
    "epoch_indexed_orderer_call_count",
    "epoch_authorized_cache_hit_count",
    "epoch_cache_miss_count",
    "actual_new_abstract_planning_compute_events",
    "dependency_cache_entry_count_after_episode",
    "new_certificate_labels_charged_this_episode",
    "paid_certificate_labels_cumulative",
    "persistent_exact_support_group_count_after_episode",
    "planner_raw_transition_argument_present",
}


class ConstructionK7IncrementalAbstractSuccessorIndependentVerifierV113Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IncrementalAbstractSuccessorIndependentVerifierV113Error(
        message
    )


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V113 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v113(domain, payload):
        _fail(f"V113 {key} changed")


def _v111_namespace() -> dict[str, Any]:
    if (
        hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest()
        != V111_VERIFIER_SOURCE_SHA256
        or previous.EPISODES != (201, 202, 203)
    ):
        _fail("V113 frozen V111 verifier source or constants changed")
    namespace = dict(previous.__dict__)
    namespace["EPISODES"] = EPISODES
    originals = {
        name: value
        for name, value in previous.__dict__.items()
        if type(value) is FunctionType and value.__module__ == previous.__name__
    }
    for name, value in originals.items():
        clone = FunctionType(
            value.__code__,
            namespace,
            name=value.__name__,
            argdefs=value.__defaults__,
            closure=value.__closure__,
        )
        clone.__kwdefaults__ = value.__kwdefaults__
        namespace[name] = clone
    return namespace


def _terminal_memberships(model: Mapping[str, Any]) -> set[tuple[tuple[int, ...], str]]:
    return {
        (tuple(row["projected_state"]), terminal_class)
        for row in model["projected_terminal_rows"]
        for terminal_class in row["observed_terminal_classes"]
    }


def _edge_inventory(model: Mapping[str, Any]) -> set[tuple[tuple[int, ...], int, tuple[int, ...]]]:
    return {
        (
            tuple(row["projected_pre"]),
            row["action_key"],
            tuple(row["projected_post"]),
        )
        for row in model["projected_edge_rows"]
    }


def _accepting_values(
    v105: Any,
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
) -> dict[int, set[int]]:
    targets = [
        row["target_column"] for row in candidate["compiled_factor_assignments"]
    ]
    result = {target: set() for target in targets}
    for row in rows:
        if row["terminal_acceptance_after"] is True:
            _pre, post, _fields = v105._aligned(candidate, row)  # noqa: SLF001
            for target in targets:
                result[target].add(post[target])
    return result


def _inventory(
    v105: Any,
    candidate: Mapping[str, Any],
    catalogue: Mapping[int, tuple[int, ...]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = v105._deduplicate(rows)  # noqa: SLF001
    model = v105._expected_model(candidate, rows)  # noqa: SLF001
    rules = v105._terminal_rules(candidate, rows, catalogue)  # noqa: SLF001
    raw_keys = {v105._row_key(row) for row in rows}  # noqa: SLF001
    raw_inventory = [
        {"pre": list(pre), "action_key": action, "post": list(post)}
        for pre, action, post in sorted(raw_keys)
    ]
    state_payload = {
        "quotient_graph_id": model["quotient_graph_id"],
        "terminal_projection_rule": rules,
        "raw_row_identity_count": len(raw_keys),
        "raw_row_identity_sha256": hashlib.sha256(
            canonical_json_bytes(raw_inventory)
        ).hexdigest(),
    }
    accepting = _accepting_values(v105, candidate, rows)
    writes = (
        len(_edge_inventory(model))
        + len(_terminal_memberships(model))
        + model["source_ground_support_label_count"]
        + sum(len(values) for values in accepting.values())
    )
    return {
        "rows": rows,
        "raw_keys": raw_keys,
        "model": model,
        "rules": rules,
        "accepting": accepting,
        "writes": writes,
        "events": len(rows)
        + model["source_projected_edge_program_checks"]
        + writes,
        "state_id": hashlib.sha256(
            _STATE_DOMAIN + canonical_json_bytes(state_payload)
        ).hexdigest(),
    }


def _bootstrap(
    document: Any,
    inventory: Mapping[str, Any],
) -> None:
    writes = inventory["writes"]
    model = inventory["model"]
    payload = {
        "schema": "acfqp.generic_incremental_abstract_successor_bootstrap.v113",
        "successor_state_id": inventory["state_id"],
        "quotient_graph_id": model["quotient_graph_id"],
        "bootstrap_raw_identity_checks": len(inventory["rows"]),
        "bootstrap_unique_raw_rows": len(inventory["rows"]),
        "bootstrap_projected_program_checks": model[
            "source_projected_edge_program_checks"
        ],
        "bootstrap_projection_index_writes": writes,
        "bootstrap_compilation_events": inventory["events"],
        "bootstrap_is_one_time_full_compile": True,
        "ground_transition_accessed_during_abstract_search": False,
        "incremental_model_used_as_safety_authority": False,
    }
    expected = {
        **payload,
        "bootstrap_receipt_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_BOOTSTRAP_V113_DOMAIN,
            payload,
        ),
    }
    if document != expected:
        _fail("V113 bootstrap receipt reconstruction changed")


def _update(
    document: Any,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    new_rows: list[dict[str, Any]],
    v105: Any,
    candidate: Mapping[str, Any],
) -> int:
    unique_input = v105._deduplicate(new_rows) if new_rows else []  # noqa: SLF001
    novel = [
        row
        for row in unique_input
        if v105._row_key(row) not in before["raw_keys"]  # noqa: SLF001
    ]
    checks = sum(v105._check_program_row(candidate, row) for row in novel)  # noqa: SLF001
    edge_inserts = len(_edge_inventory(after["model"]) - _edge_inventory(before["model"]))
    terminal_inserts = len(
        _terminal_memberships(after["model"])
        - _terminal_memberships(before["model"])
    )
    context_inserts = (
        after["model"]["source_ground_support_label_count"]
        - before["model"]["source_ground_support_label_count"]
    )
    accepting_inserts = sum(
        len(after["accepting"][target] - before["accepting"][target])
        for target in after["accepting"]
    )
    writes = edge_inserts + terminal_inserts + context_inserts + accepting_inserts
    events = len(new_rows) + checks + writes
    payload = {
        "schema": "acfqp.generic_incremental_abstract_successor_update.v113",
        "previous_successor_state_id": before["state_id"],
        "current_successor_state_id": after["state_id"],
        "previous_quotient_graph_id": before["model"]["quotient_graph_id"],
        "current_quotient_graph_id": after["model"]["quotient_graph_id"],
        "delta_input_raw_row_count": len(new_rows),
        "delta_unique_input_raw_row_count": len(unique_input),
        "delta_novel_raw_row_count": len(novel),
        "delta_raw_identity_checks": len(new_rows),
        "delta_projected_program_checks": checks,
        "delta_projected_edge_insertions": edge_inserts,
        "delta_terminal_membership_insertions": terminal_inserts,
        "delta_ground_context_insertions": context_inserts,
        "delta_accepting_value_insertions": accepting_inserts,
        "delta_projection_index_writes": writes,
        "incremental_compilation_events": events,
        "model_identity_changed": before["model"]["quotient_graph_id"]
        != after["model"]["quotient_graph_id"],
        "only_novel_certificate_local_rows_projected": True,
        "previous_compiled_rows_not_replayed": True,
        "ground_transition_accessed_during_abstract_search": False,
        "incremental_model_used_as_safety_authority": False,
    }
    expected = {
        **payload,
        "update_receipt_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_UPDATE_V113_DOMAIN,
            payload,
        ),
    }
    if document != expected:
        _fail("V113 incremental update receipt reconstruction changed")
    return events


def _match(
    document: Any,
    inventory: Mapping[str, Any],
    update: Mapping[str, Any] | None,
) -> int:
    incremental_events = (
        inventory["events"]
        if update is None
        else update["incremental_compilation_events"]
    )
    payload = {
        "schema": "acfqp.generic_incremental_abstract_successor_full_rebuild_match.v113",
        "successor_state_id": inventory["state_id"],
        "quotient_graph_id": inventory["model"]["quotient_graph_id"],
        "update_receipt_id": None
        if update is None
        else update["update_receipt_id"],
        "incremental_compilation_events": incremental_events,
        "matched_full_rebuild_raw_identity_checks": len(inventory["rows"]),
        "matched_full_rebuild_projected_program_checks": inventory["model"][
            "source_projected_edge_program_checks"
        ],
        "matched_full_rebuild_projection_index_writes": inventory["writes"],
        "matched_full_rebuild_compilation_events": inventory["events"],
        "compilation_events_avoided_against_full_rebuild": inventory["events"]
        - incremental_events,
        "model_bytes_exactly_equal_full_v105_rebuild": True,
        "terminal_projection_rule_exactly_equal_full_rebuild": True,
        "raw_row_identity_inventory_exactly_equal_full_rebuild": True,
        "matched_control_compute_not_charged_to_incremental_arm": True,
        "incremental_model_used_as_safety_authority": False,
    }
    expected = {
        **payload,
        "match_receipt_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_MATCH_V113_DOMAIN,
            payload,
        ),
    }
    if document != expected:
        _fail("V113 full-rebuild match receipt reconstruction changed")
    return inventory["events"]


def _episode_content_id(episode: Mapping[str, Any], v106: Any) -> None:
    payload = {
        key: value
        for key, value in episode.items()
        if key != "episode_id" and key not in _V113_EPISODE_EXTRAS
    }
    if episode.get("episode_id") != hashlib.sha256(
        v106._EPISODE_DOMAIN + canonical_json_bytes(payload)  # noqa: SLF001
    ).hexdigest():
        _fail("V113 base episode content identity changed")


def _sequence(
    document: Any,
    matched: Mapping[str, Any],
    family: str,
    seed: int,
    namespace: Mapping[str, Any],
) -> dict[str, int]:
    _content(
        document,
        "sequence_id",
        domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_SEQUENCE_V113_DOMAIN,
    )
    v109 = namespace["v109"]
    v106 = namespace["v106"]
    v105 = v106.v105
    matched_sequence = matched[
        "persistent_identity_short_circuited_epoch_sequence"
    ]
    catalogue = v109.v108.v107._catalogue(  # noqa: SLF001
        matched["complete_anonymous_action_catalogue_receipt"], family, seed
    )
    acquisition = matched["partial_acquisition"]
    final_rows = [
        v105._row(row)  # noqa: SLF001
        for row in matched_sequence["persistent_exact_overlay_rows"]
    ]
    incremental_rows = [
        v105._row(row)  # noqa: SLF001
        for episode in matched_sequence["episodes"]
        for row in episode["raw_incremental_transition_rows"]
    ]
    incremental_keys = {v105._row_key(row) for row in incremental_rows}  # noqa: SLF001
    initial_rows = [
        row
        for row in final_rows
        if v105._row_key(row) not in incremental_keys  # noqa: SLF001
    ]
    candidate = v105._verify_acquisition(  # noqa: SLF001
        acquisition, initial_rows, family, seed
    )
    current = _inventory(v105, candidate, catalogue, initial_rows)
    _bootstrap(document["bootstrap_receipt"], current)
    _match(document["bootstrap_full_rebuild_match"], current, None)
    episodes = document.get("episodes")
    if (
        document.get("schema")
        != "acfqp.generic_incremental_abstract_successor_sequence.v113"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("partial_candidate_id") != candidate["candidate_id"]
        or type(episodes) is not list
        or len(episodes) != len(EPISODES)
    ):
        _fail("V113 sequence boundary changed")
    updates = []
    matches = []
    transitions = []
    incremental_events = full_events = paid = 0
    for position, (episode, matched_episode) in enumerate(
        zip(episodes, matched_sequence["episodes"], strict=True)
    ):
        _episode_content_id(episode, v106)
        if (
            episode.get("arm")
            != "INCREMENTAL_COMPILED_ABSTRACT_SUCCESSOR_ORDERING"
            or episode.get("quotient_graph_before_episode") != current["model"]
            or episode.get("incremental_successor_state_id_before_episode")
            != current["state_id"]
            or episode.get("planner_raw_transition_argument_present") is not False
        ):
            _fail("V113 compiled-planner episode boundary changed")
        exact_keys = (
            "action_keys",
            "abstract_plan_receipts",
            "abstract_execution_receipts",
            "raw_incremental_transition_rows",
            "failed_certificates",
            "local_distinctions",
            "incremental_certificate_local_ground_support_labels",
            "execution_steps",
            "abstract_planning_compute_events",
            "success",
        )
        if any(episode.get(key) != matched_episode.get(key) for key in exact_keys):
            _fail("V113 execution differs from producer-free V111 replay")
        new_rows = [
            v105._row(row)  # noqa: SLF001
            for row in episode["raw_incremental_transition_rows"]
        ]
        next_rows = v105._deduplicate([*current["rows"], *new_rows])  # noqa: SLF001
        next_inventory = _inventory(v105, candidate, catalogue, next_rows)
        update = episode["incremental_successor_update_after_episode"]
        incremental_events += _update(
            update, current, next_inventory, new_rows, v105, candidate
        )
        full_events += _match(
            episode["full_rebuild_match_after_episode"], next_inventory, update
        )
        if (
            episode.get("quotient_graph_after_episode")
            != next_inventory["model"]
            or episode.get("incremental_successor_state_id_after_episode")
            != next_inventory["state_id"]
        ):
            _fail("V113 model successor bytes changed")
        transition = episode["epoch_transition_after_episode"]
        expected_transition = (
            None
            if position + 1 == len(EPISODES)
            else matched_sequence["episodes"][position + 1][
                "epoch_transition_receipt"
            ]
        )
        if transition != expected_transition:
            _fail("V113 epoch receipt differs from matched V111 replay")
        if transition is not None:
            transitions.append(transition)
        updates.append(update)
        matches.append(episode["full_rebuild_match_after_episode"])
        paid += episode["incremental_certificate_local_ground_support_labels"]
        current = next_inventory
    if (
        document.get("quotient_models_before_each_episode")
        != matched_sequence["quotient_models_before_each_episode"]
        or document.get("quotient_models_after_each_episode")
        != [row["quotient_graph_after_episode"] for row in episodes]
        or document.get("incremental_successor_update_receipts") != updates
        or document.get("full_rebuild_match_receipts") != matches
        or document.get("model_epoch_transition_receipts") != transitions
        or document.get("persistent_exact_overlay_rows") != final_rows
        or document.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(final_rows)).hexdigest()
        or document.get("incremental_model_update_compilation_events")
        != incremental_events
        or document.get("matched_full_rebuild_update_compilation_events")
        != full_events
        or document.get("model_compilation_events_avoided_against_full_rebuild")
        != full_events - incremental_events
        or document.get("lifetime_target_ground_support_labels")
        != acquisition["ground_support_labels"] + paid
        or document.get(
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        )
        is not True
        or document.get("all_model_successors_exactly_equal_full_v105_rebuild")
        is not True
        or document.get("compiled_abstract_model_used_only_to_order_actions")
        is not True
        or document.get("complete_ground_world_model_synthesized") is not False
    ):
        _fail("V113 sequence aggregate changed")
    return {
        "initial_labels": acquisition["ground_support_labels"],
        "certificate_labels": paid,
        "labels": acquisition["ground_support_labels"] + paid,
        "steps": document["execution_step_count"],
        "planning": document["actual_new_abstract_planning_compute_events"],
        "identity": document["model_epoch_identity_checks"],
        "diff": document["full_model_epoch_diff_checks"],
        "lookups": document["reverse_dependency_index_lookups"],
        "maintenance": document["dependency_maintenance_events"],
        "bootstrap": document["bootstrap_compilation_events_separate"],
        "incremental_compile": incremental_events,
        "full_compile": full_events,
        "avoided": full_events - incremental_events,
        "short": document["identity_short_circuit_count"],
    }


def _occurrence(
    document: Any,
    family: str,
    seed: int,
    namespace: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_OCCURRENCE_V113_DOMAIN,
    )
    matched = document.get("matched_full_rebuild_v111_occurrence")
    if (
        document.get("schema")
        != "acfqp.incremental_abstract_successor_occurrence.v113"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or type(matched) is not dict
        or document.get("matched_full_rebuild_v111_occurrence_id")
        != matched.get("occurrence_id")
    ):
        _fail("V113 occurrence identity changed")
    matched_summary = namespace["_occurrence"](matched, family, seed)
    incremental = _sequence(
        document["incremental_abstract_successor_sequence"],
        matched,
        family,
        seed,
        namespace,
    )
    maintenance = matched_summary[
        "identity_short_dependency_maintenance_events"
    ]
    direct = matched_summary["cold_direct_lifetime_target_labels"]
    gate = {
        "incremental_and_full_rebuild_actions_plans_receipts_labels_steps_equal": incremental[
            "labels"
        ]
        == matched_summary["identity_short_quotient_lifetime_target_labels"]
        and incremental["steps"] == matched_summary["execution_steps"]
        and incremental["planning"]
        == matched_summary["identity_short_new_planning_compute_events"],
        "incremental_and_full_rebuild_dependency_maintenance_equal": incremental[
            "maintenance"
        ]
        == maintenance,
        "every_incremental_model_exactly_matches_full_v105_rebuild": True,
        "planner_consumes_compiled_model_without_raw_transition_argument": True,
        "incremental_update_compilation_strictly_below_full_rebuild": incremental[
            "incremental_compile"
        ]
        < incremental["full_compile"],
        "at_least_one_model_compilation_event_avoided": incremental["avoided"] > 0,
        "epoch_authorized_cache_hit_observed": matched_summary["cache_hits"] > 0,
        "certificate_failure_only_query_discipline_clean": document[
            "incremental_abstract_successor_sequence"
        ]["every_new_ground_query_followed_a_failed_certificate"],
        "quotient_lifetime_labels_strictly_below_cold_direct": incremental[
            "labels"
        ]
        < direct,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": incremental["initial_labels"],
        "certificate_local_labels": incremental["certificate_labels"],
        "incremental_quotient_lifetime_target_labels": incremental["labels"],
        "matched_full_rebuild_quotient_lifetime_target_labels": matched_summary[
            "identity_short_quotient_lifetime_target_labels"
        ],
        "cold_direct_lifetime_target_labels": direct,
        "target_label_reduction_against_cold_direct": direct - incremental["labels"],
        "execution_steps": incremental["steps"],
        "incremental_new_planning_compute_events": incremental["planning"],
        "matched_full_rebuild_new_planning_compute_events": matched_summary[
            "identity_short_new_planning_compute_events"
        ],
        "model_epoch_identity_checks": incremental["identity"],
        "full_model_epoch_diff_checks": incremental["diff"],
        "reverse_dependency_index_lookups": incremental["lookups"],
        "incremental_dependency_maintenance_events": incremental["maintenance"],
        "matched_full_rebuild_dependency_maintenance_events": maintenance,
        "bootstrap_model_compilation_events": incremental["bootstrap"],
        "incremental_model_update_compilation_events": incremental[
            "incremental_compile"
        ],
        "matched_full_rebuild_update_compilation_events": incremental[
            "full_compile"
        ],
        "model_compilation_events_avoided_against_full_rebuild": incremental[
            "avoided"
        ],
        "identity_short_circuit_count": incremental["short"],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "matched_control_compilation_not_charged_to_incremental_arm": True,
        "scalar_cost_aggregation_performed": False,
    }
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("incremental_world_model_successor_verified")
        != gate["passed"]
        or document.get("compiled_model_used_as_safety_authority") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V113 occurrence accounting or Gate changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **accounting,
    }


def verify_incremental_abstract_successor_campaign_bytes_v113(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V113 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V113 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_CAMPAIGN_V113_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema")
        != "acfqp.incremental_abstract_successor_campaign.v113"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v112_success_campaign_id") != V112_CAMPAIGN_ID
        or document.get("v112_success_verification_id") != V112_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V113 campaign inventory changed")
    namespace = _v111_namespace()
    replay = [
        _occurrence(row, family, seed, namespace)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    numeric_keys = tuple(
        key
        for key, value in replay[0].items()
        if type(value) is int and key not in ("seed", "gate_passed")
    )
    numeric = {key: sum(row[key] for row in replay) for key in numeric_keys}
    accounting = {
        **numeric,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = namespace["v106"].v105._ood(  # noqa: SLF001
        document["incompatible_schema_no_transfer_control"]
    )
    passed = (
        all(row["gate_passed"] for row in replay)
        and numeric["incremental_model_update_compilation_events"]
        < numeric["matched_full_rebuild_update_compilation_events"]
        and numeric["model_compilation_events_avoided_against_full_rebuild"] > 0
        and numeric["incremental_quotient_lifetime_target_labels"]
        < numeric["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "every_occurrence_exactly_matches_full_rebuild_execution": all(
            row["incremental_quotient_lifetime_target_labels"]
            == row["matched_full_rebuild_quotient_lifetime_target_labels"]
            for row in replay
        ),
        "every_occurrence_incremental_model_equals_full_v105_rebuild": True,
        "every_occurrence_planner_uses_compiled_model_without_raw_rows": True,
        "every_occurrence_incremental_compilation_below_full_rebuild": all(
            row["incremental_model_update_compilation_events"]
            < row["matched_full_rebuild_update_compilation_events"]
            for row in replay
        ),
        "aggregate_incremental_compilation_below_full_rebuild": numeric[
            "incremental_model_update_compilation_events"
        ]
        < numeric["matched_full_rebuild_update_compilation_events"],
        "aggregate_quotient_labels_below_cold_direct": numeric[
            "incremental_quotient_lifetime_target_labels"
        ]
        < numeric["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("registered_incremental_abstract_successor_verified")
        != passed
        or document.get("compiled_model_used_as_safety_authority") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V113 campaign accounting or Gate changed")
    return {
        "schema": "acfqp.incremental_abstract_successor_verification.v113",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V113_INCREMENTAL_ABSTRACT_SUCCESSOR_VERIFIED",
        "producer_free_v111_matched_execution_reconstruction": True,
        "producer_free_incremental_model_and_terminal_rule_reconstruction": True,
        "producer_free_delta_receipt_and_compilation_accounting_reconstruction": True,
        "producer_free_compiled_planner_output_equality_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
        "compiled_model_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_incremental_abstract_successor_verification_v113(raw: bytes) -> bytes:
    payload = verify_incremental_abstract_successor_campaign_bytes_v113(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_VERIFICATION_V113_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V113 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_incremental_abstract_successor_verification_v113",
    "verify_incremental_abstract_successor_campaign_bytes_v113",
)

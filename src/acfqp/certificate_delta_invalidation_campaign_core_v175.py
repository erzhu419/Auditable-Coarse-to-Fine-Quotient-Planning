"""Cross-family campaign core for certificate-delta invalidation V175."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from types import FunctionType, SimpleNamespace

from acfqp import applicable_plan_receipt_set_sequence_v168 as sequence_v168
from acfqp import construction_k7_domain_registry_extension_v175 as domains
from acfqp import fifth_family_total_plan_receipt_set_campaign_core_v168 as v168
from acfqp import fourth_family_sample_tax_transfer_campaign_core_v166 as v166
from acfqp.certificate_delta_driven_invalidation_sequence_v175 import (
    run_certificate_delta_driven_invalidation_sequence_v175,
)
from acfqp.generic_packet_batching_adapter_v134 import FAMILY as PACKET_FAMILY
from acfqp.generic_reservoir_dispatch_adapter_v171 import (
    FAMILY as RESERVOIR_FAMILY,
    build_reservoir_dispatch_adapter_v171,
)
from acfqp.online_typed_plan_receipt_sequence_v172 import TAXONOMY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.receipt_driven_invalidation_campaign_core_v174 import (
    receipt_driven_invalidation_campaign_config_v174,
)


TARGET_FAMILIES = (*v168.TARGET_FAMILIES, RESERVOIR_FAMILY)
V174_CAMPAIGN_ID = "0e5c03c7252ea5b11e5819cbe0b11917ac90722f988969a8b55ef6f446c123ec"
V174_CAMPAIGN_BYTE_COUNT = 54_036_308
V174_CAMPAIGN_SHA256 = "23453500dd9b80213fb01b657eba323a957ef8063503f756bf6df82463754d9a"
V174_VERIFICATION_ID = "3fbd91146f5eacd92ec309a88634071ea983699ea1efe2d40bd5c078b60593ae"
V174_VERIFICATION_BYTE_COUNT = 2_617
V174_VERIFICATION_SHA256 = "64e01b82ff142a5ed784cb170b73bb016f98949939139ac6e4d339fa3039f0a0"


def certificate_delta_invalidation_campaign_config_v175():
    return receipt_driven_invalidation_campaign_config_v174()


_SEQUENCE_SOURCE_PROXY = SimpleNamespace(
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN,
)
_SEQUENCE_OUTPUT_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v175,
    CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V175_DOMAIN,
)
_ANNOTATOR_GLOBALS = dict(sequence_v168.__dict__)
_ANNOTATOR_GLOBALS.update(
    domains_v154=_SEQUENCE_SOURCE_PROXY,
    domains=_SEQUENCE_OUTPUT_PROXY,
)
_ANNOTATE = FunctionType(
    sequence_v168.annotate_applicable_plan_receipt_set_sequence_v168.__code__,
    _ANNOTATOR_GLOBALS,
    name="_annotate_certificate_delta_receipt_set_v175",
)
_V160_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v175,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V175_DOMAIN,
)
_V160_GLOBALS = dict(v168._BASE_V160_OCCURRENCE_V168.__globals__)  # noqa: SLF001
_V160_GLOBALS.update(
    domains=_V160_DOMAIN_PROXY,
    _BUILDERS={
        **_V160_GLOBALS["_BUILDERS"],
        RESERVOIR_FAMILY: build_reservoir_dispatch_adapter_v171,
    },
    run_certified_memoized_planner_sequence_v154=(
        run_certificate_delta_driven_invalidation_sequence_v175
    ),
    annotate_applicable_plan_mode_sequence_v157=_ANNOTATE,
)
_BASE_V160 = FunctionType(
    v168._BASE_V160_OCCURRENCE_V168.__code__,  # noqa: SLF001
    _V160_GLOBALS,
    name="_base_certificate_delta_v160_occurrence_v175",
)
_V166_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v166=domains.extension_content_id_v175,
    CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V175_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN=domains.CONSTRUCTION_K7_CAMPAIGN_V175_DOMAIN,
)
_V166_GLOBALS = dict(v166.__dict__)
_V166_GLOBALS.update(
    domains=_V166_DOMAIN_PROXY,
    _BASE_OCCURRENCE=_BASE_V160,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V166 = FunctionType(
    v166.build_fourth_family_sample_tax_occurrence_v166.__code__,
    _V166_GLOBALS,
    name="_base_certificate_delta_v166_occurrence_v175",
)
_V168_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v175,
    CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V175_DOMAIN,
)
_V168_GLOBALS = dict(v168.__dict__)
_V168_GLOBALS.update(
    domains=_V168_DOMAIN_PROXY,
    _BASE_V166_OCCURRENCE_V168=_BASE_V166,
    TARGET_FAMILIES=TARGET_FAMILIES,
)
_BASE_V168 = FunctionType(
    v168.build_fifth_family_total_plan_receipt_set_occurrence_v168.__code__,
    _V168_GLOBALS,
    name="_base_certificate_delta_v168_occurrence_v175",
)


def build_certificate_delta_invalidation_occurrence_v175(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    if family not in (PACKET_FAMILY, RESERVOIR_FAMILY):
        raise ValueError("V175 target family is not registered")
    base = _BASE_V168(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    sequences = (
        base["progressive_prior_sequence"],
        base["progressive_strict_sequence"],
    )
    histogram = {
        source: sum(
            sequence["online_typed_plan_source_histogram"][source]
            for sequence in sequences
        )
        for source in TAXONOMY.values()
    }
    metrics = {
        "graph_invalidations": sum(
            row["receipt_driven_graph_dependency_invalidation_count"]
            for row in sequences
        ),
        "graph_retentions": sum(
            row["receipt_driven_graph_dependency_retention_count"]
            for row in sequences
        ),
        "program_invalidations": sum(
            row["receipt_driven_compiled_program_invalidation_count"]
            for row in sequences
        ),
        "incremental_revalidations": sum(
            row["incrementally_revalidated_plan_receipt_count"]
            for row in sequences
        ),
        "delta_receipts": sum(
            row["certificate_local_model_delta_receipt_count"]
            for row in sequences
        ),
        "delta_transition_joins": sum(
            row["delta_transition_join_count"] for row in sequences
        ),
        "delta_decision_compute": sum(
            row["delta_driven_invalidation_decision_compute_events"]
            for row in sequences
        ),
        "full_graph_control_checks": sum(
            row["matched_full_graph_diff_control_checks"] for row in sequences
        ),
        "full_graph_diff_checks_avoided": sum(
            row["full_graph_diff_checks_avoided_on_invalidation_decision_path"]
            for row in sequences
        ),
    }
    role = (
        "DELTA_GRAPH_AND_COMPILED_INVALIDATION"
        if family == PACKET_FAMILY
        else "DELTA_RETENTION_AND_INCREMENTAL_REVALIDATION"
    )
    gate = {
        key: value for key, value in base["registered_gate"].items() if key != "passed"
    }
    gate.update(
        certificate_delta_for_every_episode=metrics["delta_receipts"]
        == 2 * len(episode_indices),
        delta_join_for_every_nonterminal_epoch=metrics["delta_transition_joins"]
        == 2 * (len(episode_indices) - 1),
        zero_serialized_full_graph_scan_on_decision_path=all(
            row["serialized_full_graph_rows_scanned_for_invalidation_decision"]
            == 0
            for row in sequences
        ),
        delta_frontier_exactly_matches_full_diff_control=all(
            row["certificate_local_delta_drives_changed_state_frontier"] is True
            and row["matched_full_graph_diff_is_only_uncharged_control"] is True
            for row in sequences
        ),
        positive_full_graph_diff_compute_removed_from_decision_path=metrics[
            "full_graph_diff_checks_avoided"
        ]
        > 0,
        unaffected_graph_dependencies_are_retained=metrics["graph_retentions"] > 0,
        incremental_revalidation_is_observed=metrics["incremental_revalidations"] > 0,
        registered_role_positive=(
            metrics["graph_invalidations"] > 0
            and metrics["program_invalidations"] > 0
            if family == PACKET_FAMILY
            else metrics["graph_retentions"] > 0
            and metrics["incremental_revalidations"] > 0
            and histogram["SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE"] > 0
        ),
        factor_prior_strictly_reduces_acquisition_labels=(
            base["factor_prior_sample_reduction_within_progressive_policy"] > 0
        ),
        query_policy_noninferior=(
            base["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
        ),
        query_local_exact_overlay_remains_only_safety_authority=all(
            row["query_local_exact_overlay_remains_only_safety_authority"] is True
            and row["receipt_dependency_lifecycle_is_model_or_safety_authority"]
            is False
            for row in sequences
        ),
    )
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.certificate_delta_invalidation_occurrence.v175",
        "registered_delta_dependency_role": role,
        "online_typed_plan_source_histogram": histogram,
        "delta_invalidation_metrics": metrics,
        "online_plan_issuance_receipt_count": sum(
            row["online_plan_issuance_receipt_count"] for row in sequences
        ),
        "online_execution_join_receipt_count": sum(
            row["online_execution_join_receipt_count"] for row in sequences
        ),
        "registered_gate": gate,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V175_CROSS_FAMILY_COHORT",
        "delta_invalidation_changes_selected_action_order": False,
        "delta_invalidation_is_model_or_safety_authority": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v175(
            domains.CONSTRUCTION_K7_OCCURRENCE_V175_DOMAIN, payload
        ),
    }


def _target(args):
    return build_certificate_delta_invalidation_occurrence_v175(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def _frozen(raw, *, count, digest, identity_key, identity, name):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        raise ValueError(f"V175 frozen predecessor changed: {name}")
    return document


def build_certificate_delta_invalidation_campaign_v175(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v174_campaign_raw,
    v174_verification_raw,
):
    predecessor = _frozen(
        v174_campaign_raw,
        count=V174_CAMPAIGN_BYTE_COUNT,
        digest=V174_CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=V174_CAMPAIGN_ID,
        name="V174 campaign",
    )
    verification = _frozen(
        v174_verification_raw,
        count=V174_VERIFICATION_BYTE_COUNT,
        digest=V174_VERIFICATION_SHA256,
        identity_key="verification_id",
        identity=V174_VERIFICATION_ID,
        name="V174 verification",
    )
    if not (
        predecessor["registered_gate"]["passed"] is True
        and verification["producer_free_minimal_invalidation_reconstruction"] is True
        and verification[
            "producer_free_incremental_revalidation_chain_reconstruction"
        ]
        is True
    ):
        raise ValueError("V175 predecessor boundary changed")
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            bank_raw,
            verification_raw,
            classifier_receipt_raw,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target, args))
    histogram = {
        source: sum(row["online_typed_plan_source_histogram"][source] for row in rows)
        for source in TAXONOMY.values()
    }
    metric_keys = tuple(rows[0]["delta_invalidation_metrics"])
    metrics = {
        key: sum(row["delta_invalidation_metrics"][key] for row in rows)
        for key in metric_keys
    }
    accounting = {
        "online_plan_issuance_receipt_count": sum(
            row["online_plan_issuance_receipt_count"] for row in rows
        ),
        "online_execution_join_receipt_count": sum(
            row["online_execution_join_receipt_count"] for row in rows
        ),
        **metrics,
        "factor_prior_labels_avoided": sum(
            row["factor_prior_sample_reduction_within_progressive_policy"]
            for row in rows
        ),
        "query_policy_labels_avoided": sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
        ),
        "sample_labels_execution_steps_derivation_planning_receipt_delta_and_control_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    roles = {row["registered_delta_dependency_role"] for row in rows}
    gate = {
        "required_occurrence_count": config["required_target_occurrence_count"],
        "passed_occurrence_count": sum(row["registered_gate"]["passed"] for row in rows),
        "packet_and_reservoir_delta_roles_both_present": roles
        == {
            "DELTA_GRAPH_AND_COMPILED_INVALIDATION",
            "DELTA_RETENTION_AND_INCREMENTAL_REVALIDATION",
        },
        "all_four_online_plan_sources_observed": all(
            histogram[source] > 0 for source in TAXONOMY.values()
        ),
        "positive_selective_graph_invalidation_observed": metrics[
            "graph_invalidations"
        ]
        > 0,
        "positive_unaffected_graph_retention_observed": metrics[
            "graph_retentions"
        ]
        > 0,
        "positive_exact_state_program_invalidation_observed": metrics[
            "program_invalidations"
        ]
        > 0,
        "positive_incremental_revalidation_observed": metrics[
            "incremental_revalidations"
        ]
        > 0,
        "zero_full_graph_scan_on_every_invalidation_decision": all(
            row["registered_gate"][
                "zero_serialized_full_graph_scan_on_decision_path"
            ]
            for row in rows
        ),
        "positive_full_graph_diff_compute_removed_from_decision_path": metrics[
            "full_graph_diff_checks_avoided"
        ]
        > 0,
        "delta_frontier_matches_uncharged_control_each_occurrence": all(
            row["registered_gate"][
                "delta_frontier_exactly_matches_full_diff_control"
            ]
            for row in rows
        ),
        "factor_prior_strictly_reduces_labels_each_occurrence": all(
            row["factor_prior_sample_reduction_within_progressive_policy"] > 0
            for row in rows
        ),
        "query_policy_noninferior_each_occurrence": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
            for row in rows
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            row["registered_gate"]["certificate_failure_only_local_ground_distinctions"]
            for row in rows
        ),
        "delta_lifecycle_not_safety_authority": all(
            row["delta_invalidation_is_model_or_safety_authority"] is False
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.certificate_delta_invalidation_campaign.v175",
        "preregistration_id": preregistration_id,
        "frozen_v174_campaign_id": V174_CAMPAIGN_ID,
        "frozen_v174_verification_id": V174_VERIFICATION_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "online_typed_plan_source_histogram": histogram,
        "accounting": accounting,
        "registered_gate": gate,
        "certificate_delta_driven_invalidation_observed": gate["passed"],
        "factor_prior_sample_tax_reduction_observed": gate[
            "factor_prior_strictly_reduces_labels_each_occurrence"
        ],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V175_CROSS_FAMILY_COHORT",
        "delta_invalidation_changes_selected_action_order": False,
        "delta_invalidation_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v175(
            domains.CONSTRUCTION_K7_CAMPAIGN_V175_DOMAIN, payload
        ),
    }


__all__ = (
    "PACKET_FAMILY",
    "RESERVOIR_FAMILY",
    "build_certificate_delta_invalidation_campaign_v175",
    "build_certificate_delta_invalidation_occurrence_v175",
    "certificate_delta_invalidation_campaign_config_v175",
)

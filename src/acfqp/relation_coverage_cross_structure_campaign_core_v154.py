"""V154 cross-structure reuse of the frozen V153 acquisition operator."""

from __future__ import annotations

import copy
import hashlib
from types import FunctionType

from acfqp import anonymous_relational_factor_bank_acquisition_v148 as legacy_acquisition
from acfqp import construction_k7_domain_registry_extension_v154 as domains
from acfqp import cross_domain_relational_factor_bank_campaign_core_v149 as v149
from acfqp.certified_memoized_planner_sequence_v154 import (
    run_certified_memoized_planner_sequence_v154,
)
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    FAMILY,
    build_relation_fanout_routing_adapter_v154,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_coverage_acquisition_operator_v153 import (
    acquire_matched_relation_coverage_arms_v153,
    relation_coverage_then_path_stream_v153,
)
from acfqp.relation_coverage_cross_structure_application_receipt_v154 import (
    APPLICATION_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as APPLICATION_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as APPLICATION_RECEIPT_SHA256,
)


TARGET_FAMILIES = (FAMILY,)


def _clone(function, namespace):
    clone = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _verify_application_receipt(raw: bytes):
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or (
            APPLICATION_RECEIPT_ID != "0" * 64
            and (
                len(raw) != APPLICATION_RECEIPT_BYTE_COUNT
                or hashlib.sha256(raw).hexdigest() != APPLICATION_RECEIPT_SHA256
                or document.get("application_receipt_id") != APPLICATION_RECEIPT_ID
            )
        )
        or document.get("registered_application", {}).get("fresh_target_outcomes_accessed") is not False
        or document.get("operator_remains_query_order_heuristic_not_model_or_certificate_authority") is not True
    ):
        raise ValueError("V154 application receipt changed")
    return document


def build_nonrelational_ood_control_v154(config, *, seed: int):
    adapter = build_relation_fanout_routing_adapter_v154(seed, config, incompatible=True)
    batches = []
    error = None
    try:
        for batch in relation_coverage_then_path_stream_v153(adapter):
            batches.append(batch)
    except ValueError as caught:
        error = str(caught)
    rows = tuple(row for batch in batches for row in batch)
    payload = {
        "schema": "acfqp.nonrelational_ood_control.v154",
        "family": adapter.family,
        "seed": seed,
        "observation_batch_count": len(batches),
        "raw_transition_count": len(rows),
        "raw_transition_documents": [row.to_document() for row in rows],
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "relation_discovery_error": error,
        "no_exact_positive_one_to_one_descriptor_delta_relation": error
        == "V153 raw initial observations exposed no positive relation coverage",
        "factor_bank_bytes_supplied_to_ood_control": False,
        "factor_prior_instantiation_attempted": False,
        "operator_transfer_rejected_before_bank_access": True,
        "ground_observations_used_only_for_ood_compatibility_check": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
    }
    if (
        payload["observation_batch_count"] != 4
        or payload["raw_transition_count"] != 8
        or payload["no_exact_positive_one_to_one_descriptor_delta_relation"] is not True
    ):
        raise ValueError("V154 nonrelational OOD control did not reject exactly")
    return {
        **payload,
        "ood_control_id": domains.extension_content_id_v154(
            domains.CONSTRUCTION_K7_OOD_CONTROL_V154_DOMAIN, payload
        ),
    }


_OCCURRENCE_GLOBALS = dict(v149.__dict__)
_OCCURRENCE_GLOBALS.update(
    _BUILDERS={FAMILY: build_relation_fanout_routing_adapter_v154},
    acquire_matched_anonymous_relational_factor_bank_arms_v148=acquire_matched_relation_coverage_arms_v153,
    run_certificate_local_relational_overlay_sequence_v144r1=run_certified_memoized_planner_sequence_v154,
)
_BASE_OCCURRENCE = _clone(
    v149.build_cross_domain_relational_factor_bank_occurrence_v149,
    _OCCURRENCE_GLOBALS,
)


def build_relation_coverage_cross_structure_occurrence_v154(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    application_receipt_raw,
):
    application = _verify_application_receipt(application_receipt_raw)
    base = _BASE_OCCURRENCE(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
    )
    adapter = build_relation_fanout_routing_adapter_v154(seed, config)
    legacy = legacy_acquisition.acquire_matched_anonymous_relational_factor_bank_arms_v148(
        adapter, bank_raw, verification_raw, config
    )
    prior = base["anonymous_relational_factor_prior_acquisition"]
    strict = base["strict_no_prior_acquisition"]
    legacy_prior = legacy["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    operator_reduction = legacy_prior["ground_support_labels"] - prior["ground_support_labels"]
    factor_reduction = strict["ground_support_labels"] - prior["ground_support_labels"]
    ood = build_nonrelational_ood_control_v154(config, seed=seed + 2_000_000)
    sequences = (
        base["anonymous_relational_factor_prior_owned_sequence"],
        base["strict_no_prior_owned_sequence"],
    )
    accounting = {
        **base["accounting"],
        "legacy_path_first_prior_acquisition_labels": legacy_prior["ground_support_labels"],
        "labels_avoided_by_relation_coverage_operator_vs_legacy_prior": operator_reduction,
        "labels_avoided_by_factor_prior_within_same_adaptive_operator": factor_reduction,
        "nonrelational_ood_compatibility_observation_labels": ood["observation_batch_count"],
    }
    gate = {
        **base["registered_gate"],
        "application_receipt_frozen_before_target_outcomes": application["registered_application"]["fresh_target_outcomes_accessed"] is False,
        "same_exact_v153_operator_used": True,
        "operator_noninferior_to_legacy_path_first": operator_reduction >= 0,
        "factor_prior_noninferior_within_same_operator": factor_reduction >= 0,
        "relation_template_selected_in_prior_arm": prior["relational_artifact_expression_selected_count"] > 0,
        "same_relation_available_in_strict_pool": strict["relational_artifact_expression_selected_count"] > 0,
        "v115_memoized_plan_receipt_consumed_both_arms": all(sequence["v115_memoized_compiled_program_plan_receipts_consumed"] for sequence in sequences),
        "nonrelational_ood_rejected_before_bank_access": ood["operator_transfer_rejected_before_bank_access"] and ood["factor_bank_bytes_supplied_to_ood_control"] is False,
    }
    gate["passed"] = all(gate.values())
    legacy_summary = {
        "acquisition_id": legacy_prior["acquisition_id"],
        "ground_support_labels": legacy_prior["ground_support_labels"],
        "first_accepting_observation_label": legacy_prior["first_accepting_observation_label"],
        "raw_transition_sha256": legacy_prior["raw_transition_sha256"],
        "relational_artifact_expression_selected_count": legacy_prior["relational_artifact_expression_selected_count"],
    }
    payload = {
        **{key: value for key, value in base.items() if key != "occurrence_id"},
        "schema": "acfqp.relation_coverage_cross_structure_occurrence.v154",
        "application_receipt_id": application["application_receipt_id"],
        "legacy_path_first_prior_acquisition_summary": legacy_summary,
        "nonrelational_ood_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "operator_sample_reduction_vs_legacy_prior": operator_reduction,
        "factor_prior_sample_reduction_within_adaptive_operator": factor_reduction,
        "cross_structure_claim_scope": "ONLY_THE_PREREGISTERED_FANOUT_ROUTING_COHORT",
        "operator_is_planning_or_certificate_authority": False,
        "v153_evidence_preserved": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v154(
            domains.CONSTRUCTION_K7_OCCURRENCE_V154_DOMAIN, payload
        ),
    }


def _target(args):
    config = args[0]
    return build_relation_coverage_cross_structure_occurrence_v154(
        config,
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        application_receipt_raw=bytes.fromhex(config["_v154_application_receipt_hex"]),
    )


_CAMPAIGN_GLOBALS = dict(v149.__dict__)
_CAMPAIGN_GLOBALS.update(TARGET_FAMILIES=TARGET_FAMILIES, _target=_target)
_BASE_CAMPAIGN = _clone(
    v149.build_cross_domain_relational_factor_bank_campaign_document_v149,
    _CAMPAIGN_GLOBALS,
)


def build_relation_coverage_cross_structure_campaign_document_v154(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    application_receipt_raw,
):
    application = _verify_application_receipt(application_receipt_raw)
    execution_config = copy.deepcopy(config)
    execution_config["_v154_application_receipt_hex"] = application_receipt_raw.hex()
    base = _BASE_CAMPAIGN(
        execution_config,
        preregistration_id=preregistration_id,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
    )
    operator_reduction = sum(
        row["operator_sample_reduction_vs_legacy_prior"]
        for row in base["target_occurrences"]
    )
    factor_reduction = sum(
        row["factor_prior_sample_reduction_within_adaptive_operator"]
        for row in base["target_occurrences"]
    )
    gate = {
        **base["registered_gate"],
        "application_receipt_id": application["application_receipt_id"],
        "aggregate_operator_sample_reduction_vs_legacy_prior": operator_reduction,
        "aggregate_factor_prior_reduction_within_adaptive_operator": factor_reduction,
        "operator_noninferior_everywhere": all(row["operator_sample_reduction_vs_legacy_prior"] >= 0 for row in base["target_occurrences"]),
        "factor_prior_noninferior_within_operator_everywhere": all(row["factor_prior_sample_reduction_within_adaptive_operator"] >= 0 for row in base["target_occurrences"]),
        "operator_positive_in_aggregate": operator_reduction > 0,
        "factor_prior_positive_in_aggregate": factor_reduction > 0,
        "memoized_plan_receipt_consumed_everywhere": all(row["registered_gate"]["v115_memoized_plan_receipt_consumed_both_arms"] for row in base["target_occurrences"]),
        "nonrelational_ood_rejected_everywhere": all(row["registered_gate"]["nonrelational_ood_rejected_before_bank_access"] for row in base["target_occurrences"]),
    }
    gate["passed"] = (
        base["registered_gate"]["passed"]
        and gate["operator_noninferior_everywhere"]
        and gate["factor_prior_noninferior_within_operator_everywhere"]
        and gate["operator_positive_in_aggregate"]
        and gate["factor_prior_positive_in_aggregate"]
        and gate["memoized_plan_receipt_consumed_everywhere"]
        and gate["nonrelational_ood_rejected_everywhere"]
    )
    payload = {
        **{key: value for key, value in base.items() if key != "campaign_id"},
        "schema": "acfqp.relation_coverage_cross_structure_campaign.v154",
        "application_receipt_id": application["application_receipt_id"],
        "registered_gate": gate,
        "cross_structure_operator_reuse_observed": gate["passed"],
        "sample_tax_reduction_claim_scope": "ONLY_THE_PREREGISTERED_V153_AND_V154_RELATION_COHORTS",
        "operator_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v154(
            domains.CONSTRUCTION_K7_CAMPAIGN_V154_DOMAIN, payload
        ),
    }


__all__ = (
    "build_nonrelational_ood_control_v154",
    "build_relation_coverage_cross_structure_campaign_document_v154",
    "build_relation_coverage_cross_structure_occurrence_v154",
)

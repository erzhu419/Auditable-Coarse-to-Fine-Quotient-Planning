"""Fresh packet-batching cohort exercising all online plan-source branches."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib

from acfqp import construction_k7_domain_registry_extension_v173 as domains
from acfqp import fifth_family_total_plan_receipt_set_campaign_core_v168 as v168
from acfqp import online_typed_plan_receipt_campaign_core_v172 as v172
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET_BATCHING_FAMILY,
)
from acfqp.online_typed_plan_receipt_sequence_v172 import TAXONOMY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V172R1_CAMPAIGN_ID = "c904d48bd590a287c4a1085ffecf41920ddde5cbba7a958e3906232afdd4128b"
V172R1_CAMPAIGN_BYTE_COUNT = 14_761_292
V172R1_CAMPAIGN_SHA256 = "2988188d53f74266839e107fb2e6a378cf3d2b8dfbe5f29fae3076b36556fb99"
V172R1_VERIFICATION_ID = "200a3eb5fd8109a2f8ac8f9cdf612e080edcc67c2b68af44c406380f5784ef3f"
V172R1_VERIFICATION_BYTE_COUNT = 1_716
V172R1_VERIFICATION_SHA256 = "2285bd267a3e2f1270a67fa8bd3ccdd8f23a2d6b3ff2bb6009d89ae705f80869"


def branch_complete_online_receipt_campaign_config_v173():
    config = v168.fifth_family_total_plan_receipt_set_campaign_config_v168()
    config["families"][PACKET_BATCHING_FAMILY][
        "maximum_acquisition_labels"
    ] = 2_048
    return config


def build_branch_complete_online_receipt_occurrence_v173(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    if family != PACKET_BATCHING_FAMILY:
        raise ValueError("V173 target family is not packet batching")
    base = v172._BASE_V168_OCCURRENCE(  # noqa: SLF001
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
    gate = {
        key: value
        for key, value in base["registered_gate"].items()
        if key != "passed"
    }
    gate.update(
        all_plan_receipts_issued_online=all(
            sequence[
                "every_abstract_plan_receipt_issued_before_orderer_return"
            ]
            is True
            for sequence in sequences
        ),
        all_executions_join_prior_online_receipts=all(
            sequence["every_executed_action_joins_prior_online_receipt"] is True
            for sequence in sequences
        ),
        all_online_receipt_sources_in_closed_taxonomy=(
            set(histogram) == set(TAXONOMY.values())
        ),
        direct_compiled_program_order_observed=(
            histogram["DIRECT_COMPILED_PROGRAM_ORDER"] > 0
        ),
        observation_derived_order_observed=(
            histogram["OBSERVATION_DERIVED_QUOTIENT_ORDER"] > 0
        ),
        dependency_revalidated_reuse_observed=(
            histogram["DEPENDENCY_REVALIDATED_QUOTIENT_REUSE"] > 0
        ),
        factor_prior_strictly_reduces_acquisition_labels=(
            base["factor_prior_sample_reduction_within_progressive_policy"] > 0
        ),
        query_policy_noninferior=(
            base["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
        ),
    )
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.branch_complete_online_receipt_occurrence.v173",
        "online_typed_plan_source_histogram": histogram,
        "online_plan_issuance_receipt_count": sum(
            sequence["online_plan_issuance_receipt_count"]
            for sequence in sequences
        ),
        "online_execution_join_receipt_count": sum(
            sequence["online_execution_join_receipt_count"]
            for sequence in sequences
        ),
        "registered_gate": gate,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V173_PACKET_COHORT",
        "receipt_taxonomy_changes_planning_or_execution": False,
        "receipt_taxonomy_is_model_or_safety_authority": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v173(
            domains.CONSTRUCTION_K7_OCCURRENCE_V173_DOMAIN, payload
        ),
    }


def _target(args):
    return build_branch_complete_online_receipt_occurrence_v173(
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
        raise ValueError(f"V173 frozen predecessor changed: {name}")
    return document


def build_branch_complete_online_receipt_campaign_v173(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v172r1_campaign_raw,
    v172r1_verification_raw,
):
    predecessor = _frozen(
        v172r1_campaign_raw,
        count=V172R1_CAMPAIGN_BYTE_COUNT,
        digest=V172R1_CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=V172R1_CAMPAIGN_ID,
        name="V172r1 campaign",
    )
    verification = _frozen(
        v172r1_verification_raw,
        count=V172R1_VERIFICATION_BYTE_COUNT,
        digest=V172R1_VERIFICATION_SHA256,
        identity_key="verification_id",
        identity=V172R1_VERIFICATION_ID,
        name="V172r1 verification",
    )
    if not (
        predecessor["registered_gate"]["passed"] is True
        and verification["producer_free_online_issuance_reconstruction"] is True
        and verification["producer_free_execution_join_reconstruction"] is True
    ):
        raise ValueError("V173 predecessor boundary changed")
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
    accounting = {
        "online_plan_issuance_receipt_count": sum(
            row["online_plan_issuance_receipt_count"] for row in rows
        ),
        "online_execution_join_receipt_count": sum(
            row["online_execution_join_receipt_count"] for row in rows
        ),
        "factor_prior_labels_avoided": sum(
            row["factor_prior_sample_reduction_within_progressive_policy"]
            for row in rows
        ),
        "query_policy_labels_avoided": sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
        ),
        "execution_steps": sum(
            row["accounting"]["progressive_prior_execution_steps"]
            + row["accounting"]["progressive_strict_execution_steps"]
            for row in rows
        ),
        "sample_labels_execution_steps_derivation_planning_and_receipt_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "required_fresh_packet_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_fresh_packet_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "v172r1_frozen_predecessor_preserved": True,
        "all_four_online_typed_plan_sources_observed": all(
            histogram[source] > 0 for source in TAXONOMY.values()
        ),
        "every_plan_receipt_issued_online": all(
            row["registered_gate"]["all_plan_receipts_issued_online"] for row in rows
        ),
        "every_execution_joins_prior_online_receipt": all(
            row["registered_gate"]["all_executions_join_prior_online_receipts"]
            for row in rows
        ),
        "factor_prior_strictly_reduces_labels": all(
            row["factor_prior_sample_reduction_within_progressive_policy"] > 0
            for row in rows
        ),
        "query_policy_noninferior": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
            for row in rows
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            row["registered_gate"][
                "certificate_failure_only_local_ground_distinctions"
            ]
            for row in rows
        ),
        "receipt_taxonomy_does_not_change_planning_or_execution": all(
            row["receipt_taxonomy_changes_planning_or_execution"] is False
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_fresh_packet_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.branch_complete_online_receipt_campaign.v173",
        "preregistration_id": preregistration_id,
        "frozen_v172r1_campaign_id": V172R1_CAMPAIGN_ID,
        "frozen_v172r1_verification_id": V172R1_VERIFICATION_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "online_typed_plan_source_histogram": histogram,
        "accounting": accounting,
        "registered_gate": gate,
        "branch_complete_online_receipt_taxonomy_observed": gate[
            "all_four_online_typed_plan_sources_observed"
        ],
        "factor_prior_sample_tax_reduction_observed": gate[
            "factor_prior_strictly_reduces_labels"
        ],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V173_PACKET_COHORT",
        "receipt_taxonomy_changes_planning_or_execution": False,
        "receipt_taxonomy_is_model_or_safety_authority": False,
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
        "campaign_id": domains.extension_content_id_v173(
            domains.CONSTRUCTION_K7_CAMPAIGN_V173_DOMAIN, payload
        ),
    }


__all__ = (
    "PACKET_BATCHING_FAMILY",
    "branch_complete_online_receipt_campaign_config_v173",
    "build_branch_complete_online_receipt_campaign_v173",
    "build_branch_complete_online_receipt_occurrence_v173",
)

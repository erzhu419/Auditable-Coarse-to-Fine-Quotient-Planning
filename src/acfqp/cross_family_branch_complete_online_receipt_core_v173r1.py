"""Cross-family successor: packet supplies DIRECT, reservoir supplies MEMOIZED."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib

from acfqp import branch_complete_online_receipt_campaign_core_v173 as packet_v173
from acfqp import construction_k7_domain_registry_extension_v173r1 as domains
from acfqp import online_typed_plan_receipt_campaign_core_v172 as reservoir_v172
from acfqp.generic_packet_batching_adapter_v134 import FAMILY as PACKET_FAMILY
from acfqp.generic_reservoir_dispatch_adapter_v171 import (
    FAMILY as RESERVOIR_FAMILY,
    reservoir_dispatch_config_v171,
)
from acfqp.online_typed_plan_receipt_sequence_v172 import TAXONOMY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


TARGET_FAMILIES = (PACKET_FAMILY, RESERVOIR_FAMILY)
V172R1_CAMPAIGN_ID = "c904d48bd590a287c4a1085ffecf41920ddde5cbba7a958e3906232afdd4128b"
V172R1_VERIFICATION_ID = "200a3eb5fd8109a2f8ac8f9cdf612e080edcc67c2b68af44c406380f5784ef3f"
V173_FAILURE_ID = "ce5ca1449b5956b9b60fd3b0cfa45ce2ea987822f34145cb63ec4e5a87a5626d"


def cross_family_branch_complete_campaign_config_v173r1():
    config = packet_v173.branch_complete_online_receipt_campaign_config_v173()
    reservoir = reservoir_dispatch_config_v171()
    config["families"][RESERVOIR_FAMILY] = copy.deepcopy(
        reservoir["families"][RESERVOIR_FAMILY]
    )
    config["families"][RESERVOIR_FAMILY]["maximum_acquisition_labels"] = 2_048
    return config


def build_cross_family_branch_complete_occurrence_v173r1(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    if family == PACKET_FAMILY:
        base = packet_v173.build_branch_complete_online_receipt_occurrence_v173(
            config,
            family=family,
            seed=seed,
            episode_indices=episode_indices,
            bank_raw=bank_raw,
            verification_raw=verification_raw,
            classifier_receipt_raw=classifier_receipt_raw,
        )
        role = "DIRECT_BRANCH_COVERAGE"
    elif family == RESERVOIR_FAMILY:
        base = reservoir_v172.build_online_typed_plan_receipt_occurrence_v172(
            config,
            family=family,
            seed=seed,
            episode_indices=episode_indices,
            bank_raw=bank_raw,
            verification_raw=verification_raw,
            classifier_receipt_raw=classifier_receipt_raw,
        )
        role = "MEMOIZED_BRANCH_COVERAGE"
    else:
        raise ValueError("V173r1 target family is not registered")
    histogram = base["online_typed_plan_source_histogram"]
    if not (
        base["registered_gate"]["passed"] is True
        and base["online_plan_issuance_receipt_count"] > 0
        and base["online_execution_join_receipt_count"] > 0
        and set(histogram) == set(TAXONOMY.values())
        and base["factor_prior_sample_reduction_within_progressive_policy"] > 0
        and base["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
    ):
        raise ValueError("V173r1 source occurrence boundary changed")
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate", "sample_tax_claim_scope"}
        },
        "schema": "acfqp.cross_family_branch_complete_online_receipt_occurrence.v173r1",
        "registered_branch_coverage_role": role,
        "registered_gate": {
            "source_occurrence_gate_passed": True,
            "all_plan_receipts_issued_online": True,
            "all_executions_join_prior_online_receipts": True,
            "closed_four_source_taxonomy_preserved": True,
            "factor_prior_strictly_reduces_labels": True,
            "query_policy_noninferior": True,
            "passed": True,
        },
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V173R1_CROSS_FAMILY_COHORT",
        "receipt_taxonomy_changes_planning_or_execution": False,
        "receipt_taxonomy_is_model_or_safety_authority": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v173r1(
            domains.CONSTRUCTION_K7_OCCURRENCE_V173R1_DOMAIN, payload
        ),
    }


def _target(args):
    return build_cross_family_branch_complete_occurrence_v173r1(
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
        raise ValueError(f"V173r1 frozen predecessor changed: {name}")
    return document


def build_cross_family_branch_complete_campaign_v173r1(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v172r1_campaign_raw,
    v172r1_verification_raw,
    v173_failure_raw,
):
    v172_campaign = _frozen(
        v172r1_campaign_raw,
        count=14_761_292,
        digest="2988188d53f74266839e107fb2e6a378cf3d2b8dfbe5f29fae3076b36556fb99",
        identity_key="campaign_id",
        identity=V172R1_CAMPAIGN_ID,
        name="V172r1 campaign",
    )
    v172_verification = _frozen(
        v172r1_verification_raw,
        count=1_716,
        digest="2285bd267a3e2f1270a67fa8bd3ccdd8f23a2d6b3ff2bb6009d89ae705f80869",
        identity_key="verification_id",
        identity=V172R1_VERIFICATION_ID,
        name="V172r1 verification",
    )
    v173_failure = _frozen(
        v173_failure_raw,
        count=868,
        digest="51a17147979246fda296b52464a3363b7ef6c69e762855b5d9530d40c5f90318",
        identity_key="failure_id",
        identity=V173_FAILURE_ID,
        name="V173 failure",
    )
    if not (
        v172_campaign["registered_gate"]["passed"] is True
        and v172_verification["producer_free_online_issuance_reconstruction"] is True
        and v173_failure["same_preregistration_identity_may_be_rerun"] is False
    ):
        raise ValueError("V173r1 predecessor boundary changed")
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
    roles = {row["registered_branch_coverage_role"] for row in rows}
    accounting = {
        "online_plan_issuance_receipt_count": sum(
            row["online_plan_issuance_receipt_count"] for row in rows
        ),
        "online_execution_join_receipt_count": sum(
            row["online_execution_join_receipt_count"] for row in rows
        ),
        "factor_prior_labels_avoided": sum(
            row["factor_prior_sample_reduction_within_progressive_policy"] for row in rows
        ),
        "query_policy_labels_avoided": sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
        ),
        "sample_labels_execution_derivation_planning_and_receipt_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "required_occurrence_count": config["required_target_occurrence_count"],
        "passed_occurrence_count": sum(row["registered_gate"]["passed"] for row in rows),
        "packet_and_reservoir_roles_both_present": roles
        == {"DIRECT_BRANCH_COVERAGE", "MEMOIZED_BRANCH_COVERAGE"},
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
        "failed_v173_identity_preserved_not_rerun": True,
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.cross_family_branch_complete_online_receipt_campaign.v173r1",
        "preregistration_id": preregistration_id,
        "preserved_v173_failure_id": V173_FAILURE_ID,
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
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V173R1_CROSS_FAMILY_COHORT",
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
        "campaign_id": domains.extension_content_id_v173r1(
            domains.CONSTRUCTION_K7_CAMPAIGN_V173R1_DOMAIN, payload
        ),
    }


__all__ = (
    "PACKET_FAMILY",
    "RESERVOIR_FAMILY",
    "build_cross_family_branch_complete_campaign_v173r1",
    "cross_family_branch_complete_campaign_config_v173r1",
)

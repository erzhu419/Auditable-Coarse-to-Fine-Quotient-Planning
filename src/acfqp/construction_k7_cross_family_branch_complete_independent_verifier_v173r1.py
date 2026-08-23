"""Producer-free reexecution for the V173r1 cross-family campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
from typing import NoReturn

from acfqp import construction_k7_domain_registry_extension_v173r1 as domains
from acfqp import construction_k7_online_typed_plan_receipt_independent_verifier_v172r1 as prior
from acfqp.generic_packet_batching_adapter_v134 import FAMILY as PACKET_FAMILY
from acfqp.generic_reservoir_dispatch_adapter_v171 import FAMILY as RESERVOIR_FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "fbfbfa167d59806e19270c41e951da03c3fe7677bf6c668de1a747d164804ba9"
PREREGISTRATION_BYTE_COUNT = 3_525
PREREGISTRATION_SHA256 = "3f0811eb6ab03c99e1f7ac6c27cd2f2bead80dd2691d709f957b29f2a15002c2"
CAMPAIGN_ID = "418dc59c44243cb96e275539f564b1cd651664c9af19538d75f675093b8f2840"
CAMPAIGN_BYTE_COUNT = 37_582_314
CAMPAIGN_SHA256 = "ab871f3c8ecb6a19a8876458bb7c7e68737e7493489b89723191587d8219be46"
V173_FAILURE_ID = "ce5ca1449b5956b9b60fd3b0cfa45ce2ea987822f34145cb63ec4e5a87a5626d"
TARGETS = (
    (PACKET_FAMILY, 1_099_851, "DIRECT_BRANCH_COVERAGE"),
    (PACKET_FAMILY, 1_099_852, "DIRECT_BRANCH_COVERAGE"),
    (RESERVOIR_FAMILY, 1_109_851, "MEMOIZED_BRANCH_COVERAGE"),
    (RESERVOIR_FAMILY, 1_109_852, "MEMOIZED_BRANCH_COVERAGE"),
)
EPISODES = (1_023, 1_024, 1_025, 1_026)
TARGET_WORKERS = 2
TAXONOMY = {
    "DIRECT_COMPILED_PROGRAM_ORDER",
    "SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE",
    "OBSERVATION_DERIVED_QUOTIENT_ORDER",
    "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
}
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7CrossFamilyBranchCompleteIndependentVerifierV173R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossFamilyBranchCompleteIndependentVerifierV173R1Error(
        message
    )


def _frozen(raw, *, count, digest, identity_key, identity, name):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V173r1 independent frozen {name} changed")
    return document


def _replay(args):
    config, family, seed, bank_raw, verification_raw, classifier_raw = args
    return prior._BASE_V168(  # noqa: SLF001
        config,
        family=family,
        seed=seed,
        episode_indices=EPISODES,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_raw,
    )


def verify_cross_family_branch_complete_campaign_v173r1(
    preregistration_raw: bytes,
    campaign_raw: bytes,
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    preregistration = _frozen(
        preregistration_raw,
        count=PREREGISTRATION_BYTE_COUNT,
        digest=PREREGISTRATION_SHA256,
        identity_key="preregistration_id",
        identity=PREREGISTRATION_ID,
        name="preregistration",
    )
    campaign = _frozen(
        campaign_raw,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=CAMPAIGN_ID,
        name="campaign",
    )
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    if not (
        campaign["campaign_id"]
        == domains.extension_content_id_v173r1(
            domains.CONSTRUCTION_K7_CAMPAIGN_V173R1_DOMAIN, payload
        )
        and campaign["preregistration_id"] == preregistration["preregistration_id"]
        and campaign["preserved_v173_failure_id"] == V173_FAILURE_ID
        and preregistration["frozen_predecessors"][2]["failure_id"]
        == V173_FAILURE_ID
    ):
        _fail("V173r1 independent campaign ancestry changed")
    config = prior._config()  # noqa: SLF001
    args = [
        (config, family, seed, bank_raw, bank_verification_raw, classifier_raw)
        for family, seed, _ in TARGETS
    ]
    with ProcessPoolExecutor(max_workers=TARGET_WORKERS) as executor:
        replayed = list(executor.map(_replay, args))
    rows = campaign["target_occurrences"]
    if len(rows) != len(replayed) or len(rows) != len(TARGETS):
        _fail("V173r1 independent target cardinality changed")
    histogram = {source: 0 for source in TAXONOMY}
    total_receipts = total_joins = factor_avoided = query_avoided = 0
    occurrence_ids = []
    for (family, seed, role), base, row in zip(TARGETS, replayed, rows, strict=True):
        if not (
            row["target_family"] == family
            and row["seed"] == seed
            and row["episode_indices"] == list(EPISODES)
            and row["registered_branch_coverage_role"] == role
            and canonical_json_bytes(row["progressive_prior_sequence"])
            == canonical_json_bytes(base["progressive_prior_sequence"])
            and canonical_json_bytes(row["progressive_strict_sequence"])
            == canonical_json_bytes(base["progressive_strict_sequence"])
            and row["factor_prior_sample_reduction_within_progressive_policy"]
            == base["factor_prior_sample_reduction_within_progressive_policy"]
            and row["query_policy_sample_reduction_vs_legacy_path_first"]
            == base["query_policy_sample_reduction_vs_legacy_path_first"]
            and row["registered_gate"]["passed"] is True
        ):
            _fail("V173r1 independent target reexecution changed")
        row_payload = {
            key: value for key, value in row.items() if key != "occurrence_id"
        }
        if row["occurrence_id"] != domains.extension_content_id_v173r1(
            domains.CONSTRUCTION_K7_OCCURRENCE_V173R1_DOMAIN, row_payload
        ):
            _fail("V173r1 independent occurrence identity changed")
        sequences = (
            row["progressive_prior_sequence"],
            row["progressive_strict_sequence"],
        )
        for sequence in sequences:
            prior._verify_sequence(sequence)  # noqa: SLF001
        row_receipts = sum(
            sequence["online_plan_issuance_receipt_count"] for sequence in sequences
        )
        row_joins = sum(
            sequence["online_execution_join_receipt_count"] for sequence in sequences
        )
        if not (
            row_receipts == row["online_plan_issuance_receipt_count"]
            and row_joins == row["online_execution_join_receipt_count"]
            and row_joins == sum(sequence["execution_step_count"] for sequence in sequences)
        ):
            _fail("V173r1 independent receipt accounting changed")
        total_receipts += row_receipts
        total_joins += row_joins
        factor_avoided += row["factor_prior_sample_reduction_within_progressive_policy"]
        query_avoided += row["query_policy_sample_reduction_vs_legacy_path_first"]
        for source in TAXONOMY:
            histogram[source] += row["online_typed_plan_source_histogram"][source]
        occurrence_ids.append(row["occurrence_id"])
    if not (
        all(histogram[source] > 0 for source in TAXONOMY)
        and campaign["online_typed_plan_source_histogram"] == histogram
        and campaign["target_occurrence_ids"] == occurrence_ids
        and campaign["accounting"]["online_plan_issuance_receipt_count"]
        == total_receipts
        and campaign["accounting"]["online_execution_join_receipt_count"]
        == total_joins
        and campaign["accounting"]["factor_prior_labels_avoided"]
        == factor_avoided
        and campaign["accounting"]["query_policy_labels_avoided"]
        == query_avoided
        and factor_avoided > 0
        and query_avoided >= 0
        and campaign["registered_gate"]["passed"] is True
        and campaign["receipt_taxonomy_changes_planning_or_execution"] is False
        and campaign["receipt_taxonomy_is_model_or_safety_authority"] is False
        and campaign["query_local_exact_overlay_remains_only_safety_authority"] is True
        and campaign["complete_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    ):
        _fail("V173r1 independent aggregate or claim boundary changed")
    verification_payload = {
        "schema": "acfqp.cross_family_branch_complete_online_receipt_verification.v173r1",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_id": CAMPAIGN_ID,
        "preserved_v173_failure_id": V173_FAILURE_ID,
        "verified_target_families": [family for family, _, _ in TARGETS],
        "verified_target_seeds": [seed for _, seed, _ in TARGETS],
        "verified_occurrence_ids": occurrence_ids,
        "verified_online_plan_issuance_receipt_count": total_receipts,
        "verified_online_execution_join_receipt_count": total_joins,
        "verified_online_typed_plan_source_histogram": histogram,
        "verified_factor_prior_labels_avoided": factor_avoided,
        "verified_query_policy_labels_avoided": query_avoided,
        "producer_free_target_outcome_reexecution": True,
        "producer_free_all_four_online_sources_reconstructed": True,
        "producer_free_online_issuance_and_execution_joins_reconstructed": True,
        "factor_prior_sample_tax_reduction_independently_verified": True,
        "receipt_taxonomy_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v173r1(
            domains.CONSTRUCTION_K7_VERIFICATION_V173R1_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V173r1 frozen verification changed")
    return document


__all__ = (
    "VERIFICATION_ID",
    "verify_cross_family_branch_complete_campaign_v173r1",
)

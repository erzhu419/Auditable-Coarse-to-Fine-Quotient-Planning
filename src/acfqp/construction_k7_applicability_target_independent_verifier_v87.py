"""Producer-free verification of the frozen V87 incompatibility failure."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v87 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "e5432505db2bf911324d3d719986493bfa81aa131439ee31367da9329cc2b0d8"
CAMPAIGN_BYTE_COUNT = 85_215
CAMPAIGN_SHA256 = "233d01e1429fa1742ca9cfae9aaac29e26310840ee2354166df967888088cb95"
PREREGISTRATION_ID = "cdde11a8c0ff6f38aaa5f087129081439cc1ca9490bff57f3eb1c1710cb9fa74"
PROJECTED_MODEL_ARTIFACT_ID = "c069fb2a39fee3b9dc7dc847fef15369cf8d65c5d6322bbaae1bbceb924a476e"
APPLICABILITY_MODEL_ARTIFACT_ID = "07ee765058797bc083db3180bb26952a79a224f8e8aef2f8f284237f87137f77"
SOURCE_MODEL_ID = "401693d9b6f3a50ec3581f0878181955cc804324cad003e23635b6af2e9bb1db"
APPLICABILITY_PROGRAM_ID = "956edacfc94e1312a3a6efa42e0fc2b91bf3266f61a06b3a3a5b8a1f03d38ef0"
TARGET_SEEDS = (899_101, 899_102, 899_103, 899_104, 899_105, 899_106)
VERIFICATION_ID = "d8af2766c723c1b42895f9c4b5d85e2557c366af2ab6473f19516c9b54fe19d5"
EXPECTED_CANONICAL_BYTE_COUNT = 1_823
EXPECTED_CANONICAL_SHA256 = "0a6add06ec67cd4c4a4d0396217badf39f8cb38266c18bf144a6bf58e9eb3178"
_V59_ACQUISITION_DOMAIN = b"acfqp:construction-k7-true-bit-symmetric-acquisition:v59\x00"


class ConstructionK7ApplicabilityTargetIndependentVerifierV87Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ApplicabilityTargetIndependentVerifierV87Error(message)


def _v59_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        _V59_ACQUISITION_DOMAIN + canonical_json_bytes(payload)
    ).hexdigest()


def verify_applicability_target_campaign_bytes_v87(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V87 campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V87 campaign canonical form changed")
    payload = {
        key: value for key, value in document.items() if key != "campaign_id"
    }
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or domains.extension_content_id_v87(
            domains.CONSTRUCTION_K7_APPLICABILITY_TARGET_CAMPAIGN_V87_DOMAIN,
            payload,
        )
        != CAMPAIGN_ID
    ):
        _fail("V87 campaign content identity changed")
    fixed = {
        "schema": "acfqp.applicability_conditioned_target_campaign.v87",
        "preregistration_id": PREREGISTRATION_ID,
        "projected_model_artifact_id": PROJECTED_MODEL_ARTIFACT_ID,
        "applicability_model_artifact_id": APPLICABILITY_MODEL_ARTIFACT_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "action_applicability_program_id": APPLICABILITY_PROGRAM_ID,
        "model_and_applicability_frozen_before_all_target_outcomes": True,
        "target_outcomes_used_to_refit_source_model_or_applicability": False,
        "multi_step_abstract_ordering_primary_observed": False,
        "multi_step_planning_primarily_in_abstract_model_claimed": False,
        "certificate_failure_only_local_ground_recovery_observed": True,
        "query_local_exact_overlay_only_safety_authority": True,
        "sample_tax_reduction_verified": False,
        "producer_free_verification_present": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in fixed.items()):
        _fail("V87 failure claim boundary changed")
    occurrences = document.get("target_occurrences")
    if (
        type(occurrences) is not list
        or [row.get("target_seed") for row in occurrences] != list(TARGET_SEEDS)
    ):
        _fail("V87 failed target identities changed")
    occurrence_ids = []
    labels = 0
    candidate_ids = []
    for row in occurrences:
        if type(row) is not dict:
            _fail("V87 failed occurrence changed")
        occurrence_payload = {
            key: value for key, value in row.items() if key != "occurrence_id"
        }
        if row.get("occurrence_id") != domains.extension_content_id_v87(
            domains.CONSTRUCTION_K7_APPLICABILITY_TARGET_OCCURRENCE_V87_DOMAIN,
            occurrence_payload,
        ):
            _fail("V87 failed occurrence identity changed")
        acquisition = row.get("target_common_partial_acquisition")
        if type(acquisition) is not dict:
            _fail("V87 failure acquisition changed")
        acquisition_payload = {
            key: value
            for key, value in acquisition.items()
            if key != "acquisition_id"
        }
        candidate = acquisition.get("candidate")
        candidate_payload = (
            {
                key: value
                for key, value in candidate.items()
                if key != "candidate_id"
            }
            if type(candidate) is dict
            else {}
        )
        if (
            acquisition.get("acquisition_id") != _v59_id(acquisition_payload)
            or type(candidate) is not dict
            or candidate.get("candidate_id") != _v59_id(candidate_payload)
            or acquisition.get("schema") != "acfqp.true_bit_partial_acquisition.v59"
            or acquisition.get("arm") != "ANONYMOUS_FACTOR_PRIOR_ON"
            or acquisition.get("seed") != row.get("target_seed")
            or acquisition.get("ground_support_labels")
            != row.get("target_common_partial_ground_support_labels")
            or acquisition.get("complete_world_model_claimed") is not False
            or candidate.get("complete_world_model_claimed") is not False
            or candidate.get("planning_authority_present") is not False
            or row.get("target_structurally_compatible") is not False
            or row.get("matched_ablation") is not None
            or row.get("incompatible_schema_ood_control") is not None
            or row.get("status")
            != "TARGET_STRUCTURALLY_INCOMPATIBLE_NO_TRANSFER_NO_EPISODE"
            or row.get("failure_reason") is not None
            or row.get("certificate_failure_only_local_ground_distinctions")
            is not True
            or row.get("query_local_exact_overlay_only_safety_authority") is not True
            or row.get("official_execution_allowed") is not False
        ):
            _fail("V87 failed occurrence semantics changed")
        occurrence_ids.append(row["occurrence_id"])
        candidate_ids.append(candidate["candidate_id"])
        labels += row["target_common_partial_ground_support_labels"]
    gate = {
        "required_target_occurrence_count": 6,
        "actual_target_occurrence_count": 6,
        "minimum_compatible_completed_target_count": 2,
        "actual_structurally_compatible_target_count": 0,
        "actual_completed_matched_target_count": 0,
        "every_compatible_target_completed": True,
        "certificate_failure_only_ground_discipline_clean": True,
        "every_successful_abstract_output_accepted_as_legal": False,
        "multi_step_abstract_ordering_coverage_on_every_completed_target": False,
        "applicability_filter_effective_on_every_completed_target": False,
        "strict_incompatible_schema_no_transfer_verified": False,
        "passed": False,
    }
    if document.get("registered_gate") != gate:
        _fail("V87 frozen failure Gate changed")
    sample = {
        "derived_target_certificate_local_labels": 0,
        "strict_target_certificate_local_labels": 0,
        "derived_minus_strict_target_labels": 0,
        "actual_target_sample_reduction_observed": False,
        "reduction_required_for_this_gate": False,
    }
    if document.get("sample_tax_measurement") != sample:
        _fail("V87 failure sample-tax record changed")
    accounting = {
        "offline_v85r1_template_source_labels": 515,
        "offline_residual_library_labels": 204,
        "offline_v85r1_source_common_partial_labels": 170,
        "offline_v85r1_source_certificate_local_labels": 318,
        "offline_v85r1_group_query_counts_not_physical_labels": 266,
        "offline_applicability_state_action_classifications_not_physical_labels": 4260,
        "target_common_partial_labels": labels,
        "derived_target_certificate_local_labels": 0,
        "strict_target_certificate_local_labels": 0,
        "derived_target_execution_steps": 0,
        "strict_target_execution_steps": 0,
        "derived_abstract_planning_compute_events": 0,
        "derived_applicability_relation_evaluations": 0,
        "derived_inapplicable_action_branch_evaluations_avoided": 0,
        "strict_abstract_planning_compute_events": 0,
        "all_axes_separate": True,
    }
    if document.get("accounting") != accounting:
        _fail("V87 failure accounting changed")
    verification_payload = {
        "schema": "acfqp.applicability_conditioned_failure_verification.v87",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": CAMPAIGN_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "target_occurrence_ids": occurrence_ids,
        "target_candidate_ids": candidate_ids,
        "target_occurrence_count": 6,
        "target_common_partial_labels": labels,
        "structurally_compatible_target_count": 0,
        "matched_target_episode_count": 0,
        "all_registered_target_partial_acquisitions_replayed": True,
        "all_incompatible_targets_retained_without_episode": True,
        "registered_failure_gate_verified": True,
        "sample_tax_reduction_verified": False,
        "multi_step_planning_primarily_in_abstract_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v87(
            domains.CONSTRUCTION_K7_APPLICABILITY_TARGET_VERIFICATION_V87_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V87 failure verification changed")
    return result


__all__ = ("verify_applicability_target_campaign_bytes_v87",)

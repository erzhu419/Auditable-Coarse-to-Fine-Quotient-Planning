"""Outcome-free preregistration for the V95 persistent second-domain Gate."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v95 as domains
from acfqp import construction_k7_permutation_matched_sample_tax_preregistration_v89 as previous
from acfqp.construction_k7_action_applicability_model_v87 import (
    MODEL_ARTIFACT_ID as APPLICABILITY_MODEL_ARTIFACT_ID,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    MODEL_ARTIFACT_ID as PROJECTED_MODEL_ARTIFACT_ID,
)
from acfqp.construction_k7_total_label_meta_prior_campaign_v94 import (
    CAMPAIGN_ID as V94_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V94_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_total_label_meta_prior_independent_verifier_v94 import (
    EXPECTED_CANONICAL_SHA256 as V94_VERIFICATION_SHA256,
    VERIFICATION_ID as V94_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "835cf97"
PREREGISTRATION_ID = (
    "e6bebdef1c6a4bae2569fd370282b94655e8168e83f6da14f057cbad02630e67"
)
EXPECTED_CANONICAL_BYTE_COUNT = 7_150
EXPECTED_CANONICAL_SHA256 = (
    "7e838b863b50f1a8d1a611f7325c881f3e9250a54efa0299cf001ab67485adb0"
)
TARGET_FAMILY = "BALANCED_BATCH_REFINEMENT"
TARGET_SEEDS = (982_101, 982_102)
SOURCE_EPISODE_INDEX = 0
TARGET_EPISODE_INDICES = (15, 16)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_META_PRIOR_ODDS = 16
CONFIDENCE_DENOMINATOR = 4
MAXIMUM_APPLICABILITY_GROUND_SUPPORT_LABELS = 40
MAXIMUM_INCREMENTAL_CERTIFICATE_GROUND_SUPPORT_LABELS = 100_000
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("artifacts/world_model/v86_projected_disagreement_model.json", 136251, "30c5b8775ae05039a971c20c52450efb29fcc8b57d81a38f70c9567fd9ef2bec"),
    ("artifacts/world_model/v87_action_applicability_model.json", 2978, "b564c19963692a593f38c8b64520643b71d28fb2c274d998fcd439553d1f7fd4"),
    ("src/acfqp/construction_k7_domain_registry_extension_v95.py", 1937, "10e7cf0ecf83834b625531a040a4c8198df86f1df079016f1f3bec47a50180d1"),
    ("src/acfqp/generic_action_key_permutation_adapter_v62.py", 5861, "1f3d6c47923b23458f9ef41cc693f82807fac0f804d608847637075cd64f7c72"),
    ("src/acfqp/generic_projected_low_label_applicability_v76.py", 11314, "687ce2cf970e95c3ecdba9b02652aa339762dab5855240b7d755eddd8a677f9b"),
    ("src/acfqp/generic_projected_persistent_sequence_v78.py", 11616, "dc61290662c5fcfdfc85632ce5d65e0c160e19e366240367855b6a08bde65a96"),
    ("src/acfqp/generic_preloaded_certificate_receding_engine_v74.py", 12503, "a470ec2d750353c7d951d7d82494b307be61fb99eb3ca3bd8b2023880d7392c3"),
    ("src/acfqp/generic_coordinate_alignment_v60.py", 17009, "f424ddf0ef853beaed91db0c5106ce8b04cb45f4a26ddf9467c251f9ca08b6bf"),
    ("src/acfqp/generic_coordinate_aligned_certificate_planner_v60.py", 9546, "ec3fad926bf3ec9eba6f3fb94ffb32f787849558b5fc212b88a798500acda30e"),
    ("src/acfqp/generic_applicability_conditioned_planner_v58.py", 14772, "afd72df879951c941cee9b2dbb59b4eb9847d69e1cacc17c166b3b8ae93a20a6"),
    ("src/acfqp/generic_partial_factor_proposal_v15.py", 29347, "af483f002d35c96dd5d8bd9be9df92d83fb547ae2423fe8478936990ac874f3f"),
    ("src/acfqp/generic_projected_disagreement_model_compiler_v56.py", 12065, "e92b87e65151bcaaf9aa7ab30a4421760f46f4cc15015e66d6d5e6931c8e2364"),
    ("src/acfqp/adaptive_mdl_cross_domain_campaign_core_v56.py", 47728, "a4cd8356aa17f564c226196f1aab1ff0933500d9e7620d285fdbc51e7e157b0c"),
    ("src/acfqp/true_bit_symmetric_three_domain_campaign_core_v59.py", 23230, "9d9b3d8dd1de994216bebe8acdb5748f82b5499e398f935a5c175055c9273395"),
    ("src/acfqp/persistent_second_domain_campaign_core_v95.py", 17581, "60ea17e2a5260cac161b7dbec05a088248bb98a2c79d66b1583ff66120409267"),
    ("src/acfqp/phase3e_ids.py", 414040, "afc1431487eb6aab76bf2fa2e234afa8498d69f37757abd700001538c097e888"),
)


class ConstructionK7PersistentSecondDomainPreregistrationV95Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentSecondDomainPreregistrationV95Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative, _, _ in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v95() -> dict[str, Any]:
    config = previous.campaign_config_v89()
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        source_meta_prior_odds=SOURCE_META_PRIOR_ODDS,
        confidence_denominator=CONFIDENCE_DENOMINATOR,
        maximum_applicability_ground_support_labels=(
            MAXIMUM_APPLICABILITY_GROUND_SUPPORT_LABELS
        ),
        maximum_incremental_certificate_ground_support_labels=(
            MAXIMUM_INCREMENTAL_CERTIFICATE_GROUND_SUPPORT_LABELS
        ),
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.persistent_second_domain_preregistration.v95",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v94_campaign_id": V94_CAMPAIGN_ID,
            "v94_campaign_sha256": V94_CAMPAIGN_SHA256,
            "v94_verification_id": V94_VERIFICATION_ID,
            "v94_verification_sha256": V94_VERIFICATION_SHA256,
            "projected_model_artifact_id": PROJECTED_MODEL_ARTIFACT_ID,
            "applicability_model_artifact_id": APPLICABILITY_MODEL_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v95_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V95),
            "frozen_before_any_registered_v95_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_not_previously_exposed": True,
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "target_episode_indices_unique": (
                len(set(TARGET_EPISODE_INDICES)) == len(TARGET_EPISODE_INDICES)
            ),
            "action_identifier_permutation_derived_without_transition_outcomes": True,
        },
        "construction_contract": {
            "same_constructor_projection_stop_rule_query_identities_and_exact_engine": True,
            "only_source_meta_prior_odds_differs_between_acquisition_arms": True,
            "source_meta_prior_odds": SOURCE_META_PRIOR_ODDS,
            "source_meta_prior_strength_preregistered_empirical_not_universal": True,
            "acquisition_rows_paid_once_and_persisted_across_queries": True,
            "certificate_rows_persisted_after_first_failed_certificate": True,
            "every_new_ground_query_must_follow_a_failed_certificate": True,
            "strict_cold_direct_restarts_without_free_rows_for_every_query": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "incompatible_model_must_reject_before_target_observation": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_target_must_complete_prior_no_prior_and_direct_sequences": True,
            "meta_prior_acquisition_labels_strictly_lower_on_every_target": True,
            "second_query_must_require_zero_new_certificate_labels": True,
            "multi_step_abstract_proposal_primary_on_every_query": True,
            "meta_prior_lifetime_labels_noninferior_to_no_prior_and_direct_on_every_target": True,
            "meta_prior_lifetime_labels_strictly_better_than_no_prior_and_direct_in_aggregate": True,
            "strict_incompatible_model_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_applicability_labels_per_arm_occurrence": (
                MAXIMUM_APPLICABILITY_GROUND_SUPPORT_LABELS
            ),
            "maximum_incremental_certificate_labels_per_episode": (
                MAXIMUM_INCREMENTAL_CERTIFICATE_GROUND_SUPPORT_LABELS
            ),
            "maximum_abstract_support_branch_evaluations_per_plan": (
                campaign_config_v95()[
                    "maximum_relational_support_branch_evaluations"
                ]
            ),
        },
        "accounting_contract": {
            "source_labels_separate": True,
            "target_acquisition_labels_separate_by_arm": True,
            "persistent_certificate_labels_separate_by_arm": True,
            "execution_steps_separate_by_arm": True,
            "projection_derivation_and_abstract_planning_compute_separate": True,
            "strict_direct_labels_restart_per_query": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v95_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "sample_tax_reduction_replicated_in_second_registered_domain": False,
            "sample_tax_reduction_generalized_beyond_two_registered_domain_families": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v95(
            domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_PREREGISTRATION_V95_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PersistentSecondDomainPreregistrationV95:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v95(
                domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_PREREGISTRATION_V95_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V95 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PersistentSecondDomainPreregistrationV95 | None = None


def freeze_persistent_second_domain_preregistration_v95(
) -> PersistentSecondDomainPreregistrationV95:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V95 preregistered source closure changed")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V95 frozen preregistration changed")
    _CACHE = PersistentSecondDomainPreregistrationV95(_ISSUER, raw, identity)
    return _CACHE


def verify_persistent_second_domain_preregistration_v95(
    value: Any,
) -> PersistentSecondDomainPreregistrationV95:
    if type(value) is not PersistentSecondDomainPreregistrationV95:
        _fail("V95 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_persistent_second_domain_preregistration_v95()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V95 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v95",
    "freeze_persistent_second_domain_preregistration_v95",
    "verify_persistent_second_domain_preregistration_v95",
)

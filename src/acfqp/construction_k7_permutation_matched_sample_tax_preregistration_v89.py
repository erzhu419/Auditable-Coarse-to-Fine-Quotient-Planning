"""Outcome-free preregistration for the V89 matched sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v89 as domains
from acfqp import construction_k7_replayable_coordinate_preregistration_v88 as previous
from acfqp.construction_k7_action_applicability_model_v87 import (
    MODEL_ARTIFACT_ID as APPLICABILITY_MODEL_ARTIFACT_ID,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    MODEL_ARTIFACT_ID as PROJECTED_MODEL_ARTIFACT_ID,
)
from acfqp.permutation_matched_sample_tax_campaign_core_v89 import (
    build_permutation_matched_sample_tax_campaign_document_v89,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("c14c0c9", "3d3cd84")
PREREGISTRATION_ID = "e463074f1155bc9510feda4c128c86f7652a8a8719e04ced80a94a2661d770b4"
EXPECTED_CANONICAL_BYTE_COUNT = 6_183
EXPECTED_CANONICAL_SHA256 = "4e774b23ab7ee35977d92a29b69f4ebacc9b6a3c5a56d86957130601c2b888a8"
V87_FAILED_CAMPAIGN_ID = previous.V87_FAILED_CAMPAIGN_ID
V87R1_CAMPAIGN_ID = previous.V87R1_CAMPAIGN_ID
V87R1_VERIFICATION_ID = previous.V87R1_VERIFICATION_ID
V88_CAMPAIGN_ID = "041f758ee32cb6fdef0b1218a23bdbfe47a115781ef1fc8f9c557a79a7b065b2"
V88_VERIFICATION_ID = "e176b3b775511c2c98e650e99fdb183555833ca5c4638bc7fc5d4b6f998be327"
TARGET_FAMILY = "BALANCED_BATCH_REFINEMENT"
TARGET_SEEDS = (929_101, 929_102, 929_103, 929_104, 929_105, 929_106)
SOURCE_EPISODE_INDEX = 0
TARGET_EPISODE_INDEX = 12
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MINIMUM_COMPLETED_TARGET_COUNT = 6
MINIMUM_REDUCED_TARGET_OCCURRENCE_COUNT = 4
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "artifacts/world_model/v86_projected_disagreement_model.json",
    "artifacts/world_model/v87_action_applicability_model.json",
    "src/acfqp/construction_k7_domain_registry_extension_v89.py",
    "src/acfqp/generic_action_key_permutation_adapter_v62.py",
    "src/acfqp/generic_coordinate_alignment_v60.py",
    "src/acfqp/generic_coordinate_alignment_independent_replay_v61.py",
    "src/acfqp/generic_coordinate_aligned_certificate_planner_v60.py",
    "src/acfqp/generic_applicability_conditioned_planner_v58.py",
    "src/acfqp/generic_applicability_certificate_planner_v59.py",
    "src/acfqp/permutation_matched_sample_tax_campaign_core_v89.py",
)
FROZEN_SOURCE_FACTS = (
    ("artifacts/world_model/v86_projected_disagreement_model.json", 136251, "30c5b8775ae05039a971c20c52450efb29fcc8b57d81a38f70c9567fd9ef2bec"),
    ("artifacts/world_model/v87_action_applicability_model.json", 2978, "b564c19963692a593f38c8b64520643b71d28fb2c274d998fcd439553d1f7fd4"),
    ("src/acfqp/construction_k7_domain_registry_extension_v89.py", 1625, "88ff724bc299c0fb5992aeda1c7e5c410ef94fa2b84dd0d5893428d5735873b9"),
    ("src/acfqp/generic_action_key_permutation_adapter_v62.py", 5861, "1f3d6c47923b23458f9ef41cc693f82807fac0f804d608847637075cd64f7c72"),
    ("src/acfqp/generic_coordinate_alignment_v60.py", 17009, "f424ddf0ef853beaed91db0c5106ce8b04cb45f4a26ddf9467c251f9ca08b6bf"),
    ("src/acfqp/generic_coordinate_alignment_independent_replay_v61.py", 16563, "1d71bace6e23a1aab323ecb154a3726e57f85eda71b6f6dfda9f5f6e9cc12cd7"),
    ("src/acfqp/generic_coordinate_aligned_certificate_planner_v60.py", 9546, "ec3fad926bf3ec9eba6f3fb94ffb32f787849558b5fc212b88a798500acda30e"),
    ("src/acfqp/generic_applicability_conditioned_planner_v58.py", 14772, "afd72df879951c941cee9b2dbb59b4eb9847d69e1cacc17c166b3b8ae93a20a6"),
    ("src/acfqp/generic_applicability_certificate_planner_v59.py", 16867, "60e56328833716aca9a7dea64af7caba02cd2c345b67ffe313b398e200359566"),
    ("src/acfqp/permutation_matched_sample_tax_campaign_core_v89.py", 15734, "55862fb2611a7b9f9e22cab3d3ab91826bc4136f7c758f9ce534950ccb6351cf"),
)


class ConstructionK7PermutationMatchedSampleTaxPreregistrationV89Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PermutationMatchedSampleTaxPreregistrationV89Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
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


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v89() -> dict[str, Any]:
    config = previous.campaign_config_v88()
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        target_episode_index=TARGET_EPISODE_INDEX,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        minimum_completed_target_count_v89=MINIMUM_COMPLETED_TARGET_COUNT,
        minimum_reduced_target_occurrence_count_v89=(
            MINIMUM_REDUCED_TARGET_OCCURRENCE_COUNT
        ),
        v88_campaign_id=V88_CAMPAIGN_ID,
        v88_verification_id=V88_VERIFICATION_ID,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.permutation_matched_sample_tax_preregistration.v89",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v87_failed_campaign_id": V87_FAILED_CAMPAIGN_ID,
            "v87r1_campaign_id": V87R1_CAMPAIGN_ID,
            "v87r1_verification_id": V87R1_VERIFICATION_ID,
            "v88_campaign_id": V88_CAMPAIGN_ID,
            "v88_verification_id": V88_VERIFICATION_ID,
            "projected_model_artifact_id": PROJECTED_MODEL_ARTIFACT_ID,
            "applicability_model_artifact_id": APPLICABILITY_MODEL_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v89_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V89),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_permutation_matched_sample_tax_campaign_document_v89
            ),
            "post_outcome_identity_wrapper_excluded_from_construction_source_closure": True,
            "frozen_before_any_registered_v89_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_disjoint_from_v88": min(TARGET_SEEDS) > max(previous.TARGET_SEEDS),
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "target_episode_index": TARGET_EPISODE_INDEX,
            "permutation_algorithm": "SHA256_RANK_SEED_AND_OLD_KEY",
            "permutation_domain_hex": b"acfqp:generic-action-key-permutation:v62\x00".hex(),
        },
        "construction_contract": {
            "action_identifier_permutation_derived_without_transition_outcomes": True,
            "anonymous_action_descriptor_fields_preserved": True,
            "raw_alignment_inputs_embedded_before_episode": True,
            "independent_replayer_must_rederive_alignment_and_permutation": True,
            "same_synthesizer_stopping_rule_and_exact_certificate_engine": True,
            "only_reusable_model_availability_differs_between_episode_arms": True,
            "paired_ground_execution_and_outcome_tape_must_match": True,
            "every_ground_query_must_follow_failed_certificate": True,
            "query_local_exact_overlay_only_safety_authority": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "minimum_completed_target_count": MINIMUM_COMPLETED_TARGET_COUNT,
            "minimum_reduced_target_occurrence_count": (
                MINIMUM_REDUCED_TARGET_OCCURRENCE_COUNT
            ),
            "aggregate_target_sample_reduction_required": True,
            "per_target_label_regression_forbidden": True,
            "unique_alignment_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "maximum_target_ground_support_labels_per_arm": 100_000,
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
        },
        "accounting_contract": {
            "source_labels_target_labels_execution_steps_alignment_compute_and_planning_compute_separate": True,
            "derived_and_strict_certificate_labels_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v89_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "sample_tax_reduction_verified": False,
            "multi_step_planning_primarily_in_abstract_model_claimed": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v89_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v89(
            domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_PREREGISTRATION_V89_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PermutationMatchedSampleTaxPreregistrationV89:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v89(
                domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_PREREGISTRATION_V89_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V89 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PermutationMatchedSampleTaxPreregistrationV89 | None = None


def freeze_permutation_matched_sample_tax_preregistration_v89(
) -> PermutationMatchedSampleTaxPreregistrationV89:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V89 live construction sources differ from preregistered facts")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V89 preregistration changed")
    _CACHE = PermutationMatchedSampleTaxPreregistrationV89(_ISSUER, raw, identity)
    return _CACHE


def verify_permutation_matched_sample_tax_preregistration_v89(
    value: Any,
) -> PermutationMatchedSampleTaxPreregistrationV89:
    if type(value) is not PermutationMatchedSampleTaxPreregistrationV89:
        _fail("V89 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_permutation_matched_sample_tax_preregistration_v89()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V89 preregistration differs from frozen bytes")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v89",
    "freeze_permutation_matched_sample_tax_preregistration_v89",
    "verify_permutation_matched_sample_tax_preregistration_v89",
)

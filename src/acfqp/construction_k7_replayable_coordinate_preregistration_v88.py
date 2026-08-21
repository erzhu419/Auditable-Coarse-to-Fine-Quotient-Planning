"""Outcome-free preregistration for V88 replayable coordinate transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_coordinate_aligned_target_preregistration_v87r1 as previous
from acfqp import construction_k7_domain_registry_extension_v88 as domains
from acfqp.construction_k7_action_applicability_model_v87 import MODEL_ARTIFACT_ID as APPLICABILITY_MODEL_ARTIFACT_ID
from acfqp.construction_k7_projected_model_artifact_v86 import MODEL_ARTIFACT_ID as PROJECTED_MODEL_ARTIFACT_ID
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.replayable_coordinate_target_campaign_core_v88 import build_replayable_coordinate_target_campaign_document_v88


IMPLEMENTATION_COMMIT = "4aa371f"
PREREGISTRATION_ID = "1deb31c178a6cbda3dcaf2db4a969662119bb064a60c3e4aebef5724359821c8"
EXPECTED_CANONICAL_BYTE_COUNT = 5_948
EXPECTED_CANONICAL_SHA256 = "a50cad556120cc1bb513bc347f1804a43871448f8e8587727952678820d10757"
V87_FAILED_CAMPAIGN_ID = previous.V87_FAILED_CAMPAIGN_ID
V87R1_CAMPAIGN_ID = "33e9d49933e8b2d94169911170732b178095ce55fe52258c6ccfb9d425990739"
V87R1_VERIFICATION_ID = "9a5fdb135fcebe2e4a31077e7a542d9af2338ecb1c2d76eda1e3f4f72eedd29d"
TARGET_FAMILY = "BALANCED_BATCH_REFINEMENT"
TARGET_SEEDS = (919_101, 919_102, 919_103, 919_104, 919_105, 919_106)
SOURCE_EPISODE_INDEX = 0
TARGET_EPISODE_INDEX = 11
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MINIMUM_REPLAYABLE_COMPLETED_TARGET_COUNT = 4
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "artifacts/world_model/v86_projected_disagreement_model.json",
    "artifacts/world_model/v87_action_applicability_model.json",
    "src/acfqp/construction_k7_domain_registry_extension_v88.py",
    "src/acfqp/generic_coordinate_alignment_v60.py",
    "src/acfqp/generic_coordinate_alignment_independent_replay_v61.py",
    "src/acfqp/generic_coordinate_aligned_certificate_planner_v60.py",
    "src/acfqp/generic_applicability_conditioned_planner_v58.py",
    "src/acfqp/generic_applicability_certificate_planner_v59.py",
    "src/acfqp/replayable_coordinate_target_campaign_core_v88.py",
    "src/acfqp/construction_k7_replayable_coordinate_campaign_v88.py",
)
FROZEN_SOURCE_FACTS = (
    ("artifacts/world_model/v86_projected_disagreement_model.json", 136251, "30c5b8775ae05039a971c20c52450efb29fcc8b57d81a38f70c9567fd9ef2bec"),
    ("artifacts/world_model/v87_action_applicability_model.json", 2978, "b564c19963692a593f38c8b64520643b71d28fb2c274d998fcd439553d1f7fd4"),
    ("src/acfqp/construction_k7_domain_registry_extension_v88.py", 1617, "374970f32f88c32e6395924b7403a1a60020958e562e1caafb2711370a78537e"),
    ("src/acfqp/generic_coordinate_alignment_v60.py", 17009, "f424ddf0ef853beaed91db0c5106ce8b04cb45f4a26ddf9467c251f9ca08b6bf"),
    ("src/acfqp/generic_coordinate_alignment_independent_replay_v61.py", 16563, "1d71bace6e23a1aab323ecb154a3726e57f85eda71b6f6dfda9f5f6e9cc12cd7"),
    ("src/acfqp/generic_coordinate_aligned_certificate_planner_v60.py", 9546, "ec3fad926bf3ec9eba6f3fb94ffb32f787849558b5fc212b88a798500acda30e"),
    ("src/acfqp/generic_applicability_conditioned_planner_v58.py", 14772, "afd72df879951c941cee9b2dbb59b4eb9847d69e1cacc17c166b3b8ae93a20a6"),
    ("src/acfqp/generic_applicability_certificate_planner_v59.py", 16867, "60e56328833716aca9a7dea64af7caba02cd2c345b67ffe313b398e200359566"),
    ("src/acfqp/replayable_coordinate_target_campaign_core_v88.py", 13744, "5e3dc8f8919601f84b7f911574e3ac02de38a24105f8d145cb2e4e03282e7566"),
    ("src/acfqp/construction_k7_replayable_coordinate_campaign_v88.py", 4306, "d0c15e71edfe0848f6ff7f53255f06c146358ad05892941e07ee66350a1deeb2"),
)


class ConstructionK7ReplayableCoordinatePreregistrationV88Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReplayableCoordinatePreregistrationV88Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append({
            "relative_path": relative,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
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


def campaign_config_v88() -> dict[str, Any]:
    config = previous.campaign_config_v87r1()
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        target_episode_index=TARGET_EPISODE_INDEX,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        minimum_replayable_completed_target_count=MINIMUM_REPLAYABLE_COMPLETED_TARGET_COUNT,
        v87_failed_campaign_id=V87_FAILED_CAMPAIGN_ID,
        v87r1_campaign_id=V87R1_CAMPAIGN_ID,
        v87r1_verification_id=V87R1_VERIFICATION_ID,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.replayable_coordinate_preregistration.v88",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v87_failed_campaign_id": V87_FAILED_CAMPAIGN_ID,
            "v87r1_campaign_id": V87R1_CAMPAIGN_ID,
            "v87r1_verification_id": V87R1_VERIFICATION_ID,
            "projected_model_artifact_id": PROJECTED_MODEL_ARTIFACT_ID,
            "applicability_model_artifact_id": APPLICABILITY_MODEL_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v88_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V88),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_replayable_coordinate_target_campaign_document_v88
            ),
            "frozen_before_any_registered_v88_target_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v87_failure_and_v87r1_success_preserved": True,
            "v87r1_missing_embedded_raw_alignment_inputs_not_hidden": True,
            "fresh_v88_identities_disjoint_from_all_predecessors": True,
            "blind_seed_substitution_or_posthoc_selection_used": False,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_disjoint_from_v87r1": min(TARGET_SEEDS) > max(previous.TARGET_SEEDS),
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "target_episode_index": TARGET_EPISODE_INDEX,
        },
        "construction_contract": {
            "common_partial_raw_transition_rows_embedded_before_episode": True,
            "anonymous_action_catalogue_embedded_before_episode": True,
            "independent_replayer_must_rederive_exact_alignment_from_embedded_bytes": True,
            "coordinate_alignment_and_source_models_frozen_before_episode": True,
            "target_episode_outcomes_cannot_select_alignment_or_refit_models": True,
            "same_exact_certificate_engine_in_both_arms": True,
            "every_ground_query_must_follow_failed_certificate": True,
            "query_local_exact_overlay_only_safety_authority": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "minimum_replayable_completed_target_count": MINIMUM_REPLAYABLE_COMPLETED_TARGET_COUNT,
            "raw_alignment_inputs_required_on_every_completed_target": True,
            "unique_alignment_required": True,
            "multi_step_abstract_ordering_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "target_sample_reduction_required": False,
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
            "registered_v88_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "multi_step_planning_primarily_in_abstract_model_claimed": False,
            "sample_tax_reduction_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v88_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v88(
            domains.CONSTRUCTION_K7_REPLAYABLE_COORDINATE_PREREGISTRATION_V88_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReplayableCoordinatePreregistrationV88:
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
            or domains.extension_content_id_v88(
                domains.CONSTRUCTION_K7_REPLAYABLE_COORDINATE_PREREGISTRATION_V88_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V88 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ReplayableCoordinatePreregistrationV88 | None = None


def freeze_replayable_coordinate_preregistration_v88() -> ReplayableCoordinatePreregistrationV88:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V88 preregistration changed")
    _CACHE = ReplayableCoordinatePreregistrationV88(_ISSUER, raw, identity)
    return _CACHE


def verify_replayable_coordinate_preregistration_v88(
    value: Any,
) -> ReplayableCoordinatePreregistrationV88:
    if type(value) is not ReplayableCoordinatePreregistrationV88:
        _fail("V88 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_replayable_coordinate_preregistration_v88()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V88 preregistration differs from frozen bytes")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v88",
    "freeze_replayable_coordinate_preregistration_v88",
    "verify_replayable_coordinate_preregistration_v88",
)

"""Outcome-free preregistration for V87 applicability-conditioned transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v87 as domains
from acfqp import construction_k7_projected_target_preregistration_v86 as previous
from acfqp.applicability_target_campaign_core_v87 import (
    build_applicability_target_campaign_document_v87,
)
from acfqp.construction_k7_action_applicability_model_v87 import (
    MODEL_ARTIFACT_ID as APPLICABILITY_MODEL_ARTIFACT_ID,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    MODEL_ARTIFACT_ID as PROJECTED_MODEL_ARTIFACT_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "5da5bdd"
PREREGISTRATION_ID = "cdde11a8c0ff6f38aaa5f087129081439cc1ca9490bff57f3eb1c1710cb9fa74"
EXPECTED_CANONICAL_BYTE_COUNT = 6_017
EXPECTED_CANONICAL_SHA256 = "9e1a1d5a4bd67c328bf5a4532bde6375690de71f8f81f259748f0064aca469d8"
V86_CAMPAIGN_ID = "7e40be0ebf5f68c42f050e5cd441ba1d81dca603328fda380de6fe01d52f7cae"
V86_VERIFICATION_ID = "407284fb94ab6c2431bc99d9f7b706b84efdaac5f8f319209e6fb5596cebe0d0"
TARGET_FAMILY = "BALANCED_BATCH_REFINEMENT"
TARGET_SEEDS = (899_101, 899_102, 899_103, 899_104, 899_105, 899_106)
SOURCE_EPISODE_INDEX = 0
TARGET_EPISODE_INDEX = 9
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MINIMUM_COMPATIBLE_COMPLETED_TARGET_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "artifacts/world_model/v86_projected_disagreement_model.json",
    "artifacts/world_model/v87_action_applicability_model.json",
    "src/acfqp/construction_k7_domain_registry_extension_v87.py",
    "src/acfqp/construction_k7_projected_model_artifact_v86.py",
    "src/acfqp/construction_k7_action_applicability_model_v87.py",
    "src/acfqp/generic_action_applicability_compiler_v58.py",
    "src/acfqp/generic_applicability_conditioned_planner_v58.py",
    "src/acfqp/generic_applicability_certificate_planner_v59.py",
    "src/acfqp/applicability_target_campaign_core_v87.py",
    "src/acfqp/construction_k7_applicability_target_campaign_v87.py",
)
FROZEN_SOURCE_FACTS = (
    ("artifacts/world_model/v86_projected_disagreement_model.json", 136251, "30c5b8775ae05039a971c20c52450efb29fcc8b57d81a38f70c9567fd9ef2bec"),
    ("artifacts/world_model/v87_action_applicability_model.json", 2978, "b564c19963692a593f38c8b64520643b71d28fb2c274d998fcd439553d1f7fd4"),
    ("src/acfqp/construction_k7_domain_registry_extension_v87.py", 1627, "85425165a546febe57bc9990a034f780b790a17e90cd78cb91a86f7f0118ced2"),
    ("src/acfqp/construction_k7_projected_model_artifact_v86.py", 2816, "9ce071589f9fa60bf6cc32f56518e88316152827832206654e96c78754f0b5e2"),
    ("src/acfqp/construction_k7_action_applicability_model_v87.py", 4079, "e72edc8c42ca31f5c8a4aeaf339dff9bdc47d5264df251f0fd84d4d0f52066d5"),
    ("src/acfqp/generic_action_applicability_compiler_v58.py", 10227, "44e079a8b45e01c17fe66c18f4f1a4698296f31fb00549a5bf1d70a7ceed256e"),
    ("src/acfqp/generic_applicability_conditioned_planner_v58.py", 14772, "afd72df879951c941cee9b2dbb59b4eb9847d69e1cacc17c166b3b8ae93a20a6"),
    ("src/acfqp/generic_applicability_certificate_planner_v59.py", 16867, "60e56328833716aca9a7dea64af7caba02cd2c345b67ffe313b398e200359566"),
    ("src/acfqp/applicability_target_campaign_core_v87.py", 15499, "e0994e282288574e97162978c698e816aa39de9991797ace3574f63b16bc604f"),
    ("src/acfqp/construction_k7_applicability_target_campaign_v87.py", 4713, "1c8911f419ea941936ae33e7d4e018a47bfd5365698e364e61d47d813642b88b"),
)


class ConstructionK7ApplicabilityTargetPreregistrationV87Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ApplicabilityTargetPreregistrationV87Error(message)


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


def campaign_config_v87() -> dict[str, Any]:
    config = previous.campaign_config_v86()
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        target_episode_index=TARGET_EPISODE_INDEX,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        minimum_compatible_completed_target_count=(
            MINIMUM_COMPATIBLE_COMPLETED_TARGET_COUNT
        ),
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.applicability_conditioned_target_preregistration.v87",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v86_campaign_id": V86_CAMPAIGN_ID,
            "v86_verification_id": V86_VERIFICATION_ID,
            "projected_model_artifact_id": PROJECTED_MODEL_ARTIFACT_ID,
            "applicability_model_artifact_id": APPLICABILITY_MODEL_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v87_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V87),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_applicability_target_campaign_document_v87
            ),
            "frozen_before_any_registered_v87_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_disjoint_from_v86": min(TARGET_SEEDS)
            > max(previous.TARGET_SEEDS),
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "target_episode_index": TARGET_EPISODE_INDEX,
            "source_and_target_episode_indices_disjoint": True,
        },
        "construction_contract": {
            "applicability_program_derived_only_from_frozen_source_observations": True,
            "anonymous_state_action_relation_grammar_used": True,
            "target_outcomes_cannot_select_or_refit_model_or_applicability": True,
            "same_exact_certificate_engine_in_both_arms": True,
            "only_world_model_and_applicability_availability_differs": True,
            "every_ground_query_must_follow_failed_certificate": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "incompatible_schema_must_reject_before_abstract_search": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "minimum_compatible_completed_target_count": (
                MINIMUM_COMPATIBLE_COMPLETED_TARGET_COUNT
            ),
            "every_compatible_target_must_complete_both_arms": True,
            "every_successful_abstract_output_must_be_accepted_as_legal": True,
            "accepted_abstract_orderings_must_cover_every_execution_step": True,
            "applicability_filter_must_avoid_inapplicable_branches": True,
            "certificate_failure_only_ground_discipline_required": True,
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
            "source_physical_labels_separate": True,
            "source_derived_state_action_classifications_not_physical_labels": True,
            "target_common_partial_labels_separate": True,
            "derived_and_strict_certificate_labels_separate": True,
            "execution_steps_separate": True,
            "abstract_planning_compute_separate": True,
            "applicability_relation_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v87_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "multi_step_abstract_ordering_primary_observed": False,
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
        "fresh_registered_v87_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v87(
            domains.CONSTRUCTION_K7_APPLICABILITY_TARGET_PREREGISTRATION_V87_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ApplicabilityTargetPreregistrationV87:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v87(
                domains.CONSTRUCTION_K7_APPLICABILITY_TARGET_PREREGISTRATION_V87_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V87 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ApplicabilityTargetPreregistrationV87 | None = None


def freeze_applicability_target_preregistration_v87(
) -> ApplicabilityTargetPreregistrationV87:
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
        _fail("frozen V87 preregistration changed")
    _CACHE = ApplicabilityTargetPreregistrationV87(_ISSUER, raw, identity)
    return _CACHE


def verify_applicability_target_preregistration_v87(
    value: Any,
) -> ApplicabilityTargetPreregistrationV87:
    if type(value) is not ApplicabilityTargetPreregistrationV87:
        _fail("V87 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_applicability_target_preregistration_v87()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V87 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_SEEDS",
    "campaign_config_v87",
    "freeze_applicability_target_preregistration_v87",
    "verify_applicability_target_preregistration_v87",
)

"""Outcome-free preregistration for the V96 persistent joint successor Gate."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v96 as domains
from acfqp import construction_k7_multi_residual_planning_preregistration_v67 as previous
from acfqp.construction_k7_multi_residual_planning_campaign_v67 import (
    CAMPAIGN_ID as V67_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V67_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_multi_residual_planning_independent_verifier_v67 import (
    EXPECTED_CANONICAL_SHA256 as V67_VERIFICATION_SHA256,
    VERIFICATION_ID as V67_VERIFICATION_ID,
)
from acfqp.construction_k7_persistent_second_domain_campaign_v95 import (
    CAMPAIGN_ID as V95_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V95_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_persistent_second_domain_independent_verifier_v95 import (
    EXPECTED_CANONICAL_SHA256 as V95_VERIFICATION_SHA256,
    VERIFICATION_ID as V95_VERIFICATION_ID,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    EXPECTED_CANONICAL_SHA256 as V62_LIBRARY_SHA256,
    LIBRARY_ARTIFACT_ID as V62_LIBRARY_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("c730156", "6f6c6b2")
PREREGISTRATION_ID = "535c2020329e2dc0d6d2c9742dd2be0ddd1b5ec447d9e891b8468d7cc16d0d85"
EXPECTED_CANONICAL_BYTE_COUNT = 5959
EXPECTED_CANONICAL_SHA256 = "2ecc34ffe36d5e1e2a4fd6553d9a9bd2d3e000667f56187bffdb4dae85a890c0"
TARGET_FAMILY = "COUPLED_EXCHANGE"
TARGET_SEEDS = (997_101, 997_102)
TARGET_EPISODE_INDICES = (21, 22, 23)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v96.py", 1741, "27fd09e700e3b4fc89cf12686ee602cc996be080e9f3fd65bdeb783575c195ff"),
    ("src/acfqp/generic_persistent_multi_residual_sequence_v96.py", 17285, "5e898d361fd6dd37ca7a159afc21981ecba9eb6202a0b13b74ff6e7f620a5174"),
    ("src/acfqp/persistent_multi_residual_campaign_core_v96.py", 13078, "3173d45c70021aa1ea18e4715a3f98510d24355e40ba4a35771988a97012f312"),
    ("src/acfqp/generic_multi_residual_certificate_planner_v26.py", 15056, "3f60bad172f0199160ab629b2369c6252f8d76d822150c05df6690c5e3c13e40"),
    ("src/acfqp/generic_multi_residual_abstract_planner_v25.py", 15840, "741a5f4551b9a7b3ae8d651e8771d3deab4b65a02cdaa76498810d7a23b6bc47"),
    ("src/acfqp/generic_multi_residual_acquisition_v24.py", 7722, "60927b7c9a51000c705820639bafbd188c46e536f8c6d9826ca48d052a619c24"),
    ("src/acfqp/generic_preloaded_certificate_receding_engine_v74.py", 12503, "a470ec2d750353c7d951d7d82494b307be61fb99eb3ca3bd8b2023880d7392c3"),
    ("src/acfqp/true_bit_symmetric_three_domain_campaign_core_v59.py", 23230, "9d9b3d8dd1de994216bebe8acdb5748f82b5499e398f935a5c175055c9273395"),
    ("src/acfqp/construction_k7_residual_factor_library_v62.py", 10225, "6fbe73b77d7e806d04a3163c7010a83ef82b11c52b2e169bdec239a28d836881"),
    ("src/acfqp/construction_k7_multi_residual_planning_preregistration_v67.py", 10418, "96d143828503e3909dec7d9b0fd21d1461dee828f3f929515a13a56e72c2c71f"),
    ("src/acfqp/phase3e_ids.py", 414040, "afc1431487eb6aab76bf2fa2e234afa8498d69f37757abd700001538c097e888"),
)


class ConstructionK7PersistentMultiResidualPreregistrationV96Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentMultiResidualPreregistrationV96Error(message)


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


def campaign_config_v96() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v67())
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.persistent_multi_residual_preregistration.v96",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v62_residual_library_sha256": V62_LIBRARY_SHA256,
            "v67_campaign_id": V67_CAMPAIGN_ID,
            "v67_campaign_sha256": V67_CAMPAIGN_SHA256,
            "v67_verification_id": V67_VERIFICATION_ID,
            "v67_verification_sha256": V67_VERIFICATION_SHA256,
            "v95_campaign_id": V95_CAMPAIGN_ID,
            "v95_campaign_sha256": V95_CAMPAIGN_SHA256,
            "v95_verification_id": V95_VERIFICATION_ID,
            "v95_verification_sha256": V95_VERIFICATION_SHA256,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v96_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V96),
            "frozen_before_any_registered_v96_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "target_episode_indices_unique": (
                len(set(TARGET_EPISODE_INDICES))
                == len(TARGET_EPISODE_INDICES)
            ),
        },
        "construction_contract": {
            "same_partial_candidate_and_observations_between_residual_prior_arms": True,
            "only_switched_variable": (
                "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH"
            ),
            "at_least_two_residual_proposals_required_for_joint_successor": True,
            "joint_successor_retained_across_later_queries_as_fallible_heuristic": True,
            "partial_fallback_uses_same_compiled_partial_candidate": True,
            "persistent_exact_overlay_exclusively_discharges_safety": True,
            "every_new_ground_query_must_follow_failed_certificate": True,
            "strict_cold_direct_restarts_without_free_rows_each_episode": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_target_must_retain_at_least_two_joint_residual_proposals": True,
            "every_target_later_queries_must_be_ground_label_free": True,
            "meta_lifetime_labels_must_not_exceed_no_residual_prior": True,
            "meta_lifetime_labels_must_be_strictly_below_cold_direct_in_aggregate": True,
            "joint_abstract_plan_and_executed_match_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_joint_support_branch_evaluations": campaign_config_v96()[
                "maximum_joint_support_branch_evaluations"
            ],
            "joint_support_feasible_beam_width": campaign_config_v96()[
                "joint_support_feasible_beam_width"
            ],
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "partial_acquisition_and_certificate_labels_separate": True,
            "meta_no_residual_prior_and_cold_direct_labels_separate": True,
            "execution_steps_separate": True,
            "multi_residual_synthesis_and_abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v96_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "persistent_joint_residual_integration_verified": False,
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
        "preregistration_id": domains.extension_content_id_v96(
            domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_PREREGISTRATION_V96_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PersistentMultiResidualPreregistrationV96:
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
            or domains.extension_content_id_v96(
                domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_PREREGISTRATION_V96_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V96 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PersistentMultiResidualPreregistrationV96 | None = None


def freeze_persistent_multi_residual_preregistration_v96(
) -> PersistentMultiResidualPreregistrationV96:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V96 preregistered source closure changed")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V96 frozen preregistration changed")
    _CACHE = PersistentMultiResidualPreregistrationV96(_ISSUER, raw, identity)
    return _CACHE


def verify_persistent_multi_residual_preregistration_v96(
    value: Any,
) -> PersistentMultiResidualPreregistrationV96:
    if type(value) is not PersistentMultiResidualPreregistrationV96:
        _fail("V96 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_persistent_multi_residual_preregistration_v96()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V96 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v96",
    "freeze_persistent_multi_residual_preregistration_v96",
    "verify_persistent_multi_residual_preregistration_v96",
)

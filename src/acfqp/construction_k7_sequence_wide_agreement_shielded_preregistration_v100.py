"""Outcome-free preregistration for sequence-wide shield coverage V100."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v100 as domains
from acfqp import construction_k7_agreement_shielded_preregistration_v99 as previous
from acfqp.construction_k7_agreement_shielded_campaign_v99 import (
    CAMPAIGN_ID as V99_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V99_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_agreement_shielded_independent_verifier_v99 import (
    EXPECTED_CANONICAL_SHA256 as V99_VERIFICATION_SHA256,
    VERIFICATION_ID as V99_VERIFICATION_ID,
)
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    EXPECTED_CANONICAL_SHA256 as SOURCE_LIBRARY_SHA256,
    SOURCE_LIBRARY_ARTIFACT_ID,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    EXPECTED_CANONICAL_SHA256 as V62_LIBRARY_SHA256,
    LIBRARY_ARTIFACT_ID as V62_LIBRARY_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("5b0434a",)
PREREGISTRATION_ID = "414e2cc6cd9170d4228097d756dbc7106eccbf07bc198366fc2fcd968b5ea9ea"
EXPECTED_CANONICAL_BYTE_COUNT = 7_762
EXPECTED_CANONICAL_SHA256 = "f6e52a0edef12f588c51ab5281c3d1a215f756d0373a5a04046949855ca0d2d1"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_007_101),
    ("BALANCED_BATCH_REFINEMENT", 1_007_102),
    ("MAINTENANCE_CASCADE", 1_007_103),
    ("MAINTENANCE_CASCADE", 1_007_104),
)
TARGET_EPISODE_INDICES = (81, 82, 83)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v100.py", 1814, "517936271c7262bd3b9aaa6f7b1a12efdfc43ebab932913cab5aa1b9a3be1bbf"),
    ("src/acfqp/sequence_wide_agreement_shielded_campaign_core_v100.py", 11188, "eabbe5718baee7b3ebf72eccf5fd1dff6a47443e697491cf2e19566b9e5d3ba2"),
    ("src/acfqp/construction_k7_domain_registry_extension_v99.py", 1701, "bfd33f746f6fb9e31e6185be2f8b86dae8cb64671680073a61ada343adc920b8"),
    ("src/acfqp/generic_abstract_partial_agreement_shield_v99.py", 3293, "d94822047a66cced0531c82b96feed968b9f648d797c6995c956bdd90423fe5e"),
    ("src/acfqp/generic_agreement_shielded_online_certificate_planner_v99.py", 19197, "cc79497d1661bcf74ea78c1d7a33ecef65c283fd38b328e7f26a4ca6324bdfd9"),
    ("src/acfqp/generic_persistent_agreement_shielded_sequence_v99.py", 14550, "db8e0b8d69a3adc8ada457ac253cc081ce534ab14db795c84e94f5284c6681c5"),
    ("src/acfqp/agreement_shielded_cross_family_campaign_core_v99.py", 14043, "1b90353ff7e191b000807127702573c48ec5ca1d1dbf76338645d65d6901eea5"),
    ("src/acfqp/construction_k7_agreement_shielded_independent_verifier_v99.py", 30107, "5c332aef6a834b73f069ad82b59fcc89028738316fd820946f2a186de02096c4"),
    ("src/acfqp/generic_multi_residual_acquisition_v24.py", 7722, "60927b7c9a51000c705820639bafbd188c46e536f8c6d9826ca48d052a619c24"),
    ("src/acfqp/generic_partial_factor_proposal_v15.py", 29347, "af483f002d35c96dd5d8bd9be9df92d83fb547ae2423fe8478936990ac874f3f"),
    ("src/acfqp/generic_post_dependency_residual_v97.py", 20112, "03d476fd8a354de13dbcfa9b70bf2fe0ca9c20e67b861e9dd2c62f9f9df48111"),
    ("src/acfqp/generic_preloaded_certificate_receding_engine_v74.py", 12503, "a470ec2d750353c7d951d7d82494b307be61fb99eb3ca3bd8b2023880d7392c3"),
    ("src/acfqp/generic_persistent_multi_residual_sequence_v96.py", 17285, "5e898d361fd6dd37ca7a159afc21981ecba9eb6202a0b13b74ff6e7f620a5174"),
    ("src/acfqp/true_bit_symmetric_three_domain_campaign_core_v59.py", 23230, "9d9b3d8dd1de994216bebe8acdb5748f82b5499e398f935a5c175055c9273395"),
    ("src/acfqp/construction_k7_post_dependency_source_library_v97.py", 10639, "672c5d0c48d4ed0489e4dace9d9dd78b3f85328f473a7c6c5a3bd9ae8324e6c0"),
    ("src/acfqp/construction_k7_residual_factor_library_v62.py", 10225, "6fbe73b77d7e806d04a3163c7010a83ef82b11c52b2e169bdec239a28d836881"),
    ("src/acfqp/phase3e_ids.py", 414040, "afc1431487eb6aab76bf2fa2e234afa8498d69f37757abd700001538c097e888"),
)


class ConstructionK7SequenceWideAgreementShieldedPreregistrationV100Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SequenceWideAgreementShieldedPreregistrationV100Error(
        message
    )


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": relative,
            "byte_count": len((SOURCE_ROOT / relative).read_bytes()),
            "sha256": hashlib.sha256(
                (SOURCE_ROOT / relative).read_bytes()
            ).hexdigest(),
        }
        for relative, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v100() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v99())
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        required_target_families=REQUIRED_TARGET_FAMILIES,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.sequence_wide_agreement_shielded_preregistration.v100",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v99_failed_campaign_id": V99_CAMPAIGN_ID,
            "v99_failed_campaign_sha256": V99_CAMPAIGN_SHA256,
            "v99_failure_verification_id": V99_VERIFICATION_ID,
            "v99_failure_verification_sha256": V99_VERIFICATION_SHA256,
            "v99_registered_gate_passed": False,
            "v99_failure_retained_without_correction": True,
            "post_dependency_source_library_artifact_id": SOURCE_LIBRARY_ARTIFACT_ID,
            "post_dependency_source_library_sha256": SOURCE_LIBRARY_SHA256,
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v62_residual_library_sha256": V62_LIBRARY_SHA256,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v100_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V100),
            "frozen_before_any_registered_v100_target_outcome": True,
        },
        "identity_contract": {
            "source_structure_family": "COUPLED_EXCHANGE",
            "target_occurrences": campaign_config_v100()["target_occurrences"],
            "target_seeds_unique": len(
                {seed for _family, seed in TARGET_OCCURRENCES}
            )
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "target_episode_indices_unique": len(set(TARGET_EPISODE_INDICES))
            == len(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "frozen_v99_algorithm_reused_without_change": True,
            "only_changed_variable": "REGISTERED_SHIELD_PATH_COVERAGE_WINDOW",
            "v99_path_coverage_window": "FIRST_EPISODE",
            "v100_path_coverage_window": "COMPLETE_PERSISTENT_SEQUENCE",
            "accept_and_disagreement_each_required_at_least_once_in_window": True,
            "same_partial_rows_outcomes_synthesizer_stopping_rule_and_shield_between_arms": True,
            "target_columns_drivers_thresholds_and_leaf_values_rederived_from_target_rows": True,
            "abstract_proposal_can_precede_partial_only_on_exact_action_agreement": True,
            "persistent_exact_overlay_exclusively_discharges_safety": True,
            "incompatible_schema_control_receives_no_prior_and_no_target_outcome_query": True,
            "every_new_ground_query_must_follow_failed_certificate": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "both_required_target_families_must_pass": True,
            "every_target_must_activate_strictly_before_no_prior": True,
            "every_target_must_exercise_agreement_and_disagreement_across_complete_sequence": True,
            "every_target_must_use_persistent_agreement_shielded_abstract_planning": True,
            "each_target_family_must_expose_post_dependency_candidate": True,
            "aggregate_meta_task_labels_must_not_exceed_no_prior": True,
            "aggregate_meta_task_labels_must_be_strictly_below_cold_direct": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_joint_support_branch_evaluations": campaign_config_v100()[
                "maximum_joint_support_branch_evaluations"
            ],
            "joint_support_feasible_beam_width": campaign_config_v100()[
                "joint_support_feasible_beam_width"
            ],
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "activation_labels_use_right_censoring": True,
            "meta_no_prior_and_direct_target_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_shield_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v100_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "sequence_wide_path_coverage_verified": False,
            "cross_family_activation_sample_tax_advantage_verified": False,
            "agreement_shield_negative_transfer_control_verified": False,
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
        "preregistration_id": domains.extension_content_id_v100(
            domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_PREREGISTRATION_V100_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SequenceWideAgreementShieldedPreregistrationV100:
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
            or domains.extension_content_id_v100(
                domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_PREREGISTRATION_V100_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V100 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: SequenceWideAgreementShieldedPreregistrationV100 | None = None


def freeze_sequence_wide_agreement_shielded_preregistration_v100(
) -> SequenceWideAgreementShieldedPreregistrationV100:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V100 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V100 frozen preregistration changed")
        _CACHE = SequenceWideAgreementShieldedPreregistrationV100(
            _ISSUER, raw, identity
        )
    return _CACHE


def verify_sequence_wide_agreement_shielded_preregistration_v100(
    value: Any,
) -> SequenceWideAgreementShieldedPreregistrationV100:
    if type(value) is not SequenceWideAgreementShieldedPreregistrationV100:
        _fail("V100 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_sequence_wide_agreement_shielded_preregistration_v100()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V100 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v100",
    "freeze_sequence_wide_agreement_shielded_preregistration_v100",
    "verify_sequence_wide_agreement_shielded_preregistration_v100",
)

"""Outcome-free preregistration of V159 modular factorization source labels."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v159 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "8affc432e2965583857ee32744aa620015b602e8",
    "3a7737413de8e57fed88452ad79f6dc74d0f6785",
)
SOURCE_CALIBRATION_SEEDS = (1_048_101, 1_048_102, 1_048_103, 1_048_104)
SOURCE_PREREGISTRATION_ID = "1557a40366dc59e928e265891599fa23299f3384c6eeffab79c47f488c46f295"
EXPECTED_CANONICAL_BYTE_COUNT = 2_287
EXPECTED_CANONICAL_SHA256 = "2abfd32124b8106138fbff8805394d11bb0f882b3a4e603adcc0ad760d7269f1"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v159.py",
        1_685,
        "fafefd3b1fde45a396bd02a4690d50f7091f9dab28f6af0d9ac7f4d445f8e42c",
    ),
    (
        "src/acfqp/joint_factor_query_classifier_core_v159.py",
        7_626,
        "55e76289310caadb5e04ad40cc7a046dc36c8cc4cede01338384300b3b46487b",
    ),
    (
        "src/acfqp/construction_k7_joint_factor_query_classifier_receipt_v159.py",
        7_152,
        "3dc28671a231312b2c1df541ea67e14d10580c38cca38db5f652941c67a720fa",
    ),
)


class ConstructionK7JointFactorQuerySourcePreregistrationV159Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7JointFactorQuerySourcePreregistrationV159Error(message)


def _document():
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V159 source implementation changed before calibration")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    payload = {
        "schema": "acfqp.joint_factor_query_source_preregistration.v159",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "source_calibration_family": "STOCHASTIC_MODULAR_ROUTING_HELD_OUT",
        "source_calibration_seeds": list(SOURCE_CALIBRATION_SEEDS),
        "required_source_observation_count": len(SOURCE_CALIBRATION_SEEDS),
        "finite_typed_classifier_grammar": {
            "aggregate": "COUNT_CONJUNCTIVE_PAIR_PREDICATE_GREATER_THAN",
            "initial_support_comparators": ["EQUAL", "AT_LEAST"],
            "initial_support_values": {"minimum": 1, "maximum": 16},
            "catalogue_support_comparators": ["EQUAL", "AT_LEAST"],
            "catalogue_support_values": {"minimum": 1, "maximum": 16},
            "count_thresholds": {"minimum": 0, "maximum": 8},
        },
        "registered_source_gate": {
            "all_source_identities_fixed_before_source_outcomes": True,
            "raw_initial_state_action_successor_differences_required": True,
            "factorization_relation_label_derived_without_generation_witness": True,
            "modular_source_expected_to_supply_negative_factorization_labels": True,
            "classifier_exact_mdl_then_canonical_tie_break_required": True,
            "offline_source_labels_counted_separately_from_target_labels": True,
            "fresh_v159_target_identities_not_yet_registered_or_observed": True,
        },
        "claim_boundary": {
            "source_outcomes_accessed": False,
            "fresh_v159_target_outcomes_accessed": False,
            "classifier_receipt_issued": False,
            "query_policy_is_model_planning_or_certificate_authority": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "source_preregistration_id": domains.extension_content_id_v159(
            domains.CONSTRUCTION_K7_SOURCE_PREREGISTRATION_V159_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class JointFactorQuerySourcePreregistrationV159:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    source_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_joint_factor_query_source_preregistration_v159():
    document = _document()
    raw = canonical_json_bytes(document)
    if SOURCE_PREREGISTRATION_ID != "0" * 64 and not (
        document["source_preregistration_id"] == SOURCE_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V159 frozen source preregistration changed")
    return JointFactorQuerySourcePreregistrationV159(
        _ISSUER, raw, document["source_preregistration_id"]
    )


__all__ = (
    "SOURCE_PREREGISTRATION_ID",
    "freeze_joint_factor_query_source_preregistration_v159",
)

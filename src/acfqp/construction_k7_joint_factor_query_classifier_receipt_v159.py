"""Producer for the preregistered V159 joint factor/query receipt."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v159 as domains
from acfqp import construction_k7_joint_factor_query_source_preregistration_v159 as source_pre
from acfqp.generic_modular_routing_adapter_v128 import (
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.joint_factor_query_classifier_core_v159 import (
    build_initial_factorization_source_observation_v159,
    synthesize_joint_factor_query_classifier_v159,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V157_CAMPAIGN_ID = "51810176bf2ab9d4e51f11cf8a4f73b04bfb76bef116b8ebfce9d08f3fe1ed79"
V157_CAMPAIGN_BYTE_COUNT = 13_671_890
V157_CAMPAIGN_SHA256 = "8674649d85d991d8625d43104cd4a5e07fa75ccd4ffb88236e767cba11ea5284"
V157_VERIFICATION_ID = "61332d6b56b476d960915b182eff944c0a5e67a6dcf8b4782d798b0e46a6d59d"
V157_VERIFICATION_BYTE_COUNT = 17_545
V157_VERIFICATION_SHA256 = "fae743f81b19b45e85c5a96a1ffcf2bcbeee405e8a4651aa937169c635bcb9d4"
CLASSIFIER_RECEIPT_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"


class ConstructionK7JointFactorQueryClassifierReceiptV159Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7JointFactorQueryClassifierReceiptV159Error(message)


def _source_signatures(campaign):
    rows = []
    for occurrence in campaign["target_occurrences"]:
        acquisition = occurrence["anonymous_relational_factor_prior_acquisition"]
        signature = tuple(
            tuple(pair)
            for pair in acquisition["anonymous_initial_action_support_signature"]
        )
        rows.append((signature, acquisition["guard_decision"] == "RELATION_COVERAGE"))
    return tuple(sorted(set(rows)))


def _document(source_preregistration_raw, v157_campaign_raw, v157_verification_raw):
    source_registration = loads_canonical_json(source_preregistration_raw)
    campaign = loads_canonical_json(v157_campaign_raw)
    verification = loads_canonical_json(v157_verification_raw)
    if not (
        canonical_json_bytes(source_registration) == source_preregistration_raw
        and source_registration.get("source_preregistration_id")
        == source_pre.SOURCE_PREREGISTRATION_ID
        and len(source_preregistration_raw) == source_pre.EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(source_preregistration_raw).hexdigest()
        == source_pre.EXPECTED_CANONICAL_SHA256
        and canonical_json_bytes(campaign) == v157_campaign_raw
        and campaign.get("campaign_id") == V157_CAMPAIGN_ID
        and len(v157_campaign_raw) == V157_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v157_campaign_raw).hexdigest() == V157_CAMPAIGN_SHA256
        and canonical_json_bytes(verification) == v157_verification_raw
        and verification.get("verification_id") == V157_VERIFICATION_ID
        and len(v157_verification_raw) == V157_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(v157_verification_raw).hexdigest()
        == V157_VERIFICATION_SHA256
        and verification.get(
            "registered_plan_mode_corrected_margin_evidence_independently_verified"
        )
        is True
    ):
        _fail("V159 frozen source evidence changed")
    config = modular_routing_config_v128()
    observations = tuple(
        build_initial_factorization_source_observation_v159(
            build_modular_routing_adapter_v128(seed, config)
        )
        for seed in source_registration["source_calibration_seeds"]
    )
    labelled = list(_source_signatures(campaign))
    labelled.extend(
        (
            tuple(
                tuple(pair)
                for pair in observation[
                    "anonymous_initial_action_support_signature"
                ]
            ),
            observation["positive_factorization_relation_present"],
        )
        for observation in observations
    )
    expression, mdl, evaluated, separating = (
        synthesize_joint_factor_query_classifier_v159(labelled)
    )
    payload = {
        "schema": "acfqp.joint_factor_query_classifier_receipt.v159",
        "source_preregistration_id": source_pre.SOURCE_PREREGISTRATION_ID,
        "source_v157_campaign_id": V157_CAMPAIGN_ID,
        "source_v157_verification_id": V157_VERIFICATION_ID,
        "source_modular_factorization_observations": list(observations),
        "finite_typed_classifier_grammar": source_registration[
            "finite_typed_classifier_grammar"
        ],
        "selected_expression": expression,
        "selected_expression_mdl_key": mdl,
        "candidate_expression_count_evaluated": evaluated,
        "separating_expression_count": separating,
        "exact_mdl_then_canonical_tie_break": True,
        "source_labels_derived_from_raw_factorization_or_frozen_predecessor_evidence": True,
        "offline_source_observation_labels": sum(
            row["offline_source_observation_labels"] for row in observations
        ),
        "fresh_v159_target_labels": 0,
        "fresh_v159_target_outcomes_accessed": False,
        "query_policy_classifier_is_meta_prior_only": True,
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "sample_labels_and_classifier_derivation_compute_separate": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "classifier_receipt_id": domains.extension_content_id_v159(
            domains.CONSTRUCTION_K7_CLASSIFIER_RECEIPT_V159_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class JointFactorQueryClassifierReceiptV159:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    classifier_receipt_id: str

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_joint_factor_query_classifier_receipt_v159(
    source_preregistration_raw: bytes,
    v157_campaign_raw: bytes,
    v157_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CLASSIFIER_RECEIPT_ID != "0" * 64:
        _fail("frozen V159 source attempt is terminal and will not be rerun")
    document = _document(
        source_preregistration_raw, v157_campaign_raw, v157_verification_raw
    )
    raw = canonical_json_bytes(document)
    _CACHE = JointFactorQueryClassifierReceiptV159(
        _ISSUER, raw, document["classifier_receipt_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CLASSIFIER_RECEIPT_ID",
    "run_joint_factor_query_classifier_receipt_v159",
)

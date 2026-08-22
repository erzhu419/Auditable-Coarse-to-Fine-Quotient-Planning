"""Producer-free verification of the frozen V164 replication."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v163 as domains_v163
from acfqp import construction_k7_domain_registry_extension_v164 as domains
from acfqp import construction_k7_plan_mode_margin_independent_verifier_v157 as v157
from acfqp import construction_k7_safe_paid_path_sample_tax_independent_verifier_v163 as previous
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "108bc4cf4f61123c6da7812ae76a48c21027a3b5e32e80005952a93b2ab8da1c"
CAMPAIGN_BYTE_COUNT = 33_323_896
CAMPAIGN_SHA256 = "d964f250d8d6e0587cb80a1df50515ae9b74c319b0a4f5f24aee3cae262aa9f5"
PREREGISTRATION_ID = (
    "c4b822f5b57280eb63cd0affd15f0f38b7c74d52342f0270e282de3cced94424"
)
PREREGISTRATION_BYTE_COUNT = 3_944
PREREGISTRATION_SHA256 = (
    "267e0ff7ba31d780f21915d2df29f19f55910c74cf0c3263ea3196e363ee7d95"
)
V163_CAMPAIGN_ID = previous.CAMPAIGN_ID
V163_CAMPAIGN_BYTE_COUNT = previous.CAMPAIGN_BYTE_COUNT
V163_CAMPAIGN_SHA256 = previous.CAMPAIGN_SHA256
V163_VERIFICATION_ID = previous.VERIFICATION_ID
V163_VERIFICATION_BYTE_COUNT = previous.EXPECTED_CANONICAL_BYTE_COUNT
V163_VERIFICATION_SHA256 = previous.EXPECTED_CANONICAL_SHA256
EXPECTED_OCCURRENCES = (
    *((previous.POSITIVE_FAMILY, seed) for seed in range(1_048_601, 1_048_609)),
    *((previous.FALLBACK_FAMILY, seed) for seed in range(1_048_611, 1_048_613)),
    *((previous.MODULAR_FAMILY, seed) for seed in range(1_048_621, 1_048_623)),
)
EXPECTED_EPISODES = (921, 922, 923, 924)
VERIFICATION_ID = (
    "1095eec978a045ac3fec2ef0848927ecf7ce3d290d68415656b28fe34b3f298f"
)
EXPECTED_CANONICAL_BYTE_COUNT = 41_990
EXPECTED_CANONICAL_SHA256 = (
    "91c6939851c37de8094be13bf113a17aef51abfc8379853af1f509559ea03be8"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
_V164_ADDITIONS = {
    "source_v163_occurrence_id",
    "frozen_v163_campaign_id",
    "frozen_v163_verification_id",
}


class ConstructionK7SampleTaxReplicationIndependentVerifierV164Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SampleTaxReplicationIndependentVerifierV164Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    _require(
        document.get(key)
        == _content_id(
            domain, {name: value for name, value in document.items() if name != key}
        ),
        f"V164 {key} changed",
    )


def _frozen(raw, document, *, count, digest, key, identity, label):
    _require(
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(key) == identity,
        f"V164 frozen {label} changed",
    )


def _sequence_verifier(family):
    globals_v150 = dict(v157.__dict__)
    globals_v150.update(
        EXPECTED_EPISODES=EXPECTED_EPISODES,
        _fail=_fail,
        _require=_require,
    )
    factory = FunctionType(
        v157._v150_sequence_verifier.__code__,  # noqa: SLF001
        globals_v150,
        name=v157._v150_sequence_verifier.__name__,  # noqa: SLF001
    )
    return factory(family)


def _verify_sequence(sequence, candidate, rows, *, family, seed):
    globals_v157 = dict(v157.__dict__)
    globals_v157.update(
        _v150_sequence_verifier=_sequence_verifier,
        _fail=_fail,
        _require=_require,
    )
    verifier = FunctionType(
        v157._verify_sequence.__code__,  # noqa: SLF001
        globals_v157,
        name=v157._verify_sequence.__name__,  # noqa: SLF001
    )
    return verifier(sequence, candidate, rows, family=family, seed=seed)


def _normalized_acquisition(recorded, prepared, classifier):
    """Normalize producer/verifier-local failure class names without hiding semantics."""

    normalized = previous._normalized_acquisition(  # noqa: SLF001
        recorded, prepared, classifier
    )
    history = copy.deepcopy(normalized["stopping_history"])
    producer_error = "AnonymousRelationalTemplateInstantiatorV147Error"
    verifier_error = (
        "ConstructionK7AnonymousRelationalFactorBankIndependentVerifierV148Error"
    )
    expected_errors = {
        producer_error,
        "GenericAtomicExpressionWorldModelV4Error",
        "GenericLayoutFactorizedWorldModelV5Error",
        "GenericRelationalFactorExecutionProjectionV144Error",
    }
    for update in history:
        if update.get("candidate_available") is False:
            _require(
                update.get("constructor_error_type") in expected_errors,
                "V164 unavailable-candidate failure class changed",
            )
            if update["constructor_error_type"] == producer_error:
                update["constructor_error_type"] = verifier_error
    normalized["stopping_history"] = history
    payload = {
        key: value for key, value in normalized.items() if key != "acquisition_id"
    }
    normalized["acquisition_id"] = _content_id(
        previous.v151.previous.base.domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_ACQUISITION_V148_DOMAIN,  # noqa: E501
        payload,
    )
    return normalized


_PREVIOUS_GLOBALS = dict(previous.__dict__)
_PREVIOUS_GLOBALS.update(
    EXPECTED_OCCURRENCES=EXPECTED_OCCURRENCES,
    EXPECTED_EPISODES=EXPECTED_EPISODES,
    _normalized_acquisition=_normalized_acquisition,
    _verify_sequence=_verify_sequence,
    _fail=_fail,
    _require=_require,
)
_VERIFY_PREVIOUS_OCCURRENCE = FunctionType(
    previous._verify_occurrence.__code__,  # noqa: SLF001
    _PREVIOUS_GLOBALS,
    name="_verify_v163_normalized_occurrence_for_v164",
)


def _verify_occurrence(args):
    row, bank, bank_raw, bank_verification_raw, classifier = args
    _require(
        (row.get("target_family"), row.get("seed")) in EXPECTED_OCCURRENCES
        and row.get("schema") == "acfqp.sample_tax_replication_occurrence.v164"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES
        and row.get("frozen_v163_campaign_id") == V163_CAMPAIGN_ID
        and row.get("frozen_v163_verification_id") == V163_VERIFICATION_ID,
        "V164 occurrence wrapper identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V164_DOMAIN)
    normalized = {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if key not in _V164_ADDITIONS and key != "occurrence_id"
    }
    normalized["schema"] = "acfqp.safe_paid_path_sample_tax_occurrence.v163"
    normalized["occurrence_id"] = row["source_v163_occurrence_id"]
    _verify_id(
        normalized,
        "occurrence_id",
        domains_v163.CONSTRUCTION_K7_OCCURRENCE_V163_DOMAIN,
    )
    verified = _VERIFY_PREVIOUS_OCCURRENCE(
        (normalized, bank, bank_raw, bank_verification_raw, classifier)
    )
    return {
        **verified,
        "occurrence_id": row["occurrence_id"],
        "source_v163_occurrence_id": normalized["occurrence_id"],
    }


def freeze_sample_tax_replication_verification_v164(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v162_failure_raw: bytes,
    v163_campaign_raw: bytes,
    v163_verification_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    classifier = loads_canonical_json(classifier_receipt_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    v163_campaign = loads_canonical_json(v163_campaign_raw)
    v163_verification = loads_canonical_json(v163_verification_raw)
    _frozen(
        campaign_raw,
        campaign,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        key="campaign_id",
        identity=CAMPAIGN_ID,
        label="campaign",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V164_DOMAIN)
    _frozen(
        preregistration_raw,
        registration,
        count=PREREGISTRATION_BYTE_COUNT,
        digest=PREREGISTRATION_SHA256,
        key="preregistration_id",
        identity=PREREGISTRATION_ID,
        label="preregistration",
    )
    _verify_id(
        registration,
        "preregistration_id",
        domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V164_DOMAIN,
    )
    _frozen(
        v163_campaign_raw,
        v163_campaign,
        count=V163_CAMPAIGN_BYTE_COUNT,
        digest=V163_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V163_CAMPAIGN_ID,
        label="V163 campaign",
    )
    _frozen(
        v163_verification_raw,
        v163_verification,
        count=V163_VERIFICATION_BYTE_COUNT,
        digest=V163_VERIFICATION_SHA256,
        key="verification_id",
        identity=V163_VERIFICATION_ID,
        label="V163 verification",
    )
    _require(
        v163_campaign["registered_gate"]["passed"] is True
        and v163_verification[
            "safe_query_and_factor_prior_sample_tax_evidence_independently_verified"
        ]
        is True
        and registration["frozen_v163_campaign"]["campaign_id"]
        == V163_CAMPAIGN_ID
        and registration["frozen_v163_independent_verification"]["verification_id"]
        == V163_VERIFICATION_ID,
        "V164 predecessor binding changed",
    )
    previous._frozen(  # noqa: SLF001
        classifier_receipt_raw,
        classifier,
        count=previous.CLASSIFIER_BYTE_COUNT,
        digest=previous.CLASSIFIER_SHA256,
        key="classifier_receipt_id",
        identity=previous.CLASSIFIER_RECEIPT_ID,
        label="classifier receipt",
    )
    _require(
        classifier["fresh_v161_target_outcomes_accessed"] is False
        and classifier["fresh_v161_target_labels"] == 0
        and classifier["offline_source_observation_labels"] == 96
        and classifier[
            "query_policy_classifier_is_model_planning_or_certificate_authority"
        ]
        is False,
        "V164 classifier claim boundary changed",
    )
    _require(
        canonical_json_bytes(bank) == bank_raw
        and bank.get("bank_id") == previous.v151.BANK_ID
        and len(bank_raw) == previous.v151.previous.base.BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest()
        == previous.v151.previous.base.BANK_SHA256,
        "V164 frozen factor bank changed",
    )
    _require(
        canonical_json_bytes(bank_verification) == bank_verification_raw
        and bank_verification.get("verification_id")
        == previous.v151.BANK_VERIFICATION_ID
        and len(bank_verification_raw)
        == previous.v151.previous.base.BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest()
        == previous.v151.previous.base.BANK_VERIFICATION_SHA256,
        "V164 frozen factor-bank verification changed",
    )
    failure = loads_canonical_json(v162_failure_raw)
    _require(
        canonical_json_bytes(failure) == v162_failure_raw
        and len(v162_failure_raw) == previous.V162_FAILURE_BYTE_COUNT
        and hashlib.sha256(v162_failure_raw).hexdigest()
        == previous.V162_FAILURE_SHA256
        and failure["failed_campaign_id"] == previous.V162_FAILED_CAMPAIGN_ID
        and failure["failed_result_not_reclassified_as_success"] is True
        and failure["same_identity_rerun_forbidden"] is True,
        "V164 V162 failure predecessor changed",
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(
            len(raw) == fact["byte_count"]
            and hashlib.sha256(raw).hexdigest() == fact["sha256"],
            "V164 source closure changed",
        )
    _require(
        registration["target_occurrences"]
        == [
            {"family": family, "seed": seed}
            for family, seed in EXPECTED_OCCURRENCES
        ]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["required_target_occurrence_count"] == 12
        and all(registration["registered_gate"].values())
        and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V164 preregistered contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(
            executor.map(
                _verify_occurrence,
                (
                    (
                        row,
                        bank,
                        bank_raw,
                        bank_verification_raw,
                        classifier,
                    )
                    for row in campaign["target_occurrences"]
                ),
            )
        )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V164 occurrence inventory changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    guards = tuple(row["query_policy_labels_avoided"] for row in rows)
    factors = tuple(row["factor_prior_labels_avoided"] for row in rows)
    accounting.update(
        offline_source_observation_labels=96,
        target_classifier_path_prefix_labels=sum(
            row["accounting"]["classifier_prefix_labels_included_in_acquisition"]
            for row in rows
        ),
        additional_classifier_only_target_labels=0,
        total_query_policy_labels_avoided_vs_exact_path_first=sum(guards),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(factors),
        source_and_target_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    certified_rows = [row for row in rows if row["certified_positive_switch"]]
    fallback_rows = [row for row in rows if not row["certified_positive_switch"]]
    gate = {
        "required_target_occurrence_count": 12,
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "all_three_registered_families_present": {
            row["family"] for row in rows
        }
        == {
            previous.POSITIVE_FAMILY,
            previous.FALLBACK_FAMILY,
            previous.MODULAR_FAMILY,
        },
        "at_least_one_certified_switch_exercised": bool(certified_rows),
        "query_policy_noninferior_everywhere": all(value >= 0 for value in guards),
        "query_policy_strictly_reduces_sample_tax_in_aggregate": sum(guards) > 0,
        "query_policy_positive_reduction_occurrence_present": any(
            value > 0 for value in guards
        ),
        "every_exact_fallback_is_zero_regression": all(
            row["query_policy_labels_avoided"] == 0
            and row["registered_gate"]["exact_fallback_has_zero_regression"]
            for row in fallback_rows
        ),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factors),
        "factor_prior_strictly_reduces_sample_tax_in_aggregate": sum(factors) > 0,
        "sample_tax_axes_remain_separate": accounting[
            "source_and_target_labels_execution_steps_derivation_and_planning_compute_separate"
        ],
        "no_additional_classifier_only_target_labels": accounting[
            "additional_classifier_only_target_labels"
        ]
        == 0,
        "both_arm_receding_plans_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "certificate_failure_local_recovery_exercised": sum(
            row["accounting"]["progressive_prior_certificate_local_labels"]
            + row["accounting"]["progressive_strict_certificate_local_labels"]
            for row in rows
        )
        > 0,
        "all_executed_actions_have_v109_receipts": all(
            row["registered_gate"]["all_executed_actions_have_v109_receipts"]
            for row in rows
        ),
        "strict_incompatible_schema_no_transfer_verified": incompatible_schema_no_transfer_control_v99()[
            "strict_ood_no_transfer"
        ],
        "v163_campaign_and_verification_bindings_preserved": all(
            row["source_v163_occurrence_id"]
            and row["registered_gate"]["v162_failed_identity_preserved"]
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == 12
        and gate["passed_target_occurrence_count"] == 12
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.sample_tax_replication_campaign.v164",
        "preregistration_id": PREREGISTRATION_ID,
        "frozen_v163_campaign_id": V163_CAMPAIGN_ID,
        "frozen_v163_verification_id": V163_VERIFICATION_ID,
        "target_occurrences": campaign["target_occurrences"],
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "query_and_factor_prior_sample_tax_reduction_replicated": gate["passed"],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V164_THREE_FAMILY_REPLICATION_COHORT",
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    expected_campaign = {
        **payload,
        "campaign_id": _content_id(
            domains.CONSTRUCTION_K7_CAMPAIGN_V164_DOMAIN, payload
        ),
    }
    _require(campaign == expected_campaign, "V164 aggregate campaign changed")
    verification_payload = {
        "schema": "acfqp.sample_tax_replication_verification.v164",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "frozen_v163_campaign_id": V163_CAMPAIGN_ID,
        "frozen_v163_verification_id": V163_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_v163_normalization_and_full_occurrence_reconstruction": True,
        "producer_free_query_factor_planning_certificate_and_v109_reconstruction": True,
        "query_and_factor_prior_sample_tax_replication_independently_verified": True,
        "query_policy_labels_avoided_vs_exact_path_first": sum(guards),
        "factor_prior_labels_avoided_within_same_query_policy": sum(factors),
        "sample_tax_claim_scope": campaign["sample_tax_claim_scope"],
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
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
        "verification_id": _content_id(
            domains.CONSTRUCTION_K7_VERIFICATION_V164_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V164 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_sample_tax_replication_verification_v164",
)

"""Outcome-free V58 registration for universal-mixture stopping."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as pre_v57
from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp.generic_universal_mixture_mdl_synthesizer_v13 import (
    universal_mixture_mdl_predictive_stop_update_v13,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.universal_mixture_three_domain_campaign_core_v58 import (
    build_universal_mixture_three_domain_campaign_document_v58,
)


SCHEMA_VERSION = "58.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.230"
PROFILE_KEY = "construction_k7_universal_mixture_three_domain_v58"
PREREGISTRATION_ID = "1eff338036ea7ef542c2447e87dee5588c85022cb53568f925484e3efb83fc68"
EXPECTED_CANONICAL_BYTE_COUNT = 10_527
EXPECTED_CANONICAL_SHA256 = "cf4656460c9a0872027e9cdc85df28c029979672fd1e8f52dd893dbcf8c5dbb1"
IMPLEMENTATION_COMMIT = "d72231f"

V57_CAMPAIGN_ID = (
    "744e764a35cb7ba4955852fa62c30978b7aac35d0761b7054cb64298be1fd92b"
)
V57_CAMPAIGN_SHA256 = (
    "3fc9f09eac87e1ea2180a1b6a5523694aed5c1dc41438a7484e6a9dc9f925588"
)
V57_VERIFICATION_ID = (
    "f38218a0a527dd4411bf1d105162f563eae1800d68bab6d9b821cb0e693d1469"
)
V57_VERIFICATION_SHA256 = (
    "fb79bcfc0e73a44254b9d9db32af0cc8d86293db84871026b59f80737ecbc86d"
)
FACTOR_LIBRARY = pre_v57.FACTOR_LIBRARY
FACTOR_LIBRARY_LABELS = pre_v57.FACTOR_LIBRARY_LABELS
V51_FACTOR_LIBRARY_ID = pre_v57.V51_FACTOR_LIBRARY_ID

BALANCED_TARGET_SEEDS = tuple(range(581_101, 581_133))
COUPLED_TARGET_SEEDS = tuple(range(582_101, 582_133))
MAINTENANCE_TARGET_SEEDS = tuple(range(583_101, 583_133))
DEVELOPMENT_SEEDS = (589_910, 589_911, 589_920, 589_921, 589_930, 589_931)
PLANNING_SEED_COUNT_PER_FAMILY = 4
WORKER_COUNT = 4
FACTOR_SIGNATURE_CREDIT_UNITS = 16
INVALIDATED_CANDIDATE_PENALTY_UNITS = 16
MINIMUM_REUSABLE_FACTOR_COUNT = 3
GLOBAL_ALPHA_DENOMINATOR = 20
PREDICTIVE_EVIDENCE_CREDIT_UNITS_PER_BIT = 2

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v58.py",
    "src/acfqp/generic_universal_mixture_mdl_synthesizer_v13.py",
    "src/acfqp/universal_mixture_three_domain_campaign_core_v58.py",
    *pre_v57.BOUND_SOURCE_PATHS,
)
SUCCESSOR_DOMAINS = {
    "preregistration": (
        domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_PREREGISTRATION_V58_DOMAIN
    ),
    "acquisition": (
        domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN
    ),
    "sample_tax": (
        domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_SAMPLE_TAX_V58_DOMAIN
    ),
    "campaign": domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_CAMPAIGN_V58_DOMAIN,
    "verification": (
        domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_VERIFICATION_V58_DOMAIN
    ),
}


class ConstructionK7UniversalMixturePreregistrationV58Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7UniversalMixturePreregistrationV58Error(message)


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


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v58() -> dict[str, Any]:
    config = pre_v57.campaign_config_v57()
    config["successor_domains"] = dict(SUCCESSOR_DOMAINS)
    config["families"]["BALANCED_BATCH_REFINEMENT"].update(
        target_seeds=BALANCED_TARGET_SEEDS,
        planning_seed_count=PLANNING_SEED_COUNT_PER_FAMILY,
        maximum_acquisition_labels=192,
    )
    config["families"]["COUPLED_EXCHANGE"].update(
        target_seeds=COUPLED_TARGET_SEEDS,
        planning_seed_count=PLANNING_SEED_COUNT_PER_FAMILY,
        maximum_acquisition_labels=224,
    )
    config["families"]["MAINTENANCE_CASCADE"].update(
        target_seeds=MAINTENANCE_TARGET_SEEDS,
        planning_seed_count=PLANNING_SEED_COUNT_PER_FAMILY,
        maximum_acquisition_labels=288,
    )
    config["worker_count"] = WORKER_COUNT
    config["factor_signature_credit_units"] = FACTOR_SIGNATURE_CREDIT_UNITS
    config["invalidated_candidate_penalty_units"] = (
        INVALIDATED_CANDIDATE_PENALTY_UNITS
    )
    config["minimum_reusable_factor_count"] = MINIMUM_REUSABLE_FACTOR_COUNT
    config["global_alpha_denominator"] = GLOBAL_ALPHA_DENOMINATOR
    config["predictive_evidence_credit_units_per_bit"] = (
        PREDICTIVE_EVIDENCE_CREDIT_UNITS_PER_BIT
    )
    config["v57_campaign_id"] = V57_CAMPAIGN_ID
    config["v57_verification_id"] = V57_VERIFICATION_ID
    config["require_lifetime_sample_tax_gate"] = True
    for stale in (
        "epoch_alpha_spending_base",
        "success_evalue_multiplier_numerator",
        "success_evalue_multiplier_denominator",
    ):
        config.pop(stale, None)
    return config


def _document() -> dict[str, Any]:
    registered = set(
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.universal_mixture_preregistration.v58",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v57_campaign_id": V57_CAMPAIGN_ID,
            "v57_campaign_sha256": V57_CAMPAIGN_SHA256,
            "v57_verification_id": V57_VERIFICATION_ID,
            "v57_verification_sha256": V57_VERIFICATION_SHA256,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
            "v51_factor_library_labels": FACTOR_LIBRARY_LABELS,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "successor_domains": dict(SUCCESSOR_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "stop_callable": _callable_fact(
                universal_mixture_mdl_predictive_stop_update_v13
            ),
            "campaign_builder_callable": _callable_fact(
                build_universal_mixture_three_domain_campaign_document_v58
            ),
            "frozen_before_any_v58_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": (
                set(DEVELOPMENT_SEEDS).isdisjoint(registered)
            ),
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {
                "target_seeds": list(BALANCED_TARGET_SEEDS),
                "maximum_acquisition_labels": 192,
            },
            "COUPLED_EXCHANGE": {
                "target_seeds": list(COUPLED_TARGET_SEEDS),
                "maximum_acquisition_labels": 224,
            },
            "MAINTENANCE_CASCADE": {
                "target_seeds": list(MAINTENANCE_TARGET_SEEDS),
                "maximum_acquisition_labels": 288,
            },
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
        },
        "universal_mixture_stopping_contract": {
            "candidate_frozen_before_each_scored_future_batch": True,
            "candidate_synthesis_attempted_after_every_support_query": True,
            "fixed_minimum_candidate_label_floor": None,
            "fixed_confirmation_block_size": None,
            "fixed_confidence_reserve": None,
            "reachable_frontier_exhaustion_stop_available": False,
            "predictive_null_success_probability_upper_bound": {
                "numerator": 1,
                "denominator": 2,
            },
            "alternative_success_probability_mixture": (
                "UNIFORM_OPEN_HALF_TO_ONE"
            ),
            "global_alpha": {"numerator": 1, "denominator": 20},
            "candidate_epoch_weight": "1/((j+1)*(j+2))",
            "betting_fraction_selected": False,
            "success_evalue_multiplier_selected": False,
            "epoch_spending_base_selected": False,
            "predictive_evidence_to_mdl_credit_units_per_bit": 2,
            "predictive_evidence_to_mdl_credit_inherited_from_v57": True,
            "anytime_valid_for_registered_predictive_null": True,
            "distribution_free_global_dynamics_confidence_claimed": False,
        },
        "matched_single_switch_arms": {
            "arms": ["ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"],
            "same_synthesizer_query_order_mdl_and_eprocess": True,
            "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
            "factor_prior_on_code_credit_per_reusable_signature": 16,
            "factor_prior_off_code_credit": 0,
        },
        "planning_and_recovery": {
            "planning_seed_count_per_family": PLANNING_SEED_COUNT_PER_FAMILY,
            "receding_abstract_planning": True,
            "matched_direct_baseline_same_ground_kernel_and_objective": True,
            "certificate_failure_before_every_local_ground_query": True,
            "counterexample_triggers_local_program_resynthesis": True,
        },
        "sample_tax_contract": {
            "registered_occurrence_count": len(registered),
            "factor_library_labels_charged_only_to_prior_on": (
                FACTOR_LIBRARY_LABELS
            ),
            "positive_incremental_reduction_required_in_each_family": True,
            "positive_online_and_lifetime_label_reduction_required": True,
            "all_accounting_axes_separate": True,
            "official_break_even_claimed": False,
        },
        "development_only": {
            "development_seeds": list(DEVELOPMENT_SEEDS),
            "factor_prior_on_acquisition_labels": 496,
            "strict_no_prior_acquisition_labels": 558,
            "incremental_reduction": 62,
            "factor_library_tax": FACTOR_LIBRARY_LABELS,
            "lifetime_reduction": -308,
            "lifetime_gate_enforced": False,
            "all_three_family_reductions_positive": True,
            "development_outcomes_not_registered_evidence": True,
        },
        "claim_boundary": {
            "v58_campaign_preregistered": True,
            "registered_outcome_observed": False,
            "predictive_evidence_to_mdl_credit_removed": False,
            "next_required_scaffold_removal": (
                "REPLACE_HEURISTIC_MDL_UNITS_WITH_TRUE_BIT_CODELENGTH"
            ),
            "arbitrary_domain_transfer_claimed": False,
            "global_exact_dynamics_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "factor_library": FACTOR_LIBRARY,
        "future_content_domains": dict(SUCCESSOR_DOMAINS),
        "fresh_v58_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains_v58.extension_content_id_v58(
            SUCCESSOR_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class UniversalMixturePreregistrationV58:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V58 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains_v58.extension_content_id_v58(
                SUCCESSOR_DOMAINS["preregistration"], payload
            )
            != self.preregistration_id
        ):
            _fail("V58 preregistration bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: UniversalMixturePreregistrationV58 | None = None


def freeze_universal_mixture_preregistration_v58(
) -> UniversalMixturePreregistrationV58:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V58 preregistration changed")
    if _CACHE is None:
        _CACHE = UniversalMixturePreregistrationV58(_ISSUER, raw, identity)
    return _CACHE


def verify_universal_mixture_preregistration_v58(
    value: Any,
) -> UniversalMixturePreregistrationV58:
    if type(value) is not UniversalMixturePreregistrationV58:
        _fail("V58 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_universal_mixture_preregistration_v58()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V58 preregistration does not match frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "FACTOR_LIBRARY",
    "SUCCESSOR_DOMAINS",
    "UniversalMixturePreregistrationV58",
    "campaign_config_v58",
    "freeze_universal_mixture_preregistration_v58",
    "verify_universal_mixture_preregistration_v58",
)

"""Producer-free verification of V152 changed-cardinality transfer."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import FunctionType, SimpleNamespace
import copy
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v152 as domains
from acfqp import construction_k7_relation_keyed_bank_independent_verifier_v151 as v151
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import incompatible_schema_no_transfer_control_v99
from acfqp.generic_ternary_relation_workflow_adapter_v152 import FAMILY, build_ternary_relation_workflow_adapter_v152, ternary_relation_workflow_config_v152
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "043437af4d99d554275eaf1f13a5691b1f46a332081b5a1cbe3b75f0e0586783"
CAMPAIGN_BYTE_COUNT = 30_756_918
CAMPAIGN_SHA256 = "d77f1be15500ac909f81a0b782443a659970b625f534e3c3f0acd460c936091a"
PREREGISTRATION_ID = "f5a86041bd92099f03bd87618238e4e1a5345c950e4c0ea221d8f7977a4f60ad"
PREREGISTRATION_BYTE_COUNT = 3_479
PREREGISTRATION_SHA256 = "1910e0c4da868166c7fac2d63717ffc537d9c19ada61d9a5c3e2343ef703c5a2"
V151_CAMPAIGN_ID = v151.CAMPAIGN_ID
V151_CAMPAIGN_BYTE_COUNT = v151.CAMPAIGN_BYTE_COUNT
V151_CAMPAIGN_SHA256 = v151.CAMPAIGN_SHA256
V151_VERIFICATION_ID = v151.VERIFICATION_ID
V151_VERIFICATION_BYTE_COUNT = v151.EXPECTED_CANONICAL_BYTE_COUNT
V151_VERIFICATION_SHA256 = v151.EXPECTED_CANONICAL_SHA256
BANK_ID = v151.BANK_ID
BANK_VERIFICATION_ID = v151.BANK_VERIFICATION_ID
EXPECTED_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_391, 1_047_397))
EXPECTED_EPISODES = (621, 622, 623, 624)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
SOURCE_ROOT = Path(__file__).resolve().parents[2]


class ConstructionK7TernaryRelationalTransferIndependentVerifierV152Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TernaryRelationalTransferIndependentVerifierV152Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V152 {key} changed")


def _campaign_config():
    config = ternary_relation_workflow_config_v152()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_536
    return config


_MODEL_PROXY = SimpleNamespace(**v151.previous.base.previous.base.model.__dict__)
_MODEL_PROXY._project = v151._project_allow_nonaccepting_novel_delta
_ROBUST_BASE_PROXY = SimpleNamespace(**v151.previous.base.previous.base.__dict__)
_ROBUST_BASE_PROXY.model = _MODEL_PROXY
_V145_PROXY = SimpleNamespace(**v151.previous.base.previous.__dict__)
_V145_PROXY.base = _ROBUST_BASE_PROXY
_BASE_SEQUENCE_GLOBALS = dict(v151.previous.base.__dict__)
_BASE_SEQUENCE_GLOBALS.update(EXPECTED_EPISODES=EXPECTED_EPISODES, FAMILY=FAMILY, previous=_V145_PROXY, _fail=_fail, _require=_require)
_BASE_VERIFY_SEQUENCE = FunctionType(v151.previous.base._verify_sequence.__code__, _BASE_SEQUENCE_GLOBALS, name=v151.previous.base._verify_sequence.__name__)
_SEQUENCE_GLOBALS = dict(v151.__dict__)
_SEQUENCE_GLOBALS.update(EXPECTED_EPISODES=EXPECTED_EPISODES, _BASE_VERIFY_SEQUENCE=_BASE_VERIFY_SEQUENCE, _fail=_fail, _require=_require)
_VERIFY_SEQUENCE = FunctionType(v151._verify_sequence.__code__, _SEQUENCE_GLOBALS, name=v151._verify_sequence.__name__)


_OCCURRENCE_GLOBALS = dict(v151.__dict__)
_OCCURRENCE_GLOBALS.update(
    EXPECTED_OCCURRENCES=EXPECTED_OCCURRENCES,
    EXPECTED_EPISODES=EXPECTED_EPISODES,
    build_relation_keyed_workflow_adapter_v151=build_ternary_relation_workflow_adapter_v152,
    _campaign_config=_campaign_config,
    _verify_sequence=_VERIFY_SEQUENCE,
    _fail=_fail,
    _require=_require,
)
_VERIFY_NORMALIZED_OCCURRENCE = FunctionType(v151._verify_occurrence.__code__, _OCCURRENCE_GLOBALS, name=v151._verify_occurrence.__name__)


def _verify_occurrence(args):
    row, bank = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row.get("schema") == "acfqp.ternary_relational_transfer_occurrence.v152"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES,
        "V152 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V152_DOMAIN)
    original_gate = row["registered_gate"]
    normalized_gate = {key: copy.deepcopy(value) for key, value in original_gate.items() if key != "three_key_relation_instantiated_from_two_key_source_template"}
    normalized = {
        **{key: copy.deepcopy(value) for key, value in row.items() if key != "occurrence_id"},
        "schema": "acfqp.relation_keyed_relational_bank_occurrence.v151",
        "registered_gate": normalized_gate,
        "relation_binding_derived_from_raw_transition_deltas": row["relation_binding_derived_from_target_raw_transition_deltas"],
        "relational_template_selection_itself_observed": original_gate["relational_artifact_selected_in_prior_arm"],
        "v150_cross_domain_campaign_preserved": True,
    }
    normalized["occurrence_id"] = v151.domains.extension_content_id_v151(v151.domains.CONSTRUCTION_K7_OCCURRENCE_V151_DOMAIN, {key: value for key, value in normalized.items() if key != "occurrence_id"})
    verified = _VERIFY_NORMALIZED_OCCURRENCE((normalized, bank))
    _require(
        original_gate == {**normalized_gate, "three_key_relation_instantiated_from_two_key_source_template": True}
        and row["source_relation_key_cardinality"] == 2
        and row["target_relation_key_cardinality"] == 3
        and row["relation_cardinality_supplied_by_prior"] is False
        and row["relation_binding_derived_from_target_raw_transition_deltas"] is True
        and row["direct_numeric_increment_field_present"] is False
        and row["v151_campaign_and_verification_preserved"] is True,
        "V152 changed-cardinality evidence changed",
    )
    return {**verified, "occurrence_id": row["occurrence_id"], "source_relation_key_cardinality": 2, "target_relation_key_cardinality": 3}


def freeze_ternary_relational_transfer_verification_v152(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    v151_campaign_raw: bytes,
    v151_verification_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    predecessor = loads_canonical_json(v151_campaign_raw)
    predecessor_verification = loads_canonical_json(v151_verification_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    _require(canonical_json_bytes(campaign) == campaign_raw and len(campaign_raw) == CAMPAIGN_BYTE_COUNT and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256 and campaign.get("campaign_id") == CAMPAIGN_ID, "V152 campaign identity changed")
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V152_DOMAIN)
    _require(canonical_json_bytes(registration) == preregistration_raw and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT and hashlib.sha256(preregistration_raw).hexdigest() == PREREGISTRATION_SHA256 and registration.get("preregistration_id") == PREREGISTRATION_ID, "V152 preregistration identity changed")
    _verify_id(registration, "preregistration_id", domains.CONSTRUCTION_K7_PREREGISTRATION_V152_DOMAIN)
    _require(
        canonical_json_bytes(predecessor) == v151_campaign_raw and len(v151_campaign_raw) == V151_CAMPAIGN_BYTE_COUNT and hashlib.sha256(v151_campaign_raw).hexdigest() == V151_CAMPAIGN_SHA256 and predecessor.get("campaign_id") == V151_CAMPAIGN_ID
        and canonical_json_bytes(predecessor_verification) == v151_verification_raw and len(v151_verification_raw) == V151_VERIFICATION_BYTE_COUNT and hashlib.sha256(v151_verification_raw).hexdigest() == V151_VERIFICATION_SHA256 and predecessor_verification.get("verification_id") == V151_VERIFICATION_ID
        and registration["frozen_v151_predecessor"]["v151_campaign_id"] == V151_CAMPAIGN_ID and registration["frozen_v151_predecessor"]["v151_verification_id"] == V151_VERIFICATION_ID,
        "V152 predecessor changed",
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(len(raw) == fact["byte_count"] and hashlib.sha256(raw).hexdigest() == fact["sha256"], "V152 source closure changed")
    _require(
        canonical_json_bytes(bank) == bank_raw and bank.get("bank_id") == BANK_ID and len(bank_raw) == v151.previous.base.BANK_BYTE_COUNT and hashlib.sha256(bank_raw).hexdigest() == v151.previous.base.BANK_SHA256
        and canonical_json_bytes(bank_verification) == bank_verification_raw and bank_verification.get("verification_id") == BANK_VERIFICATION_ID and len(bank_verification_raw) == v151.previous.base.BANK_VERIFICATION_BYTE_COUNT and hashlib.sha256(bank_verification_raw).hexdigest() == v151.previous.base.BANK_VERIFICATION_SHA256
        and registration["target_occurrences"] == [{"family": family, "seed": seed} for family, seed in EXPECTED_OCCURRENCES]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES and registration["target_worker_count"] == 2 and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V152 bank or contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(executor.map(_verify_occurrence, ((row, bank) for row in campaign["target_occurrences"])))
    _require(tuple((row["family"], row["seed"]) for row in rows) == EXPECTED_OCCURRENCES and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows], "V152 occurrence inventory changed")
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(sample_labels_execution_steps_derivation_and_planning_compute_separate=True, scalar_cost_aggregation_performed=False)
    reductions = tuple(row["labels_avoided"] for row in rows)
    family_reductions = {FAMILY: sum(reductions)}
    gate = campaign["registered_gate"]
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID and campaign["accounting"] == accounting and campaign["incompatible_schema_no_transfer_control"] == incompatible_schema_no_transfer_control_v99()
        and gate["passed"] is True and gate["aggregate_paired_acquisition_label_reduction"] == sum(reductions) == 48 and gate["positive_reduction_occurrence_count"] == 6 and gate["zero_reduction_occurrence_count"] == 0 and gate["negative_reduction_occurrence_count"] == 0
        and gate["family_aggregate_reductions"] == family_reductions and gate["changed_relation_cardinality_transfer_everywhere"] is True
        and campaign["relational_template_changed_cardinality_transfer_claimed"] is True and campaign["claim_scope"] == "ONLY_THE_PREREGISTERED_V152_TERNARY_RELATION_WORKFLOW_COHORT"
        and campaign["v151_campaign_and_verification_preserved"] is True and campaign["complete_ground_world_model_synthesized"] is False and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False and campaign["official_scalar_cost"] is None and campaign["official_N_break_even"] is None and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN" and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V152 aggregate Gate changed",
    )
    payload = {
        "schema": "acfqp.ternary_relational_transfer_verification.v152",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "preserved_v151_campaign_id": V151_CAMPAIGN_ID,
        "preserved_v151_verification_id": V151_VERIFICATION_ID,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "verified_family_aggregate_reductions": family_reductions,
        "producer_free_three_key_relation_binding_reconstruction": True,
        "producer_free_changed_cardinality_template_selection_reconstruction": True,
        "producer_free_matched_stop_planning_and_certificate_reconstruction": True,
        "registered_changed_cardinality_sample_efficiency_improvement_independently_verified": True,
        "claim_scope": campaign["claim_scope"],
        "complete_world_model_claimed": False,
        "arbitrary_relation_cardinality_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": domains.extension_content_id_v152(domains.CONSTRUCTION_K7_VERIFICATION_V152_DOMAIN, payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(document["verification_id"] == VERIFICATION_ID and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256, "V152 verification changed")
    return raw


__all__ = ("VERIFICATION_ID", "freeze_ternary_relational_transfer_verification_v152")

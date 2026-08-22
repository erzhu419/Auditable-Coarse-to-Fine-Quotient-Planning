"""Producer-free verification of the V153 relation-coverage campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import FunctionType, SimpleNamespace
import copy
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp import construction_k7_domain_registry_extension_v153 as domains
from acfqp import construction_k7_relation_keyed_bank_independent_verifier_v151 as v151
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import incompatible_schema_no_transfer_control_v99
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import FAMILY, build_quaternary_relation_workflow_adapter_v153, quaternary_relation_workflow_config_v153
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "47028757be59d7b6617d01411d5e0b580944df931ecb82bcdcea27f98fccee27"
CAMPAIGN_BYTE_COUNT = 7_167_903
CAMPAIGN_SHA256 = "b85a19614111542a7cb1cd150019c7bf6775e15fc2cd4a8f6d2e8ec7c6c4f61d"
PREREGISTRATION_ID = "c8f9ea990c7408f386780e17798127dae6f1c901b9e0343442942bde53a2f230"
PREREGISTRATION_BYTE_COUNT = 4_852
PREREGISTRATION_SHA256 = "12997f69cfdf3b662ca10d3ae0d389ed307db475816d44fe0748d065728978be"
OPERATOR_RECEIPT_ID = "07b8dddbaa4915cc7cd98804cee6efefefb287d2a0512120b0dc6623dcd687a9"
OPERATOR_RECEIPT_BYTE_COUNT = 1_578
OPERATOR_RECEIPT_SHA256 = "fd07c8439e639a1fb5a2b323282f50ca7fb3f968035a9c6a539e056c54b92b95"
BANK_ID = v151.BANK_ID
BANK_VERIFICATION_ID = v151.BANK_VERIFICATION_ID
EXPECTED_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_411, 1_047_415))
EXPECTED_EPISODES = (641, 642, 643, 644)
VERIFICATION_ID = "edeec1a912c6ff4da374490fd53a1ab8eb84d0d70ef4492f8d00b367f51128ef"
EXPECTED_CANONICAL_BYTE_COUNT = 10_351
EXPECTED_CANONICAL_SHA256 = "ccc9b46543e592d238a79cefbd8f7241631f8771bf297580cd265af291628c18"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
_WRAPPER_KEYS = {
    "source_v148_acquisition_id",
    "observation_derived_relation_coverage_then_path_backtracking",
    "initial_action_relation_support_exhausted_without_generation_witness",
    "relation_field_and_delta_coordinate_selected_by_exact_dependency_rule",
    "adaptive_action_choice_uses_only_previously_observed_anonymous_relation",
    "operator_changes_query_order_not_model_hypothesis_pool_or_stop_rule",
}
_OPERATOR_GATE_KEYS = {
    "operator_receipt_frozen_before_target_outcomes",
    "adaptive_operator_reduces_labels_vs_legacy_path_first_prior",
    "factor_prior_reduces_labels_within_same_adaptive_operator",
    "adaptive_operator_reaches_accepting_observation_before_legacy",
    "four_key_relation_instantiated_and_selected",
}
_OPERATOR_ACCOUNTING_KEYS = {
    "legacy_path_first_prior_acquisition_labels",
    "labels_avoided_by_relation_coverage_operator_vs_legacy_prior",
    "labels_avoided_by_factor_prior_within_same_adaptive_operator",
}


class ConstructionK7RelationCoverageIndependentVerifierV153Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationCoverageIndependentVerifierV153Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V153 {key} changed")


def _campaign_config():
    config = quaternary_relation_workflow_config_v153()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_536
    return config


def _derive_relation(adapter, observations):
    candidates = []
    for field in range(len(adapter.catalogue[0].fields)):
        for coordinate in range(len(observations[0][2][0].pre)):
            relation = {}
            valid = True
            for _state, key, batch, _successors in observations:
                value = adapter.catalogue[key].fields[field]
                deltas = {row.post[coordinate] - row.pre[coordinate] for row in batch}
                if len(deltas) != 1 or value in relation and relation[value] != next(iter(deltas)):
                    valid = False
                    break
                relation[value] = next(iter(deltas))
            values = tuple(relation.values())
            if valid and len(relation) == len(observations) and set(relation) == {action.fields[field] for action in adapter.catalogue} and len(set(values)) == len(values) and min(values) > 0:
                candidates.append((-(max(values) - min(values)), field, coordinate, relation))
    _require(bool(candidates), "V153 independent relation coverage discovery failed")
    _span, field, coordinate, relation = min(candidates)
    return field, coordinate, relation


def _adaptive_stream(adapter):
    initial = adapter.initial()
    transition_index = 0
    queried = set()
    observations = []
    for action in adapter.actions(initial):
        key = adapter.action_key(action)
        batch = ground._transition_batch(adapter, initial, key, transition_index)  # noqa: SLF001
        transition_index += len(batch)
        successors = tuple(outcome.next_state for outcome in adapter.kernel.step(initial, action))
        observations.append((initial, key, batch, successors))
        queried.add((initial, key))
        yield batch
    field, _coordinate, relation = _derive_relation(adapter, observations)
    best = max(observations, key=lambda item: (relation[adapter.catalogue[item[1]].fields[field]], -item[1]))
    active = tuple(state for state in best[3] if adapter.active(state))
    current = min(active, key=adapter.encode) if active else None
    while current is not None and adapter.active(current):
        known = tuple(action for action in adapter.actions(current) if adapter.catalogue[adapter.action_key(action)].fields[field] in relation)
        if not known:
            break
        action = max(known, key=lambda row: (relation[adapter.catalogue[adapter.action_key(row)].fields[field]], -adapter.action_key(row)))
        key = adapter.action_key(action)
        batch = ground._transition_batch(adapter, current, key, transition_index)  # noqa: SLF001
        transition_index += len(batch)
        queried.add((current, key))
        yield batch
        active = tuple(outcome.next_state for outcome in adapter.kernel.step(current, action) if adapter.active(outcome.next_state))
        current = min(active, key=adapter.encode) if active else None
    seen = set()

    def visit(state):
        nonlocal transition_index
        if state in seen:
            return
        seen.add(state)
        for action in adapter.actions(state):
            key = adapter.action_key(action)
            if (state, key) not in queried:
                batch = ground._transition_batch(adapter, state, key, transition_index)  # noqa: SLF001
                transition_index += len(batch)
                queried.add((state, key))
                yield batch
            for outcome in adapter.kernel.step(state, action):
                if adapter.active(outcome.next_state):
                    yield from visit(outcome.next_state)

    yield from visit(initial)


def _normalized_acquisition(recorded):
    _verify_id(recorded, "acquisition_id", domains.CONSTRUCTION_K7_ACQUISITION_V153_DOMAIN)
    normalized = {
        key: copy.deepcopy(value)
        for key, value in recorded.items()
        if key not in _WRAPPER_KEYS and key != "acquisition_id"
    }
    normalized["schema"] = "acfqp.anonymous_relational_factor_bank_acquisition_arm.v148"
    normalized["fair_witness_blind_path_first_backtracking"] = True
    normalized["acquisition_id"] = recorded["source_v148_acquisition_id"]
    return normalized


def _rebuild_adaptive(recorded, adapter, bank, batches, *, enabled, config):
    return v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(recorded), adapter, bank, batches, enabled=enabled, config=config
    )


_PATH_PROXY = SimpleNamespace(**v151.previous.base.previous.base.path_predecessor.__dict__)
_PATH_PROXY._path_first_batches = _adaptive_stream
_MODEL_PROXY = SimpleNamespace(**v151.previous.base.previous.base.model.__dict__)
_MODEL_PROXY._project = v151._project_allow_nonaccepting_novel_delta
_ROBUST_BASE_PROXY = SimpleNamespace(**v151.previous.base.previous.base.__dict__)
_ROBUST_BASE_PROXY.path_predecessor = _PATH_PROXY
_ROBUST_BASE_PROXY.model = _MODEL_PROXY
_V145_PROXY = SimpleNamespace(**v151.previous.base.previous.__dict__)
_V145_PROXY.base = _ROBUST_BASE_PROXY
_V148_PROXY = SimpleNamespace(**v151.previous.base.__dict__)
_V148_PROXY.previous = _V145_PROXY
_V148_PROXY._rebuild_acquisition = _rebuild_adaptive
_V150_PROXY = SimpleNamespace(**v151.previous.__dict__)
_V150_PROXY.base = _V148_PROXY

_BASE_SEQUENCE_GLOBALS = dict(v151.previous.base.__dict__)
_BASE_SEQUENCE_GLOBALS.update(EXPECTED_EPISODES=EXPECTED_EPISODES, FAMILY=FAMILY, previous=_V145_PROXY, _fail=_fail, _require=_require)
_BASE_VERIFY_SEQUENCE = FunctionType(v151.previous.base._verify_sequence.__code__, _BASE_SEQUENCE_GLOBALS, name=v151.previous.base._verify_sequence.__name__)
_SEQUENCE_GLOBALS = dict(v151.__dict__)
_SEQUENCE_GLOBALS.update(EXPECTED_EPISODES=EXPECTED_EPISODES, previous=_V150_PROXY, _BASE_VERIFY_SEQUENCE=_BASE_VERIFY_SEQUENCE, _fail=_fail, _require=_require)
_VERIFY_SEQUENCE = FunctionType(v151._verify_sequence.__code__, _SEQUENCE_GLOBALS, name=v151._verify_sequence.__name__)

_OCCURRENCE_GLOBALS = dict(v151.__dict__)
_OCCURRENCE_GLOBALS.update(EXPECTED_OCCURRENCES=EXPECTED_OCCURRENCES, EXPECTED_EPISODES=EXPECTED_EPISODES, previous=_V150_PROXY, build_relation_keyed_workflow_adapter_v151=build_quaternary_relation_workflow_adapter_v153, _campaign_config=_campaign_config, _verify_sequence=_VERIFY_SEQUENCE, _fail=_fail, _require=_require)
_VERIFY_NORMALIZED_OCCURRENCE = FunctionType(v151._verify_occurrence.__code__, _OCCURRENCE_GLOBALS, name=v151._verify_occurrence.__name__)


def _legacy_summary(adapter, bank, *, target, config):
    stream = v151.previous.base.previous.base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(target))
    rows = []
    source = execution = instantiation = terminal_stop = None
    previous_id = None
    issued = invalidated = disagreements = epoch = successes = selected_relational = 0
    accepting = None
    for labels, batch in enumerate(batches, 1):
        rows.extend(batch)
        current = tuple(rows)
        if accepting is None and any(row.terminal_acceptance_after is True for row in batch):
            accepting = labels
        if source is not None:
            replay = v151.previous.base.exact_generic_artifact_factor_replay_v121(execution, current, adapter.catalogue)
            if replay["exact"] is True:
                successes += 1
            else:
                previous_id = source.public_document["candidate_id"]
                source = execution = instantiation = None
                invalidated += 1
                epoch += 1
                successes = 0
        if source is None:
            try:
                layout = v151.previous.base.discover_generic_layout_v5(current, adapter.catalogue, layout_domain=config["generic_domains"]["layout"])
                instantiation = v151.previous.base._instantiate(bank, current, adapter.catalogue, layout)  # noqa: SLF001
                prepared = v151.previous.base._prepare_search(current, adapter.catalogue, instantiation, config)  # noqa: SLF001
                source, compute = v151.previous.base._synthesize(current, instantiation, prepared, enabled=True, labels=labels, minimum=config["minimum_reusable_factor_count"])  # noqa: SLF001
                execution = v151.previous.base.previous._lower_candidate(source, current, adapter.catalogue)  # noqa: SLF001
                issued = labels
                selected_relational = compute["relational_artifact_expression_selected_count"]
                if previous_id is not None and source.public_document["candidate_id"] != previous_id:
                    disagreements += 1
            except Exception:
                source = execution = instantiation = None
                continue
        try:
            terminal_stop = v151.previous.base.previous._relational_stop(  # noqa: SLF001
                source, execution, current, adapter.catalogue, enabled=True, epoch=epoch, invalidated=invalidated, successes=successes, alpha=config["global_alpha_denominator"]
            )
        except Exception:
            previous_id = source.public_document["candidate_id"]
            source = execution = instantiation = None
            invalidated += 1
            epoch += 1
            successes = 0
            continue
    _require(source is not None and execution is not None and terminal_stop is not None and terminal_stop["stopped"] is True and accepting is not None, "V153 legacy baseline did not close")
    raw_rows = tuple(rows)
    return {
        "ground_support_labels": target,
        "first_accepting_observation_label": accepting,
        "raw_transition_sha256": hashlib.sha256(canonical_json_bytes([row.to_document() for row in raw_rows])).hexdigest(),
        "relational_artifact_expression_selected_count": selected_relational,
    }


def _verify_occurrence(args):
    row, bank = args
    family, seed = row["target_family"], row["seed"]
    _require((family, seed) in EXPECTED_OCCURRENCES and row.get("schema") == "acfqp.relation_coverage_planning_occurrence.v153" and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES, "V153 occurrence identity changed")
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V153_DOMAIN)
    original_gate = row["registered_gate"]
    prior = row["anonymous_relational_factor_prior_acquisition"]
    strict = row["strict_no_prior_acquisition"]
    normalized_gate = {key: copy.deepcopy(value) for key, value in original_gate.items() if key not in _OPERATOR_GATE_KEYS}
    normalized_gate.update(
        relational_artifact_selected_in_prior_arm=prior["relational_artifact_expression_selected_count"] > 0,
        same_relational_expression_available_in_strict_pool=strict["relational_artifact_expression_selected_count"] > 0,
    )
    normalized_gate["passed"] = all(normalized_gate.values())
    normalized_accounting = {key: copy.deepcopy(value) for key, value in row["accounting"].items() if key not in _OPERATOR_ACCOUNTING_KEYS}
    normalized = {
        **{key: copy.deepcopy(value) for key, value in row.items() if key != "occurrence_id"},
        "schema": "acfqp.relation_keyed_relational_bank_occurrence.v151",
        "registered_gate": normalized_gate,
        "accounting": normalized_accounting,
        "relation_binding_derived_from_raw_transition_deltas": True,
        "direct_numeric_increment_field_present": False,
        "relational_template_selection_itself_observed": True,
        "v150_cross_domain_campaign_preserved": True,
        "incomplete_abstract_path_never_used_as_execution_authority": True,
        "incomplete_abstract_plan_abstention_count": sum(
            sequence["incomplete_abstract_plan_abstention_count"]
            for sequence in (
                row["anonymous_relational_factor_prior_owned_sequence"],
                row["strict_no_prior_owned_sequence"],
            )
        ),
    }
    normalized["occurrence_id"] = v151.domains.extension_content_id_v151(v151.domains.CONSTRUCTION_K7_OCCURRENCE_V151_DOMAIN, {key: value for key, value in normalized.items() if key != "occurrence_id"})
    verified = _VERIFY_NORMALIZED_OCCURRENCE((normalized, bank))
    config = _campaign_config()
    adapter = build_quaternary_relation_workflow_adapter_v153(seed, config)
    legacy_recorded = row["legacy_path_first_prior_acquisition_summary"]
    legacy = _legacy_summary(adapter, bank, target=legacy_recorded["ground_support_labels"], config=config)
    operator_reduction = legacy["ground_support_labels"] - prior["ground_support_labels"]
    prior_reduction = strict["ground_support_labels"] - prior["ground_support_labels"]
    expected_operator_gate = {
        "operator_receipt_frozen_before_target_outcomes": True,
        "adaptive_operator_reduces_labels_vs_legacy_path_first_prior": operator_reduction > 0,
        "factor_prior_reduces_labels_within_same_adaptive_operator": prior_reduction > 0,
        "adaptive_operator_reaches_accepting_observation_before_legacy": prior["first_accepting_observation_label"] < legacy["first_accepting_observation_label"],
        "four_key_relation_instantiated_and_selected": prior["relational_artifact_expression_selected_count"] > 0,
    }
    _require(
        all(original_gate[key] is value for key, value in expected_operator_gate.items())
        and legacy == {key: legacy_recorded[key] for key in legacy}
        and type(legacy_recorded.get("acquisition_id")) is str and len(legacy_recorded["acquisition_id"]) == 64
        and row["operator_receipt_id"] == OPERATOR_RECEIPT_ID
        and row["operator_sample_reduction_vs_legacy_prior"] == operator_reduction
        and row["factor_prior_sample_reduction_within_adaptive_operator"] == prior_reduction
        and row["accounting"] == {**normalized_accounting, "legacy_path_first_prior_acquisition_labels": legacy["ground_support_labels"], "labels_avoided_by_relation_coverage_operator_vs_legacy_prior": operator_reduction, "labels_avoided_by_factor_prior_within_same_adaptive_operator": prior_reduction}
        and row["operator_is_planning_or_certificate_authority"] is False
        and row["v151_v152_evidence_preserved"] is True,
        "V153 operator occurrence evidence changed",
    )
    return {
        **verified,
        "occurrence_id": row["occurrence_id"],
        "legacy_path_first_prior_labels": legacy["ground_support_labels"],
        "operator_labels_avoided": operator_reduction,
        "factor_prior_labels_avoided_within_operator": prior_reduction,
        "accounting": row["accounting"],
    }


def freeze_relation_coverage_verification_v153(campaign_raw: bytes, preregistration_raw: bytes, operator_receipt_raw: bytes, bank_raw: bytes, bank_verification_raw: bytes):
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    receipt = loads_canonical_json(operator_receipt_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    _require(canonical_json_bytes(campaign) == campaign_raw and len(campaign_raw) == CAMPAIGN_BYTE_COUNT and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256 and campaign.get("campaign_id") == CAMPAIGN_ID, "V153 campaign identity changed")
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V153_DOMAIN)
    _require(canonical_json_bytes(registration) == preregistration_raw and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT and hashlib.sha256(preregistration_raw).hexdigest() == PREREGISTRATION_SHA256 and registration.get("preregistration_id") == PREREGISTRATION_ID, "V153 preregistration identity changed")
    _verify_id(registration, "preregistration_id", domains.CONSTRUCTION_K7_PREREGISTRATION_V153_DOMAIN)
    _require(canonical_json_bytes(receipt) == operator_receipt_raw and len(operator_receipt_raw) == OPERATOR_RECEIPT_BYTE_COUNT and hashlib.sha256(operator_receipt_raw).hexdigest() == OPERATOR_RECEIPT_SHA256 and receipt.get("operator_receipt_id") == OPERATOR_RECEIPT_ID and registration["frozen_operator_receipt"] == receipt, "V153 operator receipt changed")
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(len(raw) == fact["byte_count"] and hashlib.sha256(raw).hexdigest() == fact["sha256"], "V153 source closure changed")
    _require(
        canonical_json_bytes(bank) == bank_raw and bank.get("bank_id") == BANK_ID and len(bank_raw) == v151.previous.base.BANK_BYTE_COUNT and hashlib.sha256(bank_raw).hexdigest() == v151.previous.base.BANK_SHA256
        and canonical_json_bytes(bank_verification) == bank_verification_raw and bank_verification.get("verification_id") == BANK_VERIFICATION_ID and len(bank_verification_raw) == v151.previous.base.BANK_VERIFICATION_BYTE_COUNT and hashlib.sha256(bank_verification_raw).hexdigest() == v151.previous.base.BANK_VERIFICATION_SHA256
        and registration["target_occurrences"] == [{"family": family, "seed": seed} for family, seed in EXPECTED_OCCURRENCES] and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES and registration["target_worker_count"] == 2 and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V153 bank or registered contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(executor.map(_verify_occurrence, ((row, bank) for row in campaign["target_occurrences"])))
    _require(tuple((row["family"], row["seed"]) for row in rows) == EXPECTED_OCCURRENCES and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows], "V153 occurrence inventory changed")
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(sample_labels_execution_steps_derivation_and_planning_compute_separate=True, scalar_cost_aggregation_performed=False)
    operator_reduction = sum(row["operator_labels_avoided"] for row in rows)
    prior_reduction = sum(row["factor_prior_labels_avoided_within_operator"] for row in rows)
    gate = campaign["registered_gate"]
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID and campaign["operator_receipt_id"] == OPERATOR_RECEIPT_ID and campaign["accounting"] == accounting and campaign["incompatible_schema_no_transfer_control"] == incompatible_schema_no_transfer_control_v99()
        and gate["passed"] is True and gate["aggregate_operator_sample_reduction_vs_legacy_prior"] == operator_reduction == 345 and gate["aggregate_factor_prior_reduction_within_adaptive_operator"] == prior_reduction == 20
        and gate["operator_positive_everywhere"] is True and gate["factor_prior_positive_within_operator_everywhere"] is True
        and campaign["sample_tax_reduction_operator_observed"] is True and campaign["operator_is_model_planning_or_certificate_authority"] is False and campaign["complete_world_model_synthesized"] is False
        and campaign["official_execution_allowed"] is False and campaign["official_scalar_cost"] is None and campaign["official_N_break_even"] is None and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN" and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V153 aggregate Gate changed",
    )
    payload = {
        "schema": "acfqp.relation_coverage_verification.v153",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "operator_receipt_id": OPERATOR_RECEIPT_ID,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_relation_coverage_discovery_and_query_reconstruction": True,
        "producer_free_legacy_path_first_baseline_reconstruction": True,
        "producer_free_adaptive_prior_strict_stop_reconstruction": True,
        "producer_free_abstract_planning_and_certificate_recovery_reconstruction": True,
        "registered_operator_sample_tax_reduction_independently_verified": True,
        "operator_sample_reduction_vs_legacy_prior": operator_reduction,
        "factor_prior_sample_reduction_within_operator": prior_reduction,
        "operator_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": domains.extension_content_id_v153(domains.CONSTRUCTION_K7_VERIFICATION_V153_DOMAIN, payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(document["verification_id"] == VERIFICATION_ID and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256, "V153 verification changed")
    return raw


__all__ = ("VERIFICATION_ID", "freeze_relation_coverage_verification_v153")

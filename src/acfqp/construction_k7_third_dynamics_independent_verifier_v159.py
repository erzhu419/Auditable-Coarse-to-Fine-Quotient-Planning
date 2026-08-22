"""Producer-free verification of the frozen V159 third-dynamics campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp import construction_k7_domain_registry_extension_v159 as domains
from acfqp import construction_k7_plan_mode_margin_independent_verifier_v157 as v157
from acfqp import construction_k7_relation_keyed_bank_independent_verifier_v151 as v151
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY,
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.joint_factor_query_classifier_core_v159 import (
    anonymous_initial_support_signature_v159,
    build_initial_factorization_source_observation_v159,
    evaluate_joint_factor_query_expression_v159,
    factorization_relation_candidates_v159,
    synthesize_joint_factor_query_classifier_v159,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "76561d796084acf486f92e55feeca59a2b671cfacd03ddd2eb17230a8503bc55"
CAMPAIGN_BYTE_COUNT = 22_440_110
CAMPAIGN_SHA256 = "10befc870c0ef542b32dc401e8f6d81bc99314c5ec6cc972ad56d161dad23748"
PREREGISTRATION_ID = "c4d0d30374737df6ee38cfcd7e3ee9ba2f642007f753a9a43d8440154a36d413"
PREREGISTRATION_BYTE_COUNT = 13_314
PREREGISTRATION_SHA256 = "d1b705eab085c549a616d9811f6cd3d61d958f6390cc1feff9cc2eb64cd776bb"
SOURCE_PREREGISTRATION_ID = "1557a40366dc59e928e265891599fa23299f3384c6eeffab79c47f488c46f295"
SOURCE_PREREGISTRATION_BYTE_COUNT = 2_287
SOURCE_PREREGISTRATION_SHA256 = "2abfd32124b8106138fbff8805394d11bb0f882b3a4e603adcc0ad760d7269f1"
CLASSIFIER_RECEIPT_ID = "464febb181620c04c171817ca1b934b3014e7fcc48cdc5a8162bfd5ba23e954a"
CLASSIFIER_RECEIPT_BYTE_COUNT = 10_690
CLASSIFIER_RECEIPT_SHA256 = "cff14491ae87b69ef853cbf55109be0b0122ead9b9045fe3c4407bc574794317"
V157_CAMPAIGN_ID = v157.CAMPAIGN_ID
V157_CAMPAIGN_BYTE_COUNT = v157.CAMPAIGN_BYTE_COUNT
V157_CAMPAIGN_SHA256 = v157.CAMPAIGN_SHA256
V157_VERIFICATION_ID = v157.VERIFICATION_ID
V157_VERIFICATION_BYTE_COUNT = v157.EXPECTED_CANONICAL_BYTE_COUNT
V157_VERIFICATION_SHA256 = v157.EXPECTED_CANONICAL_SHA256
BANK_ID = v157.BANK_ID
BANK_VERIFICATION_ID = v157.BANK_VERIFICATION_ID
SOURCE_CALIBRATION_SEEDS = (1_048_101, 1_048_102, 1_048_103, 1_048_104)
EXPECTED_SEEDS = (1_048_121, 1_048_122, 1_048_123, 1_048_124)
EXPECTED_EPISODES = (821, 822, 823, 824)
VERIFICATION_ID = "43714af046dc9ec04a3d35fddec08c6e803867afbde154f8a2cbae3e9cf5bebb"
EXPECTED_CANONICAL_BYTE_COUNT = 14_492
EXPECTED_CANONICAL_SHA256 = "cae733f19abf841dc37bfeb6d4cb038a4a1cd480fe452cf25d069ac262d0faae"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
_ACQUISITION_ADDITIONS = {
    "source_v148_acquisition_id",
    "joint_factor_query_classifier_receipt_id",
    "anonymous_initial_action_support_signature",
    "selected_classifier_expression",
    "selected_predicate_match_count",
    "query_policy_decision",
    "v158_metadata_classifier_counterfactual_match_count",
    "v158_metadata_classifier_counterfactual_decision",
    "source_labels_derived_from_raw_factorization_differences",
    "target_factorization_probe_labels_added_by_classifier",
    "exact_signature_registry_consulted",
    "classifier_accessed_target_ground_successor_outcomes",
    "classifier_changes_query_order_not_hypothesis_pool_or_stop_rule",
    "classifier_is_model_planning_or_certificate_authority",
}


class ConstructionK7ThirdDynamicsIndependentVerifierV159Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThirdDynamicsIndependentVerifierV159Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V159 {key} changed")


def _frozen(raw, document, *, count, digest, key, identity, label):
    _require(
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(key) == identity,
        f"V159 frozen {label} changed",
    )


def _source_signatures(campaign):
    rows = []
    for occurrence in campaign["target_occurrences"]:
        acquisition = occurrence["anonymous_relational_factor_prior_acquisition"]
        signature = tuple(
            tuple(pair)
            for pair in acquisition["anonymous_initial_action_support_signature"]
        )
        rows.append(
            (signature, acquisition["guard_decision"] == "RELATION_COVERAGE")
        )
    return tuple(sorted(set(rows)))


def _verify_classifier_receipt(
    raw,
    source_registration,
    source_campaign,
    source_verification,
):
    config = modular_routing_config_v128()
    observations = tuple(
        build_initial_factorization_source_observation_v159(
            build_modular_routing_adapter_v128(seed, config)
        )
        for seed in SOURCE_CALIBRATION_SEEDS
    )
    labelled = list(_source_signatures(source_campaign))
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
        "source_preregistration_id": SOURCE_PREREGISTRATION_ID,
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
    expected = {
        **payload,
        "classifier_receipt_id": _content_id(
            domains.CONSTRUCTION_K7_CLASSIFIER_RECEIPT_V159_DOMAIN, payload
        ),
    }
    document = loads_canonical_json(raw)
    _frozen(
        raw,
        document,
        count=CLASSIFIER_RECEIPT_BYTE_COUNT,
        digest=CLASSIFIER_RECEIPT_SHA256,
        key="classifier_receipt_id",
        identity=CLASSIFIER_RECEIPT_ID,
        label="classifier receipt",
    )
    _require(
        source_verification.get(
            "registered_plan_mode_corrected_margin_evidence_independently_verified"
        )
        is True
        and document == expected,
        "V159 source factorization labels or classifier were not independently rederived",
    )
    return document


def _config():
    config = modular_routing_config_v128()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 2_048
    return config


def _normalized_acquisition(recorded, *, classifier, signature, selected, count):
    _verify_id(
        recorded, "acquisition_id", domains.CONSTRUCTION_K7_ACQUISITION_V159_DOMAIN
    )
    v158_count = sum(pair[0] == 1 for pair in signature)
    _require(
        recorded.get("schema") == "acfqp.joint_factor_query_acquisition_arm.v159"
        and recorded.get("joint_factor_query_classifier_receipt_id")
        == CLASSIFIER_RECEIPT_ID
        and recorded.get("anonymous_initial_action_support_signature")
        == [list(pair) for pair in signature]
        and recorded.get("selected_classifier_expression")
        == classifier["selected_expression"]
        and recorded.get("selected_predicate_match_count") == count
        and recorded.get("query_policy_decision")
        == ("RELATION_COVERAGE" if selected else "PATH_FIRST_SAFE_FALLBACK")
        and recorded.get("v158_metadata_classifier_counterfactual_match_count")
        == v158_count
        and recorded.get("v158_metadata_classifier_counterfactual_decision")
        == ("RELATION_COVERAGE" if v158_count > 1 else "PATH_FIRST_SAFE_FALLBACK")
        and recorded.get("source_labels_derived_from_raw_factorization_differences")
        is True
        and recorded.get("target_factorization_probe_labels_added_by_classifier")
        == 0
        and recorded.get("exact_signature_registry_consulted") is False
        and recorded.get("classifier_accessed_target_ground_successor_outcomes")
        is False
        and recorded.get("classifier_changes_query_order_not_hypothesis_pool_or_stop_rule")
        is True
        and recorded.get("classifier_is_model_planning_or_certificate_authority")
        is False,
        "V159 acquisition wrapper changed",
    )
    normalized = {
        key: copy.deepcopy(value)
        for key, value in recorded.items()
        if key not in _ACQUISITION_ADDITIONS and key != "acquisition_id"
    }
    normalized["schema"] = "acfqp.anonymous_relational_factor_bank_acquisition_arm.v148"
    normalized["acquisition_id"] = recorded["source_v148_acquisition_id"]
    return normalized


def _sequence_verifier(family):
    globals_v150 = dict(v157.__dict__)
    globals_v150.update(
        EXPECTED_EPISODES=EXPECTED_EPISODES, _fail=_fail, _require=_require
    )
    factory = FunctionType(
        v157._v150_sequence_verifier.__code__,  # noqa: SLF001
        globals_v150,
        name=v157._v150_sequence_verifier.__name__,  # noqa: SLF001
    )
    return factory(family)


def _verify_sequence(sequence, candidate, rows, *, seed):
    globals_v157 = dict(v157.__dict__)
    globals_v157.update(
        _v150_sequence_verifier=_sequence_verifier, _fail=_fail, _require=_require
    )
    verifier = FunctionType(
        v157._verify_sequence.__code__,  # noqa: SLF001
        globals_v157,
        name=v157._verify_sequence.__name__,  # noqa: SLF001
    )
    return verifier(sequence, candidate, rows, family=FAMILY, seed=seed)


def _factorization_corroboration(adapter, rows):
    initial = adapter.encode(adapter.initial())
    initial_keys = tuple(
        adapter.action_key(action) for action in adapter.actions(adapter.initial())
    )
    observations = []
    additional = 0
    transition_index = max(row.index for row in rows) + 1
    for key in initial_keys:
        selected = tuple(
            row for row in rows if row.pre == initial and row.action.key == key
        )
        if not selected:
            selected = ground._transition_batch(  # noqa: SLF001
                adapter, adapter.initial(), key, transition_index
            )
            transition_index += len(selected)
            additional += 1
        observations.append({"action_key": key, "rows": selected})
    candidates = factorization_relation_candidates_v159(adapter, observations)
    return {
        "initial_action_count": len(initial_keys),
        "initial_actions_recovered_from_already_paid_target_rows": additional == 0,
        "additional_target_factorization_probe_labels": additional,
        "factorization_relation_candidates": list(candidates),
        "factorization_relation_candidate_count": len(candidates),
        "positive_factorization_relation_present": bool(candidates),
        "classifier_decision_corroborated_by_paid_raw_differences": True,
    }


def _verify_occurrence(args):
    row, bank, classifier = args
    seed = row["seed"]
    _require(
        seed in EXPECTED_SEEDS
        and row.get("target_family") == FAMILY
        and row.get("schema")
        == "acfqp.third_dynamics_joint_factor_query_occurrence.v159"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES,
        "V159 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V159_DOMAIN)
    config = _config()
    adapter = build_modular_routing_adapter_v128(seed, config)
    signature = anonymous_initial_support_signature_v159(adapter)
    selected, count = evaluate_joint_factor_query_expression_v159(
        classifier["selected_expression"], signature
    )
    _require(selected is False, "V159 classifier no longer selects safe fallback")
    prior_doc = row["joint_policy_prior_acquisition"]
    strict_doc = row["joint_policy_strict_acquisition"]
    stream = v151.previous.base.previous.base.path_predecessor._path_first_batches(  # noqa: SLF001
        adapter
    )
    batches = tuple(next(stream) for _ in range(strict_doc["ground_support_labels"]))
    prior_candidate, prior_rows = v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(
            prior_doc,
            classifier=classifier,
            signature=signature,
            selected=selected,
            count=count,
        ),
        adapter,
        bank,
        batches,
        enabled=True,
        config=config,
    )
    strict_candidate, strict_rows = v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(
            strict_doc,
            classifier=classifier,
            signature=signature,
            selected=selected,
            count=count,
        ),
        adapter,
        bank,
        batches,
        enabled=False,
        config=config,
    )
    prior_sequence, prior_mode = _verify_sequence(
        row["joint_policy_prior_sequence"], prior_candidate, prior_rows, seed=seed
    )
    strict_sequence, strict_mode = _verify_sequence(
        row["joint_policy_strict_sequence"], strict_candidate, strict_rows, seed=seed
    )
    _require(
        prior_mode == strict_mode == "DIRECT_GENERIC_FACTOR_PROGRAM",
        "V159 plan receipt mode changed",
    )
    factorization = _factorization_corroboration(adapter, prior_rows)
    _require(
        row["paid_target_factorization_corroboration"] == factorization,
        "V159 target factorization audit changed",
    )
    guard_reduction = 0
    factor_reduction = strict_doc["ground_support_labels"] - prior_doc[
        "ground_support_labels"
    ]
    accounting = {
        "joint_policy_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "joint_policy_strict_acquisition_labels": strict_doc["ground_support_labels"],
        "legacy_path_first_prior_acquisition_labels": prior_doc[
            "ground_support_labels"
        ],
        "labels_avoided_by_joint_query_policy_vs_legacy_path_first": 0,
        "labels_avoided_by_factor_prior_within_joint_query_policy": factor_reduction,
        "joint_policy_prior_certificate_local_labels": prior_sequence[
            "certificate_local_labels"
        ],
        "joint_policy_strict_certificate_local_labels": strict_sequence[
            "certificate_local_labels"
        ],
        "joint_policy_prior_execution_steps": prior_sequence["execution_steps"],
        "joint_policy_strict_execution_steps": strict_sequence["execution_steps"],
        "joint_policy_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "joint_policy_strict_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "joint_policy_prior_planning_compute_events": prior_sequence[
            "planning_compute_events"
        ],
        "joint_policy_strict_planning_compute_events": strict_sequence[
            "planning_compute_events"
        ],
        "additional_target_factorization_probe_labels": factorization[
            "additional_target_factorization_probe_labels"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    source_sequences = (
        row["joint_policy_prior_sequence"],
        row["joint_policy_strict_sequence"],
    )
    gate = {
        "fresh_target_identity": True,
        "distinct_modular_partial_stochastic_dynamics_exercised": True,
        "classifier_receipt_frozen_before_target_outcomes": classifier[
            "fresh_v159_target_outcomes_accessed"
        ]
        is False,
        "source_labels_derived_from_raw_factorization_differences": all(
            document["source_labels_derived_from_raw_factorization_differences"]
            is True
            for document in (prior_doc, strict_doc)
        ),
        "v158_metadata_classifier_false_positive_observed": all(
            document["v158_metadata_classifier_counterfactual_decision"]
            == "RELATION_COVERAGE"
            for document in (prior_doc, strict_doc)
        ),
        "joint_factor_classifier_selected_safe_fallback": all(
            document["query_policy_decision"] == "PATH_FIRST_SAFE_FALLBACK"
            for document in (prior_doc, strict_doc)
        ),
        "paid_raw_factorization_corroborates_fallback": factorization[
            "positive_factorization_relation_present"
        ]
        is False,
        "bounded_target_factorization_audit_labels": factorization[
            "additional_target_factorization_probe_labels"
        ]
        <= 1,
        "fallback_is_exact_legacy_path_first": True,
        "query_policy_introduced_zero_sample_regression": guard_reduction == 0,
        "factor_prior_noninferior_within_joint_policy": factor_reduction >= 0,
        "matched_acquisition_completed_within_cap": all(
            0 < document["ground_support_labels"] <= 2_048
            for document in (prior_doc, strict_doc)
        ),
        "both_arms_use_same_synthesizer_and_stop_rule": all(
            prior_doc[key] is True and strict_doc[key] is True
            for key in (
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "both_arm_receding_episodes_succeed": all(
            episode["success"]
            for sequence in source_sequences
            for episode in sequence["episodes"]
        ),
        "planner_consumes_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in source_sequences
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in source_sequences
        ),
        "query_local_overlay_not_promoted_to_global_dynamics": all(
            sequence["source_partial_program_mutated_after_certificate_failure"]
            is False
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in source_sequences
        ),
        "direct_generic_plan_receipt_mode_exercised_both_arms": all(
            sequence["applicable_plan_receipt_mode"]
            == "DIRECT_GENERIC_FACTOR_PROGRAM"
            for sequence in source_sequences
        ),
        "all_executed_actions_have_v109_receipts": all(
            sequence["all_executed_actions_have_v109_receipts"]
            for sequence in source_sequences
        ),
        "exact_signature_registry_not_consulted": all(
            document["exact_signature_registry_consulted"] is False
            for document in (prior_doc, strict_doc)
        ),
    }
    gate["passed"] = all(gate.values())
    _require(
        row["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
        and row["v146_factor_bank_id"] == BANK_ID
        and row["v146_independent_verification_id"] == BANK_VERIFICATION_ID
        and row["accounting"] == accounting
        and row["registered_gate"] == gate
        and row["guard_sample_reduction_vs_legacy_path_first"] == 0
        and row["factor_prior_sample_reduction_within_joint_policy"]
        == factor_reduction
        and row["sample_tax_claim_scope"]
        == "ONLY_THIS_PREREGISTERED_V159_THIRD_DYNAMICS_COHORT"
        and row[
            "query_policy_classifier_is_model_planning_or_certificate_authority"
        ]
        is False
        and row["complete_world_model_synthesized"] is False
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["official_N_break_even"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and row["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V159 occurrence evidence changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "seed": seed,
        "signature": [list(pair) for pair in signature],
        "predicate_match_count": count,
        "factorization": factorization,
        "guard_labels_avoided": 0,
        "factor_prior_labels_avoided": factor_reduction,
        "prior_sequence": prior_sequence,
        "strict_sequence": strict_sequence,
        "accounting": accounting,
        "registered_gate": gate,
    }


def freeze_third_dynamics_verification_v159(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    classifier_receipt_raw: bytes,
    source_preregistration_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v157_campaign_raw: bytes,
    v157_verification_raw: bytes,
):
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    source_registration = loads_canonical_json(source_preregistration_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    source_campaign = loads_canonical_json(v157_campaign_raw)
    source_verification = loads_canonical_json(v157_verification_raw)
    _frozen(
        campaign_raw,
        campaign,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        key="campaign_id",
        identity=CAMPAIGN_ID,
        label="campaign",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V159_DOMAIN)
    _frozen(
        preregistration_raw,
        registration,
        count=PREREGISTRATION_BYTE_COUNT,
        digest=PREREGISTRATION_SHA256,
        key="preregistration_id",
        identity=PREREGISTRATION_ID,
        label="target preregistration",
    )
    _verify_id(
        registration,
        "preregistration_id",
        domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V159_DOMAIN,
    )
    _frozen(
        source_preregistration_raw,
        source_registration,
        count=SOURCE_PREREGISTRATION_BYTE_COUNT,
        digest=SOURCE_PREREGISTRATION_SHA256,
        key="source_preregistration_id",
        identity=SOURCE_PREREGISTRATION_ID,
        label="source preregistration",
    )
    _verify_id(
        source_registration,
        "source_preregistration_id",
        domains.CONSTRUCTION_K7_SOURCE_PREREGISTRATION_V159_DOMAIN,
    )
    _frozen(
        v157_campaign_raw,
        source_campaign,
        count=V157_CAMPAIGN_BYTE_COUNT,
        digest=V157_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V157_CAMPAIGN_ID,
        label="V157 source campaign",
    )
    _frozen(
        v157_verification_raw,
        source_verification,
        count=V157_VERIFICATION_BYTE_COUNT,
        digest=V157_VERIFICATION_SHA256,
        key="verification_id",
        identity=V157_VERIFICATION_ID,
        label="V157 source verification",
    )
    classifier = _verify_classifier_receipt(
        classifier_receipt_raw,
        source_registration,
        source_campaign,
        source_verification,
    )
    _require(
        canonical_json_bytes(bank) == bank_raw
        and bank.get("bank_id") == BANK_ID
        and len(bank_raw) == v151.previous.base.BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest() == v151.previous.base.BANK_SHA256
        and canonical_json_bytes(bank_verification) == bank_verification_raw
        and bank_verification.get("verification_id") == BANK_VERIFICATION_ID
        and len(bank_verification_raw) == v151.previous.base.BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest()
        == v151.previous.base.BANK_VERIFICATION_SHA256,
        "V159 frozen factor bank changed",
    )
    for fact in (
        *source_registration["frozen_implementation_source_facts"],
        *registration["frozen_implementation_source_facts"],
    ):
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(
            len(raw) == fact["byte_count"]
            and hashlib.sha256(raw).hexdigest() == fact["sha256"],
            "V159 source closure changed",
        )
    _require(
        source_registration["source_calibration_seeds"]
        == list(SOURCE_CALIBRATION_SEEDS)
        and all(source_registration["registered_source_gate"].values())
        and source_registration["claim_boundary"]["source_outcomes_accessed"]
        is False
        and registration["frozen_classifier_receipt"] == classifier
        and registration["target_occurrences"]
        == [{"family": FAMILY, "seed": seed} for seed in EXPECTED_SEEDS]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["required_target_occurrence_count"] == 4
        and registration["maximum_acquisition_labels"] == 2_048
        and registration[
            "maximum_target_factorization_audit_labels_per_occurrence"
        ]
        == 1
        and all(registration["registered_gate"].values())
        and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V159 preregistered contracts changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(
            executor.map(
                _verify_occurrence,
                ((row, bank, classifier) for row in campaign["target_occurrences"]),
            )
        )
    _require(
        tuple(row["seed"] for row in rows) == EXPECTED_SEEDS
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V159 occurrence inventory changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    accounting.update(
        offline_source_factorization_labels=8,
        target_factorization_probe_labels=sum(
            row["accounting"]["additional_target_factorization_probe_labels"]
            for row in rows
        ),
        source_and_target_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    factors = tuple(row["factor_prior_labels_avoided"] for row in rows)
    guards = tuple(row["guard_labels_avoided"] for row in rows)
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "fresh_third_dynamics_occurrence_count": len(rows),
        "v158_false_positive_repaired_everywhere": all(
            row["registered_gate"][
                "v158_metadata_classifier_false_positive_observed"
            ]
            and row["registered_gate"][
                "joint_factor_classifier_selected_safe_fallback"
            ]
            for row in rows
        ),
        "paid_factorization_corroborates_fallback_everywhere": all(
            row["factorization"]["positive_factorization_relation_present"] is False
            for row in rows
        ),
        "bounded_target_factorization_audit_labels": accounting[
            "target_factorization_probe_labels"
        ]
        <= 4,
        "zero_query_policy_sample_regression_everywhere": all(
            value == 0 for value in guards
        ),
        "aggregate_factor_prior_sample_reduction": sum(factors),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factors),
        "factor_prior_positive_in_aggregate": sum(factors) > 0,
        "both_arm_receding_plans_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "certificate_failure_local_recovery_exercised": sum(
            row["accounting"]["joint_policy_prior_certificate_local_labels"]
            + row["accounting"]["joint_policy_strict_certificate_local_labels"]
            for row in rows
        )
        > 0,
        "direct_generic_and_v109_receipt_path_exercised_everywhere": all(
            row["registered_gate"][
                "direct_generic_plan_receipt_mode_exercised_both_arms"
            ]
            and row["registered_gate"]["all_executed_actions_have_v109_receipts"]
            for row in rows
        ),
        "strict_incompatible_schema_no_transfer_verified": incompatible_schema_no_transfer_control_v99()[
            "strict_ood_no_transfer"
        ],
    }
    gate["passed"] = (
        len(rows) == gate["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    _require(
        campaign["schema"] == "acfqp.third_dynamics_joint_factor_query_campaign.v159"
        and campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
        and campaign["incompatible_schema_no_transfer_control"]
        == incompatible_schema_no_transfer_control_v99()
        and campaign["accounting"] == accounting
        and campaign["registered_gate"] == gate
        and gate["passed"] is True
        and sum(guards) == 0
        and sum(factors) == 32
        and accounting["target_factorization_probe_labels"] == 3
        and campaign[
            "third_genuinely_distinct_partial_stochastic_dynamics_verified"
        ]
        is True
        and campaign["joint_factorization_labelled_query_policy_verified"] is True
        and campaign["sample_tax_claim_scope"]
        == "ONLY_THIS_PREREGISTERED_V159_THIRD_DYNAMICS_COHORT"
        and campaign[
            "query_policy_classifier_is_model_planning_or_certificate_authority"
        ]
        is False
        and campaign["complete_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V159 aggregate evidence changed",
    )
    payload = {
        "schema": "acfqp.third_dynamics_verification.v159",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "source_preregistration_id": SOURCE_PREREGISTRATION_ID,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "source_v157_campaign_id": V157_CAMPAIGN_ID,
        "source_v157_verification_id": V157_VERIFICATION_ID,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_source_factorization_label_reconstruction": True,
        "producer_free_joint_classifier_reconstruction": True,
        "producer_free_target_acquisition_and_factorization_audit_reconstruction": True,
        "producer_free_abstract_planning_plan_receipt_and_certificate_reconstruction": True,
        "third_dynamics_joint_factor_query_evidence_independently_verified": True,
        "query_policy_guard_sample_reduction_vs_legacy": 0,
        "factor_prior_sample_reduction_within_joint_policy": 32,
        "offline_source_factorization_labels": 8,
        "target_factorization_audit_labels": 3,
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
        **payload,
        "verification_id": _content_id(
            domains.CONSTRUCTION_K7_VERIFICATION_V159_DOMAIN, payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V159 frozen verification changed",
        )
    return raw


__all__ = ("VERIFICATION_ID", "freeze_third_dynamics_verification_v159")

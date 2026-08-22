"""Producer-free reconstruction of the frozen V168 campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v150 as domains_v150
from acfqp import construction_k7_domain_registry_extension_v154 as domains_v154
from acfqp import construction_k7_domain_registry_extension_v157 as domains_v157
from acfqp import construction_k7_domain_registry_extension_v168 as domains
from acfqp import construction_k7_plan_mode_margin_independent_verifier_v157 as v157
from acfqp import construction_k7_safe_paid_path_sample_tax_independent_verifier_v163 as previous
from acfqp import construction_k7_sample_tax_replication_independent_verifier_v164 as replication
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET_BATCHING_FAMILY,
    build_packet_batching_adapter_v134,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce"
CAMPAIGN_BYTE_COUNT = 25_586_483
CAMPAIGN_SHA256 = (
    "e0cd4d36fb72bf79519878e1a368aeecf128cd91c4571bf0071d68af2760dfa5"
)
PREREGISTRATION_ID = (
    "0857616c9066fef7c2502827b8ffb337848dbf230d61aa436555b3c0dde2bc89"
)
PREREGISTRATION_BYTE_COUNT = 3_041
PREREGISTRATION_SHA256 = (
    "a6896bcca48ec67c3ed8963dab50f552da9f42c81343c280b16a7c7174f76f9c"
)
V166_FAILURE_ID = (
    "2d299454ac4aaa7d0517875f568b90a782d79c1c4aa6881b5d0e18ab48d15911"
)
V166_FAILURE_BYTE_COUNT = 1_800
V166_FAILURE_SHA256 = (
    "22333a80c08c1915da8659b25651ee8b49850a7fea132d0acb6df0540dabc51c"
)
V164_CAMPAIGN_ID = "108bc4cf4f61123c6da7812ae76a48c21027a3b5e32e80005952a93b2ab8da1c"
V164_VERIFICATION_ID = (
    "1095eec978a045ac3fec2ef0848927ecf7ce3d290d68415656b28fe34b3f298f"
)
V165_AUDIT_ID = "8de483f4f827caddf96dd367b470aba6b8fef409f3cc060c4f3308fd592cbdeb"
V165_VERIFICATION_ID = (
    "d9aab6590d650f534edf19b7f87fd51045cd0d07cdf9d528f9873de3421e6390"
)
V167_CAMPAIGN_ID = "433be30e23c4c6f1a27b6e271fb02127b3b62e8218268de8941eec64bec94839"
V167_CAMPAIGN_BYTE_COUNT = 23_911_368
V167_CAMPAIGN_SHA256 = (
    "73a52baa738282a18a64b5be7c4aff0f089038647b9adeca9c8ecabe2b56920b"
)
V167_VERIFICATION_ID = (
    "c45e31ec1b25c87398361fedd04d5c96d9b05a95d465592a85bef7d2af4b6dd8"
)
V167_VERIFICATION_BYTE_COUNT = 28_646
V167_VERIFICATION_SHA256 = (
    "f850ae07d362acceb59732ce2fe4a163e86aa5e4d1071c4aa2a7b6683fbf9a6f"
)
TARGET_FAMILIES = (PACKET_BATCHING_FAMILY,)
EXPECTED_OCCURRENCES = (
    (PACKET_BATCHING_FAMILY, 1_049_851),
    (PACKET_BATCHING_FAMILY, 1_049_852),
)
EXPECTED_EPISODES = (953, 954, 955, 956)
VERIFICATION_ID = (
    "11378538ea1d8340647b9e172f34c7e6f427a1d177a045074e596329c2cb8908"
)
EXPECTED_CANONICAL_BYTE_COUNT = 10_215
EXPECTED_CANONICAL_SHA256 = (
    "ecf1c0d10fc9cedc508353425cbf2c93533a52cbd2b07af2076eb5b9161cbc09"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
DIRECT_MODE = "DIRECT_GENERIC_FACTOR_PROGRAM"
MEMOIZED_MODE = "V115_MEMOIZED_COMPILED_PROGRAM"
REGISTERED_MODES = (DIRECT_MODE, MEMOIZED_MODE)
RECEIPT_SET_TRUTH_TABLE = (
    {
        "registered_counts": {DIRECT_MODE: 1, MEMOIZED_MODE: 0},
        "modes": [DIRECT_MODE],
        "receipt_set_class": "DIRECT_ONLY",
        "none_defers_to_v109_and_query_local_certificate": False,
    },
    {
        "registered_counts": {DIRECT_MODE: 0, MEMOIZED_MODE: 1},
        "modes": [MEMOIZED_MODE],
        "receipt_set_class": "MEMOIZED_ONLY",
        "none_defers_to_v109_and_query_local_certificate": False,
    },
    {
        "registered_counts": {DIRECT_MODE: 1, MEMOIZED_MODE: 1},
        "modes": [DIRECT_MODE, MEMOIZED_MODE],
        "receipt_set_class": "MIXED",
        "none_defers_to_v109_and_query_local_certificate": False,
    },
    {
        "registered_counts": {DIRECT_MODE: 0, MEMOIZED_MODE: 0},
        "modes": [],
        "receipt_set_class": "NONE",
        "none_defers_to_v109_and_query_local_certificate": True,
    },
)
_SEQUENCE_ADDITIONS = {
    "source_v154_sequence_id",
    "applicable_plan_receipt_mode",
    "applicable_plan_receipt_modes",
    "abstract_plan_receipt_count_by_registered_mode",
    "actual_v109_receipt_count_by_registered_mode",
    "registered_plan_receipt_set_class",
    "registered_plan_receipt_set_totalized",
    "at_least_one_registered_plan_mode_exercised",
    "mixed_registered_plan_mode_sequence",
    "empty_registered_plan_mode_set_is_failure",
    "none_path_defers_to_v109_and_query_local_certificate",
    "each_abstract_receipt_contains_one_concrete_plan_document",
    "multiple_registered_modes_mean_temporal_receipt_use_not_action_competition",
    "all_executed_actions_have_v109_receipts",
    "registered_plan_mode_set_changes_planning_or_execution",
    "registered_plan_mode_set_is_safety_authority",
}
_BUILDERS = {
    **previous._BUILDERS,  # noqa: SLF001
    PACKET_BATCHING_FAMILY: build_packet_batching_adapter_v134,
}


class ConstructionK7FifthFamilyTotalPlanReceiptSetIndependentVerifierV168Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FifthFamilyTotalPlanReceiptSetIndependentVerifierV168Error(
        message
    )


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
            domain,
            {name: value for name, value in document.items() if name != key},
        ),
        f"V168 {key} changed",
    )


def _frozen(raw, document, *, count, digest, key, identity, label):
    _require(
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(key) == identity,
        f"V168 frozen {label} changed",
    )


def _config():
    config = previous._config()  # noqa: SLF001
    packet = packet_batching_config_v134()
    config["families"][PACKET_BATCHING_FAMILY] = copy.deepcopy(
        packet["families"][PACKET_BATCHING_FAMILY]
    )
    config["families"][PACKET_BATCHING_FAMILY][
        "maximum_acquisition_labels"
    ] = 2_048
    return config


def _mode(plan):
    if plan.get("schema") == "acfqp.generic_projected_program_memo_plan.v115":
        return MEMOIZED_MODE
    if plan.get("planning_source") == "COMPILED_FACTOR_PROGRAM_FALLBACK":
        return DIRECT_MODE
    return None


def _sequence_verifier(family):
    namespace = dict(v157.__dict__)
    namespace.update(
        EXPECTED_EPISODES=EXPECTED_EPISODES,
        _fail=_fail,
        _require=_require,
    )
    factory = FunctionType(
        v157._v150_sequence_verifier.__code__,  # noqa: SLF001
        namespace,
        name=v157._v150_sequence_verifier.__name__,  # noqa: SLF001
    )
    return factory(family)


def _verify_sequence(sequence, candidate, rows, *, family, seed):
    _verify_id(
        sequence,
        "sequence_id",
        domains.CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN,
    )
    wrappers = [
        wrapper
        for episode in sequence["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
    ]
    counts = {mode: 0 for mode in REGISTERED_MODES}
    for wrapper in wrappers:
        _require(
            type(wrapper) is dict and type(wrapper.get("abstract_plan")) is dict,
            "V168 abstract plan receipt changed",
        )
        mode = _mode(wrapper["abstract_plan"])
        if mode is not None:
            counts[mode] += 1
    expected_counts = {
        DIRECT_MODE: sequence["direct_generic_factor_program_plan_count"],
        MEMOIZED_MODE: sequence[
            "v115_memoized_compiled_program_plan_receipt_count"
        ],
    }
    modes = [mode for mode in REGISTERED_MODES if counts[mode] > 0]
    receipt_set_class = (
        "NONE"
        if not modes
        else "DIRECT_ONLY"
        if modes == [DIRECT_MODE]
        else "MEMOIZED_ONLY"
        if modes == [MEMOIZED_MODE]
        else "MIXED"
    )
    actual = sequence["all_actual_legality_conditioned_execution_receipts"]
    actual_counts = {mode: 0 for mode in REGISTERED_MODES}
    for receipt in actual:
        wrapper = receipt.get("quotient_plan_receipt")
        if wrapper is not None:
            mode = _mode(wrapper["abstract_plan"])
            if mode is not None:
                actual_counts[mode] += 1
    _require(
        counts == expected_counts
        and sequence["applicable_plan_receipt_mode"]
        == (
            "NO_REGISTERED_COMPILED_PROGRAM_PLAN_RECEIPT"
            if receipt_set_class == "NONE"
            else "REGISTERED_COMPILED_PROGRAM_PLAN_MODE_SET"
        )
        and sequence["applicable_plan_receipt_modes"] == modes
        and sequence["registered_plan_receipt_set_class"] == receipt_set_class
        and sequence["abstract_plan_receipt_count_by_registered_mode"] == counts
        and sequence["actual_v109_receipt_count_by_registered_mode"]
        == actual_counts
        and sequence["registered_plan_receipt_set_totalized"] is True
        and sequence["at_least_one_registered_plan_mode_exercised"] is bool(modes)
        and sequence["mixed_registered_plan_mode_sequence"] is (
            receipt_set_class == "MIXED"
        )
        and sequence["empty_registered_plan_mode_set_is_failure"] is False
        and sequence["none_path_defers_to_v109_and_query_local_certificate"] is (
            receipt_set_class == "NONE"
        )
        and sequence[
            "each_abstract_receipt_contains_one_concrete_plan_document"
        ]
        is True
        and sequence[
            "multiple_registered_modes_mean_temporal_receipt_use_not_action_competition"
        ]
        is True
        and sequence["all_executed_actions_have_v109_receipts"] is True
        and sequence["registered_plan_mode_set_changes_planning_or_execution"]
        is False
        and sequence["registered_plan_mode_set_is_safety_authority"] is False
        and len(actual)
        == sequence["actual_legality_conditioned_execution_receipt_count"]
        == sequence["execution_step_count"]
        and all(
            receipt.get("schema")
            == "acfqp.generic_dependency_revalidated_execution_receipt.v109"
            and receipt.get("receipt_is_observation_not_safety_authority") is True
            and receipt.get("query_local_exact_overlay_remains_only_safety_authority")
            is True
            for receipt in actual
        ),
        "V168 plan receipt set annotation changed",
    )
    normalized_v154 = {
        key: copy.deepcopy(value)
        for key, value in sequence.items()
        if key not in _SEQUENCE_ADDITIONS and key != "sequence_id"
    }
    normalized_v154["schema"] = "acfqp.certified_memoized_planner_sequence.v154"
    normalized_v154["sequence_id"] = sequence["source_v154_sequence_id"]
    _verify_id(
        normalized_v154,
        "sequence_id",
        domains_v154.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN,
    )
    memoized = 0
    for episode in normalized_v154["episodes"]:
        for wrapper in episode["abstract_plan_receipts"]:
            if (
                wrapper["abstract_plan"].get("schema")
                == "acfqp.generic_projected_program_memo_plan.v115"
            ):
                v157._verify_v115_plan(wrapper["abstract_plan"])  # noqa: SLF001
                memoized += 1
    _require(
        memoized == counts[MEMOIZED_MODE]
        and normalized_v154[
            "v115_memoized_compiled_program_plan_receipts_consumed"
        ]
        is (memoized > 0),
        "V168 memoized receipt inventory changed",
    )
    normalized_v150 = {
        key: copy.deepcopy(value)
        for key, value in normalized_v154.items()
        if key not in v157._V154_SEQUENCE_ADDITIONS and key != "sequence_id"  # noqa: SLF001
    }
    normalized_v150["schema"] = "acfqp.certified_planner_abstention_sequence.v150"
    normalized_v150["sequence_id"] = _content_id(
        domains_v150.CONSTRUCTION_K7_SEQUENCE_V150_DOMAIN, normalized_v150
    )
    verified = _sequence_verifier(family)(
        normalized_v150, candidate, rows, family=family, seed=seed
    )
    return verified, tuple(modes), receipt_set_class


def _verify_occurrence(args):
    row, bank, bank_raw, bank_verification_raw, classifier = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row.get("schema")
        == "acfqp.fifth_family_total_plan_receipt_set_occurrence.v168"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES,
        "V168 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN)
    config = _config()
    adapter = _BUILDERS[family](seed, config)
    prepared = previous._prepare(  # noqa: SLF001
        adapter, classifier["selected_expression"]
    )
    prior_doc = row["progressive_prior_acquisition"]
    strict_doc = row["progressive_strict_acquisition"]
    maximum = max(
        prior_doc["ground_support_labels"], strict_doc["ground_support_labels"]
    )
    stream = previous._query_stream(adapter, prepared)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(maximum))
    prior_candidate, prior_rows = previous.v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        replication._normalized_acquisition(  # noqa: SLF001
            prior_doc, prepared, classifier
        ),
        adapter,
        bank,
        batches,
        enabled=True,
        config=config,
    )
    strict_candidate, strict_rows = previous.v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        replication._normalized_acquisition(  # noqa: SLF001
            strict_doc, prepared, classifier
        ),
        adapter,
        bank,
        batches,
        enabled=False,
        config=config,
    )
    prior_verified, prior_modes, prior_class = _verify_sequence(
        row["progressive_prior_sequence"],
        prior_candidate,
        prior_rows,
        family=family,
        seed=seed,
    )
    strict_verified, strict_modes, strict_class = _verify_sequence(
        row["progressive_strict_sequence"],
        strict_candidate,
        strict_rows,
        family=family,
        seed=seed,
    )
    legacy = acquire_matched_anonymous_relational_factor_bank_arms_v148(
        adapter, bank_raw, bank_verification_raw, config
    )["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    legacy_summary = {
        key: legacy[key]
        for key in (
            "acquisition_id",
            "ground_support_labels",
            "raw_transition_sha256",
            "first_accepting_observation_label",
        )
    }
    guard_reduction = (
        legacy["ground_support_labels"] - prior_doc["ground_support_labels"]
    )
    factor_reduction = (
        strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    )
    sequences = (
        row["progressive_prior_sequence"],
        row["progressive_strict_sequence"],
    )
    accounting = {
        "progressive_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "progressive_strict_acquisition_labels": strict_doc["ground_support_labels"],
        "legacy_path_first_prior_acquisition_labels": legacy[
            "ground_support_labels"
        ],
        "classifier_prefix_labels_included_in_acquisition": prior_doc[
            "classifier_prefix_observation_labels"
        ],
        "additional_classifier_only_target_labels": 0,
        "labels_avoided_by_progressive_query_policy_vs_legacy_path_first": guard_reduction,
        "labels_avoided_by_factor_prior_within_progressive_policy": factor_reduction,
        "progressive_prior_certificate_local_labels": sequences[0][
            "certificate_ground_support_labels_paid_once"
        ],
        "progressive_strict_certificate_local_labels": sequences[1][
            "certificate_ground_support_labels_paid_once"
        ],
        "progressive_prior_execution_steps": sequences[0]["execution_step_count"],
        "progressive_strict_execution_steps": sequences[1]["execution_step_count"],
        "progressive_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "progressive_strict_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "classifier_derivation_compute_events": classifier[
            "classifier_derivation_compute_events"
        ],
        "progressive_prior_planning_compute_events": sequences[0][
            "actual_new_abstract_planning_compute_events"
        ],
        "progressive_strict_planning_compute_events": sequences[1][
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    certified = prepared["certified_positive_switch"]
    exact_fallback = (
        prior_doc["source_v148_acquisition_id"] == legacy["acquisition_id"]
        and prior_doc["ground_support_labels"] == legacy["ground_support_labels"]
        and prior_doc["raw_transition_sha256"] == legacy["raw_transition_sha256"]
    )
    gate = {
        "fresh_target_identity": True,
        "classifier_receipt_frozen_before_target_outcomes": classifier[
            "fresh_v161_target_outcomes_accessed"
        ]
        is False,
        "no_named_initial_or_catalogue_support_primitive": all(
            document["no_named_initial_or_catalogue_support_primitive"] is True
            for document in (prior_doc, strict_doc)
        ),
        "decision_before_full_initial_action_frontier": all(
            document["full_initial_action_frontier_required_for_decision"] is False
            for document in (prior_doc, strict_doc)
        ),
        "classifier_uses_only_paid_target_raw_prefix": all(
            document["classifier_accessed_only_its_paid_target_raw_prefix"] is True
            and document[
                "classifier_prefix_labels_are_included_in_ground_support_labels"
            ]
            is True
            for document in (prior_doc, strict_doc)
        ),
        "query_policy_noninferior_to_legacy_path_first": guard_reduction >= 0,
        "factor_prior_noninferior_within_same_progressive_policy": factor_reduction
        >= 0,
        "matched_acquisition_completed_within_cap": all(
            0
            < document["ground_support_labels"]
            <= config["families"][family]["maximum_acquisition_labels"]
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
            for sequence in sequences
            for episode in sequence["episodes"]
        ),
        "planner_consumes_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in sequences
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in sequences
        ),
        "query_local_overlay_not_promoted_to_global_dynamics": all(
            sequence["source_partial_program_mutated_after_certificate_failure"]
            is False
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in sequences
        ),
        "all_executed_actions_have_v109_receipts": all(
            sequence["all_executed_actions_have_v109_receipts"]
            for sequence in sequences
        ),
        "exact_signature_registry_not_consulted": all(
            document["exact_signature_registry_consulted"] is False
            for document in (prior_doc, strict_doc)
        ),
        "raw_prefix_query_decision_matches_paid_evidence": (
            prior_doc["query_policy_decision"]
            == strict_doc["query_policy_decision"]
            == ("RELATION_COVERAGE" if certified else "PATH_FIRST_SAFE_FALLBACK")
        ),
        "certified_switch_requires_classifier_and_paid_relation_witness": (
            not certified
            or all(
                document["classifier_decision"] == "RELATION_COVERAGE"
                and document["paid_prefix_relation_candidate_count"] > 0
                for document in (prior_doc, strict_doc)
            )
        ),
        "query_policy_noninferior_to_exact_path_first": guard_reduction >= 0,
        "certified_switch_is_noninferior_when_exercised": (
            guard_reduction >= 0 if certified else True
        ),
        "exact_fallback_has_zero_regression": (
            guard_reduction == 0 and exact_fallback if not certified else True
        ),
        "factor_prior_noninferior_within_same_query_policy": factor_reduction >= 0,
        "v164_replication_identity_preserved": True,
        "v165_nonidentifiability_boundary_preserved": True,
        "profitability_classifier_not_issued": True,
        "registered_plan_receipt_set_totalized_both_arms": all(
            sequence["registered_plan_receipt_set_totalized"] is True
            for sequence in sequences
        ),
        "none_receipt_set_is_nonfailure_v109_certificate_fallback": all(
            sequence["empty_registered_plan_mode_set_is_failure"] is False
            and (
                sequence["registered_plan_receipt_set_class"] != "NONE"
                or sequence[
                    "none_path_defers_to_v109_and_query_local_certificate"
                ]
                is True
            )
            for sequence in sequences
        ),
        "mixed_plan_mode_sequence_is_temporal_not_action_competition": all(
            sequence[
                "multiple_registered_modes_mean_temporal_receipt_use_not_action_competition"
            ]
            is True
            for sequence in sequences
        ),
        "every_abstract_receipt_contains_one_concrete_plan": all(
            sequence["each_abstract_receipt_contains_one_concrete_plan_document"]
            is True
            for sequence in sequences
        ),
        "plan_mode_set_is_not_safety_authority": all(
            sequence["registered_plan_mode_set_is_safety_authority"] is False
            for sequence in sequences
        ),
        "v166_failed_identity_preserved": True,
        "v166_same_identity_not_rerun": True,
    }
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        "schema": "acfqp.fifth_family_total_plan_receipt_set_occurrence.v168",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(EXPECTED_EPISODES),
        "classifier_receipt_id": previous.CLASSIFIER_RECEIPT_ID,
        "v146_factor_bank_id": prior_doc["v146_factor_bank_id"],
        "v146_independent_verification_id": prior_doc[
            "v146_independent_verification_id"
        ],
        "progressive_prior_acquisition": prior_doc,
        "progressive_strict_acquisition": strict_doc,
        "progressive_prior_sequence": sequences[0],
        "progressive_strict_sequence": sequences[1],
        "legacy_path_first_prior_summary": legacy_summary,
        "applicable_plan_receipt_mode": (
            "REGISTERED_COMPILED_PROGRAM_PLAN_MODE_SET"
        ),
        "accounting": accounting,
        "query_policy_sample_reduction_vs_legacy_path_first": guard_reduction,
        "factor_prior_sample_reduction_within_progressive_policy": factor_reduction,
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "frozen_v164_campaign_id": V164_CAMPAIGN_ID,
        "frozen_v164_verification_id": V164_VERIFICATION_ID,
        "frozen_v165_identifiability_audit_id": V165_AUDIT_ID,
        "frozen_v165_independent_verification_id": V165_VERIFICATION_ID,
        "registered_gate": gate,
        "certified_positive_switch": certified,
        "exact_path_first_fallback": not certified,
        "profitability_classifier_issued": False,
        "sample_tax_claim_scope": (
            "ONLY_THIS_PREREGISTERED_V168_FIVE_FAMILY_COHORT"
        ),
        "failed_v166_attempt_id": V166_FAILURE_ID,
        "registered_plan_mode_sets": [list(prior_modes), list(strict_modes)],
        "registered_plan_receipt_set_classes": [prior_class, strict_class],
        "mixed_registered_plan_mode_sequence_observed": any(
            sequence["mixed_registered_plan_mode_sequence"]
            for sequence in sequences
        ),
        "plan_mode_set_annotation_changes_planner_or_execution": False,
    }
    expected = {
        **payload,
        "occurrence_id": _content_id(
            domains.CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN, payload
        ),
    }
    _require(row == expected, "V168 occurrence evidence changed")
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "certified_positive_switch": certified,
        "query_policy_labels_avoided": guard_reduction,
        "factor_prior_labels_avoided": factor_reduction,
        "plan_mode_sets": [list(prior_modes), list(strict_modes)],
        "plan_receipt_set_classes": [prior_class, strict_class],
        "prior_sequence": prior_verified,
        "strict_sequence": strict_verified,
        "accounting": accounting,
        "registered_gate": gate,
    }


def freeze_fifth_family_total_plan_receipt_set_verification_v168(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v167_campaign_raw: bytes,
    v167_verification_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    classifier = loads_canonical_json(classifier_receipt_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    v167_campaign = loads_canonical_json(v167_campaign_raw)
    v167_verification = loads_canonical_json(v167_verification_raw)
    _frozen(
        campaign_raw,
        campaign,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        key="campaign_id",
        identity=CAMPAIGN_ID,
        label="campaign",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V168_DOMAIN)
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
        domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V168_DOMAIN,
    )
    _frozen(
        v167_campaign_raw,
        v167_campaign,
        count=V167_CAMPAIGN_BYTE_COUNT,
        digest=V167_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V167_CAMPAIGN_ID,
        label="V167 campaign",
    )
    _frozen(
        v167_verification_raw,
        v167_verification,
        count=V167_VERIFICATION_BYTE_COUNT,
        digest=V167_VERIFICATION_SHA256,
        key="verification_id",
        identity=V167_VERIFICATION_ID,
        label="V167 verification",
    )
    _require(
        v167_campaign["registered_gate"]["passed"] is True
        and v167_verification[
            "fourth_family_factor_prior_sample_tax_transfer_independently_verified"
        ]
        is True
        and registration["frozen_v167_campaign"]["campaign_id"]
        == V167_CAMPAIGN_ID
        and registration["frozen_v167_independent_verification"][
            "verification_id"
        ]
        == V167_VERIFICATION_ID
        and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V168 predecessor/preregistration binding changed",
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
        and classifier[
            "query_policy_classifier_is_model_planning_or_certificate_authority"
        ]
        is False,
        "V168 classifier boundary changed",
    )
    _require(
        canonical_json_bytes(bank) == bank_raw
        and bank.get("bank_id") == previous.v151.BANK_ID
        and len(bank_raw) == previous.v151.previous.base.BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest()
        == previous.v151.previous.base.BANK_SHA256,
        "V168 factor bank changed",
    )
    _require(
        canonical_json_bytes(bank_verification) == bank_verification_raw
        and bank_verification.get("verification_id")
        == previous.v151.BANK_VERIFICATION_ID
        and len(bank_verification_raw)
        == previous.v151.previous.base.BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest()
        == previous.v151.previous.base.BANK_VERIFICATION_SHA256,
        "V168 factor bank verification changed",
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(
            len(raw) == fact["byte_count"]
            and hashlib.sha256(raw).hexdigest() == fact["sha256"],
            "V168 source closure changed",
        )
    _require(
        registration["target_occurrences"]
        == [
            {"family": family, "seed": seed}
            for family, seed in EXPECTED_OCCURRENCES
        ]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["required_target_occurrence_count"] == 2
        and all(registration["registered_gate"].values()),
        "V168 preregistered target contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(
            executor.map(
                _verify_occurrence,
                (
                    (row, bank, bank_raw, bank_verification_raw, classifier)
                    for row in campaign["target_occurrences"]
                ),
            )
        )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V168 occurrence inventory changed",
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
        total_query_policy_labels_avoided_vs_exact_path_first=sum(guards),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(factors),
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    gate = {
        "required_fresh_packet_occurrence_count": 2,
        "passed_fresh_packet_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "every_fresh_target_is_packet_batching": all(
            row["family"] == PACKET_BATCHING_FAMILY for row in rows
        ),
        "frozen_v167_campaign_preserved": True,
        "v166_frozen_failure_preserved": all(
            row["registered_gate"]["v166_failed_identity_preserved"] for row in rows
        ),
        "v166_failed_targets_not_reused": True,
        "plan_receipt_set_totalized_everywhere": all(
            receipt_class in {"DIRECT_ONLY", "MEMOIZED_ONLY", "MIXED", "NONE"}
            for row in rows
            for receipt_class in row["plan_receipt_set_classes"]
        ),
        "none_receipt_set_is_admissible_without_authority_change": all(
            row["registered_gate"][
                "none_receipt_set_is_nonfailure_v109_certificate_fallback"
            ]
            for row in rows
        ),
        "all_executed_actions_have_v109_receipts": all(
            row["registered_gate"]["all_executed_actions_have_v109_receipts"]
            for row in rows
        ),
        "mixed_plan_mode_sequences_admitted_without_authority_change": all(
            row["registered_gate"]["plan_mode_set_is_not_safety_authority"]
            for row in rows
        ),
        "fresh_packet_query_policy_noninferior": all(value >= 0 for value in guards),
        "fresh_packet_factor_prior_noninferior": all(value >= 0 for value in factors),
        "fresh_packet_receding_plans_succeed": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "fresh_packet_certificate_failure_only_local_ground_distinctions": all(
            row["registered_gate"][
                "certificate_failure_only_local_ground_distinctions"
            ]
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == 2
        and gate["passed_fresh_packet_occurrence_count"] == 2
        and all(value for value in gate.values() if type(value) is bool)
    )
    histogram = {
        name: sum(
            receipt_class == name
            for row in rows
            for receipt_class in row["plan_receipt_set_classes"]
        )
        for name in ("DIRECT_ONLY", "MEMOIZED_ONLY", "MIXED", "NONE")
    }
    payload = {
        "schema": "acfqp.fifth_family_total_plan_receipt_set_campaign.v168",
        "preregistration_id": PREREGISTRATION_ID,
        "frozen_v167_campaign": {
            "campaign_id": V167_CAMPAIGN_ID,
            "byte_count": V167_CAMPAIGN_BYTE_COUNT,
            "sha256": V167_CAMPAIGN_SHA256,
            "registered_plan_mode_sequence_histogram": v167_campaign[
                "registered_plan_mode_sequence_histogram"
            ],
        },
        "target_occurrences": campaign["target_occurrences"],
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "fresh_packet_accounting": accounting,
        "failed_v166_attempt_id": V166_FAILURE_ID,
        "fresh_packet_registered_plan_receipt_set_histogram": histogram,
        "registered_gate": gate,
        "fifth_family_factor_prior_sample_tax_transfer_verified": gate["passed"],
        "v166_failure_preserved_not_reclassified": True,
        "plan_mode_set_annotation_changes_planner_or_execution": False,
        "mixed_and_none_branches_are_semantic_totalization_not_observed_frequency_claim": True,
        "sample_tax_claim_scope": (
            "V167_FOUR_FAMILY_EVIDENCE_PLUS_THIS_PREREGISTERED_V168_PACKET_COHORT"
        ),
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
            domains.CONSTRUCTION_K7_CAMPAIGN_V168_DOMAIN, payload
        ),
    }
    _require(campaign == expected_campaign, "V168 aggregate campaign changed")
    verification_payload = {
        "schema": "acfqp.fifth_family_total_plan_receipt_set_verification.v168",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "failed_v166_attempt_id": V166_FAILURE_ID,
        "verified_occurrences": list(rows),
        "verified_fresh_packet_accounting": accounting,
        "verified_fresh_packet_plan_receipt_set_histogram": histogram,
        "verified_total_receipt_set_truth_table": list(RECEIPT_SET_TRUTH_TABLE),
        "producer_free_acquisition_candidate_sequence_and_v109_reconstruction": True,
        "frozen_v167_campaign_and_verification_preserved": True,
        "fifth_family_factor_prior_sample_tax_transfer_independently_verified": True,
        "direct_memoized_mixed_and_none_totalization_independently_verified": True,
        "query_policy_labels_avoided_vs_exact_path_first": sum(guards),
        "factor_prior_labels_avoided_within_same_query_policy": sum(factors),
        "sample_tax_claim_scope": campaign["sample_tax_claim_scope"],
        "query_policy_or_receipt_set_annotation_is_safety_authority": False,
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
            domains.CONSTRUCTION_K7_VERIFICATION_V168_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V168 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_fifth_family_total_plan_receipt_set_verification_v168",
)

"""Frozen protocol for the matched 2048 decision-point signature pilot."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
import re
from typing import Any, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.decision_point_signature_2048_pilot_v2 import (
    AUGMENTED_PREFIX_DIMENSION_V2,
    DECISION_PREFIX_ACTION_COUNT_V2,
    DECISION_PREFIX_ARMS_V2,
    DECISION_PREFIX_TAPE_ROOT_V2,
    DECISION_STATE_COUNT_V2,
    DECISION_STATE_LIBRARY_TAPE_ROOT_V2,
    FrozenDecisionStateV2,
    GENERATOR_ACTION_PRIORITY_V2,
    GENERATOR_MAX_DECISIONS_PER_EPISODE_V2,
    GENERATOR_MAX_EPISODES_V2,
    RAW_PREFIX_ARM_V2,
    RAW_PREFIX_DIMENSION_V2,
    ROTATED_PREFIX_ARM_V2,
    STRATEGIC_PREFIX_ARM_V2,
    build_decision_state_library_v2,
    validate_decision_state_library_v2,
)
from acfqp.science.early_strategic_signature_protocol_v1 import (
    EarlyStrategicSignatureProtocolV1Error,
    PARENT_U005_PROTOCOL_ID_V1,
    PARENT_U005_SOURCE_COMMIT_V1,
    _validate_candidate_models as _validate_u005_candidate_models,
    _validate_parent_manifest as _validate_u005_parent_manifest,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2,
)


DECISION_POINT_PROTOCOL_SCHEMA_V2 = (
    "acfqp.science.decision_point_signature_protocol.v2"
)
DECISION_POINT_PROTOCOL_DOMAIN_V2 = (
    "acfqp.science.decision-point-signature-protocol.v2"
)
PRIOR_RESULT_DOMAIN_V2 = "acfqp.science.early-strategic-signature-result.v1"
PILOT_EXECUTION_IDENTITY_V2 = (
    "acfqp-decision-point-signature-2048-pilot-v2-ordinal1-attempt1"
)
PRIOR_PROTOCOL_ID_V2 = (
    "d06e07f8f49ac4ef9957417befe766cd411ee928e574724199c849d4e8b5b6ee"
)
PRIOR_SOURCE_COMMIT_V2 = "bacb6218c3cd1b56a3190d2e86b6fbe44b6e0838"
PRIOR_EXECUTION_IDENTITY_V2 = (
    "acfqp-early-strategic-signature-2048-pilot-v1-ordinal2-attempt1"
)
PRIOR_RESULT_SCHEMA_V2 = (
    "acfqp.science.early_strategic_signature_evaluation.v1"
)
BOOTSTRAP_REPLICATES_V2 = 2_000
BOOTSTRAP_RANDOM_SEED_V2 = 180_002
LOGISTIC_L2_STRENGTH_V2 = 1.0
LABELED_POLICY_COUNT_PER_CLASS_V2 = 8
EXCLUDED_MIDDLE_POLICY_COUNT_V2 = 8
PILOT_ARMS_V2 = (
    "raw",
    "raw_plus_rotated_redundancy",
    "raw_plus_strategic",
)
RAW_ARM_V2, ROTATED_REDUNDANCY_ARM_V2, STRATEGIC_ARM_V2 = PILOT_ARMS_V2

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_CONTENT_ID = re.compile(r"^[0-9a-f]{64}$")
_LABEL_FIELDS = frozenset({"seed", "label", "mean_label_score"})


class DecisionPointSignatureProtocolV2Error(ValueError):
    """The parent, prior result, or frozen V2 design is not exact."""


def _fail(message: str) -> NoReturn:
    raise DecisionPointSignatureProtocolV2Error(message)


def _content_id(domain: str, value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\x00" + canonical_json_bytes(dict(value))
    ).hexdigest()


def _validate_prior_result(
    value: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    if type(value) is not dict:
        _fail("prior early-opening result must be a plain object")
    if (
        value.get("schema") != PRIOR_RESULT_SCHEMA_V2
        or value.get("protocol_id") != PRIOR_PROTOCOL_ID_V2
        or value.get("source_commit") != PRIOR_SOURCE_COMMIT_V2
        or value.get("pilot_execution_identity")
        != PRIOR_EXECUTION_IDENTITY_V2
        or value.get("PROVISIONAL_DESIGN_SIGNAL_GATE") != "FAIL"
        or value.get("provisional_design_signal") != "FAIL"
        or value.get("scientific_success") is not False
        or value.get("scientific_success_claimed") is not False
        or value.get("official_execution_allowed") is not False
        or value.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or value.get("SCALAR_CALIBRATION_GATE") != "NOT_RUN"
        or value.get("BREAK_EVEN_GATE") != "NOT_RUN"
        or value.get("OFFICIAL_EXECUTION_GATE") != "NOT_RUN"
    ):
        _fail("prior early-opening failure identity or claim boundary changed")
    raw_labels = value.get("policy_labels")
    if (
        type(raw_labels) is not list
        or len(raw_labels) != 24
        or any(type(row) is not dict for row in raw_labels)
    ):
        _fail("prior result must contain the exact 24 policy labels")
    labels = [dict(row) for row in raw_labels]
    expected_seeds = list(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2)
    if (
        any(set(row) != _LABEL_FIELDS for row in labels)
        or [row.get("seed") for row in labels] != expected_seeds
    ):
        _fail("prior policy label roster changed")
    for row in labels:
        score = row["mean_label_score"]
        if (
            type(row["seed"]) is not int
            or row["label"] not in {"NOVICE", "EXPERT", "EXCLUDED_MIDDLE"}
            or type(score) not in {int, float}
            or not math.isfinite(float(score))
            or float(score) < 0.0
        ):
            _fail("prior policy label row has a noncanonical value")
        row["mean_label_score"] = float(score)
    ordered = sorted(labels, key=lambda row: (row["mean_label_score"], row["seed"]))
    expected_by_seed: dict[int, str] = {}
    for index, row in enumerate(ordered):
        expected_by_seed[row["seed"]] = (
            "NOVICE"
            if index < LABELED_POLICY_COUNT_PER_CLASS_V2
            else "EXPERT"
            if index >= 24 - LABELED_POLICY_COUNT_PER_CLASS_V2
            else "EXCLUDED_MIDDLE"
        )
    if any(row["label"] != expected_by_seed[row["seed"]] for row in labels):
        _fail("prior labels no longer equal bottom-8/middle-8/top-8 score ranks")
    return labels, _content_id(PRIOR_RESULT_DOMAIN_V2, value)


def _validate_decision_states(value: Any) -> list[dict[str, Any]]:
    if (
        type(value) is not list
        or len(value) != DECISION_STATE_COUNT_V2
        or any(type(row) is not dict for row in value)
    ):
        _fail("decision state library must contain exactly 64 rows")
    frozen_rows: list[FrozenDecisionStateV2] = []
    for row in value:
        try:
            frozen = FrozenDecisionStateV2.from_document(row)
        except (TypeError, ValueError) as error:
            raise DecisionPointSignatureProtocolV2Error(str(error)) from error
        document = frozen.to_document()
        if document != row:
            _fail("decision state row is not in canonical field form")
        frozen_rows.append(frozen)
    try:
        frozen_rows = list(validate_decision_state_library_v2(frozen_rows))
    except (TypeError, ValueError) as error:
        raise DecisionPointSignatureProtocolV2Error(str(error)) from error
    states = [row.to_document() for row in frozen_rows]
    if [row.get("state_index") for row in states] != list(
        range(DECISION_STATE_COUNT_V2)
    ):
        _fail("decision state indices changed")
    boards = [tuple(row["board"]) for row in states]
    if len(set(boards)) != DECISION_STATE_COUNT_V2:
        _fail("decision state boards are not unique")
    return states


def _payload(
    *,
    parent_protocol_id: str,
    parent_manifest_id: str,
    prior_result_id: str,
    source_commit: str,
    candidate_models: Sequence[Mapping[str, Any]],
    policy_labels: Sequence[Mapping[str, Any]],
    decision_states: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": DECISION_POINT_PROTOCOL_SCHEMA_V2,
        "schema_version": "2.0.0",
        "pilot_kind": "MATCHED_RESOURCE_DECISION_POINT_EXPLORATORY_SIGNAL",
        "source_commit": source_commit,
        "pilot_execution_identity": PILOT_EXECUTION_IDENTITY_V2,
        "parent_u005_protocol_id": parent_protocol_id,
        "parent_u005_source_commit": PARENT_U005_SOURCE_COMMIT_V1,
        "parent_u005_manifest_id": parent_manifest_id,
        "prior_v1_protocol_id": PRIOR_PROTOCOL_ID_V2,
        "prior_v1_source_commit": PRIOR_SOURCE_COMMIT_V2,
        "prior_v1_execution_identity": PRIOR_EXECUTION_IDENTITY_V2,
        "prior_v1_result_id": prior_result_id,
        "redesign_lineage": {
            "prior_provisional_design_signal": "FAIL",
            "prior_failure_was_not_reinterpreted": True,
            "changed_estimand": True,
            "old_estimand": "FIRST_8_ACCEPTED_ACTIONS_AFTER_GAME_RESET",
            "new_estimand": "8_ACCEPTED_ACTIONS_AFTER_MATCHED_RESOURCE_DECISION_POINT",
            "representation_polarity_unchanged": True,
            "checkpoint_or_policy_subset_changed": False,
            "fresh_exploratory_identity": True,
        },
        "candidate_models": [dict(row) for row in candidate_models],
        "policy_labels": [dict(row) for row in policy_labels],
        "labeling_contract": {
            "source": "FROZEN_PRIOR_V1_64_FULL_GAME_MEAN_SCORES",
            "rank_order": "ASCENDING_MEAN_THEN_ASCENDING_POLICY_SEED",
            "novice": "BOTTOM_8",
            "expert": "TOP_8",
            "excluded": "MIDDLE_8",
            "policy_seed_is_statistical_cluster": True,
        },
        "decision_state_library_contract": {
            "generator_is_independent_of_candidate_policies": True,
            "tape_root": DECISION_STATE_LIBRARY_TAPE_ROOT_V2,
            "action_priority": list(GENERATOR_ACTION_PRIORITY_V2),
            "selection": "FIRST_ELIGIBLE_STATE_PER_GENERATOR_EPISODE",
            "maximum_generator_episodes": GENERATOR_MAX_EPISODES_V2,
            "maximum_decisions_per_episode": (
                GENERATOR_MAX_DECISIONS_PER_EPISODE_V2
            ),
            "state_count": DECISION_STATE_COUNT_V2,
            "unique_maximum_rank_minimum": 6,
            "unique_maximum_must_be_in_corner": True,
            "minimum_empty_cells": 8,
            "must_offer_both_corner_preserving_and_corner_breaking_actions": True,
            "one_state_at_most_per_generator_episode": True,
        },
        "decision_states": [dict(row) for row in decision_states],
        "prefix_tape_root": DECISION_PREFIX_TAPE_ROOT_V2,
        "prefix_action_count": DECISION_PREFIX_ACTION_COUNT_V2,
        "matched_start_state_and_spawn_tape_across_policies": True,
        "state_canonicalization_applied": False,
        "arms": list(PILOT_ARMS_V2),
        "feature_matrix_keys": {
            RAW_ARM_V2: RAW_PREFIX_ARM_V2,
            ROTATED_REDUNDANCY_ARM_V2: ROTATED_PREFIX_ARM_V2,
            STRATEGIC_ARM_V2: STRATEGIC_PREFIX_ARM_V2,
        },
        "feature_dimensions": {
            RAW_ARM_V2: RAW_PREFIX_DIMENSION_V2,
            ROTATED_REDUNDANCY_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
            STRATEGIC_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
        },
        "strategic_representation_contract": {
            "resource_quality_weights_refit": False,
            "resource_quality": "FROZEN_V1_EQUAL_CORE_RESOURCE_ORDERING",
            "regret": "LEGAL_ACTION_OPPORTUNITY_NORMALIZED_PRESPAWN_REGRET",
            "corner_opportunity_and_choice_recorded": True,
            "uses_only_observed_prefix_and_deterministic_prespawn_swipes": True,
        },
        "modeling_contract": {
            "cross_validation": "LEAVE_ONE_POLICY_OUT_GROUPED",
            "standardization": "TRAINING_FOLD_ONLY_Z_STANDARDIZATION",
            "zero_variance_training_coordinate_scale": 1,
            "classifier": "L2_LOGISTIC_REGRESSION",
            "optimizer": "SCIPY_OPTIMIZE_L_BFGS_B",
            "l2_strength": LOGISTIC_L2_STRENGTH_V2,
            "intercept_penalized": False,
            "training_label_weighting": "EQUAL_TOTAL_WEIGHT_PER_LABEL_WITHIN_FOLD",
            "heldout_policy_rows_never_enter_fit_or_standardization": True,
        },
        "bootstrap_contract": {
            "kind": "PAIRED_STRATIFIED_POLICY_CLUSTER_BOOTSTRAP",
            "replicates": BOOTSTRAP_REPLICATES_V2,
            "random_seed": BOOTSTRAP_RANDOM_SEED_V2,
            "confidence_interval": "PERCENTILE_95",
            "same_cluster_draws_for_all_arms": True,
        },
        "provisional_design_signal_contract": {
            "strategic_auroc_minimum": {"numerator": 4, "denominator": 5},
            "strategic_auroc_ci95_lower_minimum": {
                "numerator": 3,
                "denominator": 4,
            },
            "strategic_minus_each_control_auroc_ci95_lower_strictly_positive": True,
            "strategic_minus_each_control_brier_ci95_upper_nonpositive": True,
            "confirmatory_or_scientific_gate": False,
        },
        "claim_boundary": {
            "fresh_exploratory_pilot_only": True,
            "answers_first_8_actions_after_game_reset": False,
            "answers_8_actions_after_matched_resource_decision_point": True,
            "confirmatory_execution_authorized": False,
            "scientific_success_claimed": False,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
            "official_execution_allowed": False,
            "if_fail_stop_this_2048_signature_line": True,
        },
    }


def build_decision_point_protocol_v2(
    parent_protocol: Mapping[str, Any],
    parent_manifest: Mapping[str, Any],
    prior_result: Mapping[str, Any],
    source_commit: str,
) -> dict[str, Any]:
    """Freeze the new estimand before any decision-prefix outcomes exist."""

    if type(source_commit) is not str or _COMMIT.fullmatch(source_commit) is None:
        _fail("V2 source commit must be one lowercase full Git object ID")
    try:
        parent, candidates, manifest_id = _validate_u005_parent_manifest(
            parent_protocol, parent_manifest
        )
    except EarlyStrategicSignatureProtocolV1Error as error:
        raise DecisionPointSignatureProtocolV2Error(str(error)) from error
    labels, prior_result_id = _validate_prior_result(prior_result)
    state_documents = [
        state.to_document() for state in build_decision_state_library_v2()
    ]
    states = _validate_decision_states(state_documents)
    payload = _payload(
        parent_protocol_id=parent["protocol_id"],
        parent_manifest_id=manifest_id,
        prior_result_id=prior_result_id,
        source_commit=source_commit,
        candidate_models=candidates,
        policy_labels=labels,
        decision_states=states,
    )
    return {
        **payload,
        "protocol_id": _content_id(DECISION_POINT_PROTOCOL_DOMAIN_V2, payload),
    }


def validate_decision_point_protocol_v2(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the exact frozen V2 payload and all structural contracts."""

    if type(document) is not dict:
        _fail("V2 protocol must be a plain object")
    protocol_id = document.get("protocol_id")
    if type(protocol_id) is not str or _CONTENT_ID.fullmatch(protocol_id) is None:
        _fail("V2 protocol ID changed shape")
    payload = dict(document)
    del payload["protocol_id"]
    if _content_id(DECISION_POINT_PROTOCOL_DOMAIN_V2, payload) != protocol_id:
        _fail("V2 protocol identity is not replayable")
    source_commit = payload.get("source_commit")
    parent_protocol_id = payload.get("parent_u005_protocol_id")
    parent_manifest_id = payload.get("parent_u005_manifest_id")
    prior_result_id = payload.get("prior_v1_result_id")
    if (
        type(source_commit) is not str
        or _COMMIT.fullmatch(source_commit) is None
        or parent_protocol_id != PARENT_U005_PROTOCOL_ID_V1
        or type(parent_manifest_id) is not str
        or _CONTENT_ID.fullmatch(parent_manifest_id) is None
        or type(prior_result_id) is not str
        or _CONTENT_ID.fullmatch(prior_result_id) is None
    ):
        _fail("V2 parent, prior, or source binding changed")
    try:
        candidates = _validate_u005_candidate_models(payload.get("candidate_models"))
    except EarlyStrategicSignatureProtocolV1Error as error:
        raise DecisionPointSignatureProtocolV2Error(str(error)) from error
    labels = payload.get("policy_labels")
    if type(labels) is not list:
        _fail("V2 policy label registry changed")
    validated_labels, _unused = _validate_prior_result(
        {
            "schema": PRIOR_RESULT_SCHEMA_V2,
            "protocol_id": PRIOR_PROTOCOL_ID_V2,
            "source_commit": PRIOR_SOURCE_COMMIT_V2,
            "pilot_execution_identity": PRIOR_EXECUTION_IDENTITY_V2,
            "PROVISIONAL_DESIGN_SIGNAL_GATE": "FAIL",
            "provisional_design_signal": "FAIL",
            "scientific_success": False,
            "scientific_success_claimed": False,
            "official_execution_allowed": False,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
            "policy_labels": labels,
        }
    )
    states = _validate_decision_states(payload.get("decision_states"))
    expected = _payload(
        parent_protocol_id=parent_protocol_id,
        parent_manifest_id=parent_manifest_id,
        prior_result_id=prior_result_id,
        source_commit=source_commit,
        candidate_models=candidates,
        policy_labels=validated_labels,
        decision_states=states,
    )
    if payload != expected:
        _fail("V2 protocol differs from the frozen decision-point design")
    return dict(document)


__all__ = (
    "BOOTSTRAP_RANDOM_SEED_V2",
    "BOOTSTRAP_REPLICATES_V2",
    "DECISION_POINT_PROTOCOL_DOMAIN_V2",
    "DECISION_POINT_PROTOCOL_SCHEMA_V2",
    "DecisionPointSignatureProtocolV2Error",
    "EXCLUDED_MIDDLE_POLICY_COUNT_V2",
    "LABELED_POLICY_COUNT_PER_CLASS_V2",
    "LOGISTIC_L2_STRENGTH_V2",
    "PILOT_ARMS_V2",
    "PILOT_EXECUTION_IDENTITY_V2",
    "RAW_ARM_V2",
    "ROTATED_REDUNDANCY_ARM_V2",
    "STRATEGIC_ARM_V2",
    "PRIOR_EXECUTION_IDENTITY_V2",
    "PRIOR_PROTOCOL_ID_V2",
    "PRIOR_SOURCE_COMMIT_V2",
    "build_decision_point_protocol_v2",
    "validate_decision_point_protocol_v2",
)

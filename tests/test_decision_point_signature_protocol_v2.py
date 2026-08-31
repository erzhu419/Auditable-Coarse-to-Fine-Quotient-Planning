from __future__ import annotations

from copy import deepcopy

import pytest

from acfqp.domains import standard_2048
from acfqp.science import decision_point_signature_protocol_v2 as subject
from acfqp.science.decision_point_signature_2048_pilot_v2 import (
    DECISION_STATE_COUNT_V2,
    FrozenDecisionStateV2,
    is_eligible_decision_state_v2,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2,
    build_ratified_hybrid_confirmatory_protocol_v2,
    registered_hybrid_confirmatory_device_v2,
)


SOURCE_COMMIT = "2" * 40


def _parent_documents() -> tuple[dict, dict]:
    protocol = build_ratified_hybrid_confirmatory_protocol_v2(
        subject.PARENT_U005_SOURCE_COMMIT_V1
    )
    jobs = []
    for arm in HYBRID_CONFIRMATORY_ARMS_V2:
        for seed in HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2:
            jobs.append(
                {
                    "job_ordinal": len(jobs),
                    "arm": arm,
                    "seed": seed,
                    "execution_id": f"u005:{arm}:{seed}",
                    "worker": (
                        seed - HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2[0]
                    )
                    % 2,
                    "device": registered_hybrid_confirmatory_device_v2(seed),
                }
            )
    return protocol, {
        "schema": (
            "acfqp.science.latent_resource_hybrid_confirmatory_launch_manifest.v2"
        ),
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "job_count": 72,
        "worker_count": 2,
        "jobs": jobs,
    }


def _prior_result() -> dict:
    labels = []
    for index, seed in enumerate(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2):
        labels.append(
            {
                "seed": seed,
                "mean_label_score": float(1_000 + index),
                "label": (
                    "NOVICE"
                    if index < 8
                    else "EXPERT"
                    if index >= 16
                    else "EXCLUDED_MIDDLE"
                ),
            }
        )
    return {
        "schema": subject.PRIOR_RESULT_SCHEMA_V2,
        "protocol_id": subject.PRIOR_PROTOCOL_ID_V2,
        "source_commit": subject.PRIOR_SOURCE_COMMIT_V2,
        "pilot_execution_identity": subject.PRIOR_EXECUTION_IDENTITY_V2,
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


@pytest.fixture(scope="module")
def protocol() -> dict:
    parent_protocol, parent_manifest = _parent_documents()
    return subject.build_decision_point_protocol_v2(
        parent_protocol, parent_manifest, _prior_result(), SOURCE_COMMIT
    )


def test_protocol_freezes_new_estimand_without_reinterpreting_v1(
    protocol: dict,
) -> None:
    assert protocol["pilot_execution_identity"] == (
        "acfqp-decision-point-signature-2048-pilot-v2-ordinal1-attempt1"
    )
    assert protocol["source_commit"] == SOURCE_COMMIT
    assert protocol["redesign_lineage"]["prior_provisional_design_signal"] == "FAIL"
    assert protocol["redesign_lineage"]["prior_failure_was_not_reinterpreted"]
    assert protocol["redesign_lineage"]["changed_estimand"]
    assert not protocol["claim_boundary"]["answers_first_8_actions_after_game_reset"]
    assert protocol["claim_boundary"][
        "answers_8_actions_after_matched_resource_decision_point"
    ]
    assert not protocol["claim_boundary"]["confirmatory_execution_authorized"]
    assert protocol["claim_boundary"]["if_fail_stop_this_2048_signature_line"]
    assert subject.validate_decision_point_protocol_v2(protocol) == protocol


def test_protocol_closes_exact_policy_labels_and_eligible_state_library(
    protocol: dict,
) -> None:
    assert [row["seed"] for row in protocol["candidate_models"]] == list(
        HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2
    )
    assert [row["seed"] for row in protocol["policy_labels"]] == list(
        HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2
    )
    assert len(protocol["decision_states"]) == DECISION_STATE_COUNT_V2
    states = [
        FrozenDecisionStateV2.from_document(row)
        for row in protocol["decision_states"]
    ]
    assert all(
        is_eligible_decision_state_v2(
            standard_2048.state_from_board_v1(state.board)
        )
        for state in states
    )
    assert len({state.board for state in states}) == DECISION_STATE_COUNT_V2
    assert protocol["prefix_action_count"] == 8
    assert protocol["feature_dimensions"] == {
        "raw": 184,
        "raw_plus_rotated_redundancy": 248,
        "raw_plus_strategic": 248,
    }


def test_prior_label_reranking_and_protocol_tamper_are_rejected(
    protocol: dict,
) -> None:
    parent_protocol, parent_manifest = _parent_documents()
    prior = _prior_result()
    prior["policy_labels"][0]["label"] = "EXPERT"
    with pytest.raises(
        subject.DecisionPointSignatureProtocolV2Error,
        match="bottom-8",
    ):
        subject.build_decision_point_protocol_v2(
            parent_protocol, parent_manifest, prior, SOURCE_COMMIT
        )

    tampered = deepcopy(protocol)
    tampered["prefix_action_count"] = 7
    with pytest.raises(
        subject.DecisionPointSignatureProtocolV2Error,
        match="identity",
    ):
        subject.validate_decision_point_protocol_v2(tampered)

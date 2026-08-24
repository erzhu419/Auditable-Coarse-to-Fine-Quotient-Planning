from __future__ import annotations

from pathlib import Path

import pytest

from acfqp import construction_k7_open_world_campaign_v181r5 as campaign
from acfqp.open_world_transition_oracle_v181 import RawTransitionObservationV181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class _Certificate:
    certified = False
    selected_action = None
    strict_rank_decrease_proved = False
    planning_compute_events = 1

    def to_document(self):
        return {
            "certified": False,
            "strict_rank_decrease_proved": False,
            "persistent_model_bound_rank_cache_used": True,
            "planning_compute_events": 1,
        }


class _Planner:
    compiled_model_id = "a" * 64
    cached_subproblem_count = 0

    def certify(self, state):
        return _Certificate()


class _CoveredModel:
    compiled_model_id = "a" * 64
    coordinates = ()
    terminal_dependencies = ()

    def terminal(self, state):
        return tuple(state) == (0,)

    def predict_support(self, state, action):
        return ((0,),)

    def to_document(self):
        return {"compiled_model_id": self.compiled_model_id}


class _OneStepOracle:
    manifest_commitment = "b" * 64
    horizon = 3

    def initial_state(self, occurrence_index):
        return (1,)

    def legal_actions(self):
        return ((0,),)

    def query(self, **kwargs):
        return RawTransitionObservationV181(
            kwargs["occurrence_index"],
            kwargs["query_index"],
            tuple(kwargs["state"]),
            tuple(kwargs["action"]),
            (0,),
            True,
            "c" * 64,
        )


class _AcquisitionModel:
    total_enumeration_events = 7

    def __init__(self, archive_reference_count: int):
        self.archive_reference_count = archive_reference_count
        self.compiled_model_id = ("1" if archive_reference_count else "2") * 64

    def to_document(self):
        return {
            "compiled_model_id": self.compiled_model_id,
            "archive_reference_count": self.archive_reference_count,
            "archive_mdl_discount_used": False,
            "archive_reference_revalidated_on_current_rows": True,
        }


class _AcquisitionOracle:
    manifest_commitment = "8" * 64
    moduli = (5, 4, 3, 6, 2)
    action_width = 2

    def query(self, **kwargs):
        state = tuple(kwargs["state"])
        action = tuple(kwargs["action"])
        return RawTransitionObservationV181(
            kwargs["occurrence_index"],
            kwargs["query_index"],
            state,
            action,
            state,
            False,
            f"{kwargs['query_index']:064x}",
        )


def test_same_stop_formula_uses_only_revalidated_selected_prior_credit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(campaign, "MINIMUM_LABEL_COUNT", 16)
    monkeypatch.setattr(campaign, "MAXIMUM_LABEL_COUNT", 64)
    monkeypatch.setattr(campaign, "_covers", lambda model, row: True)
    monkeypatch.setattr(
        campaign,
        "compile_world_model_v181r5",
        lambda observations, **kwargs: _AcquisitionModel(
            int(bool(tuple(kwargs["archive"])))
        ),
    )
    progress = campaign.DurableProgressV181R5(tmp_path, "9" * 64)
    prior = campaign._acquire(
        _AcquisitionOracle(),
        manifest_index=0,
        arm=campaign.ARMS[0],
        archive=(("S", 0),),
        progress=progress,
    )
    strict = campaign._acquire(
        _AcquisitionOracle(),
        manifest_index=0,
        arm=campaign.ARMS[1],
        archive=(),
        progress=progress,
    )
    assert len(prior.observations) == 32
    assert prior.revalidated_prior_confirmation_credit == 1
    assert prior.effective_confirmation_count == 2
    assert len(strict.observations) == 48
    assert strict.revalidated_prior_confirmation_credit == 0
    assert strict.effective_confirmation_count == 2


def test_covered_certificate_fallback_row_does_not_recompile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        campaign,
        "compile_world_model_v181r5",
        lambda *args, **kwargs: pytest.fail("covered row must not recompile"),
    )
    progress = campaign.DurableProgressV181R5(tmp_path, "d" * 64)
    outcome = campaign._episode(
        _OneStepOracle(),
        manifest_index=0,
        occurrence_index=0,
        arm=campaign.ARMS[0],
        initial_model=_CoveredModel(),
        initial_planner_session=_Planner(),
        initial_training_rows=(),
        archive=(),
        progress=progress,
    )
    assert outcome.document["terminal_reached"] is True
    assert outcome.document["target_ground_label_count"] == 1
    assert outcome.document["model_recompilation_count"] == 0
    assert outcome.document["covered_recompilation_skip_count"] == 1
    assert outcome.document["every_local_ground_distinction_has_certificate_failure"] is True
    assert outcome.document["every_certificate_uses_persistent_model_bound_rank_cache"] is True
    assert progress.last_resolution["stage"] == "EPISODE_COMPLETE"


def test_progress_records_occurrence_and_finish_forward_bytes(tmp_path: Path) -> None:
    progress = campaign.DurableProgressV181R5(tmp_path, "e" * 64)
    first = progress.append(
        stage="EPISODE_COMPLETE",
        manifest_index=2,
        arm=campaign.ARMS[1],
        block_index=None,
        occurrence_index=11,
        decision_index=7,
        event_document={"episode_id": "f" * 64},
        row_ids=("f" * 64,),
    )
    raw = (tmp_path / "checkpoint-0000.json").read_bytes()
    assert raw == canonical_json_bytes(first)
    assert loads_canonical_json(raw)["occurrence_index"] == 11
    assert progress.last_resolution == {
        "stage": "EPISODE_COMPLETE",
        "manifest_index": 2,
        "arm": campaign.ARMS[1],
        "block_index": None,
        "occurrence_index": 11,
        "decision_index": 7,
    }


def test_progress_directory_must_begin_fresh(tmp_path: Path) -> None:
    (tmp_path / "checkpoint-0000.json").write_text("occupied")
    with pytest.raises(campaign.OpenWorldCampaignV181R5Error, match="begin fresh"):
        campaign.DurableProgressV181R5(tmp_path, "a" * 64)

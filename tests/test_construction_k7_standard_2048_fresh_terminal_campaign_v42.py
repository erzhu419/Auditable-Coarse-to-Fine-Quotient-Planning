from __future__ import annotations

from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_fresh_terminal_campaign_v42 as campaign


@pytest.fixture(scope="module")
def development_episode() -> dict:
    return campaign.build_development_fixture_episode_v42(decision_limit=1)


def test_v42_development_fixture_is_short_chained_and_nonformal(
    development_episode: dict,
) -> None:
    assert development_episode["execution_kind"] == "DEVELOPMENT_FIXTURE"
    assert development_episode["initial_decision_index"] == 0
    assert development_episode["decision_limit"] == 1
    assert development_episode["decision_count"] == 1
    assert development_episode["closure_reason"] == "DECISION_CAP_REACHED_WITH_ACTIVE_STATE"
    assert development_episode["decision_cap_fail_closed"] is True
    assert development_episode["additional_model_label_count"] == 0
    assert development_episode["crash_resume_or_cross_process_cache_persistence_claimed"] is False
    assert development_episode["in_process_subproof_cache_reused"] is False

    first = development_episode["steps"][0]
    assert first["decision_index"] == 0
    assert first["previous_step_id"] is None
    assert first["plan_certificate"]["previous_step_id"] is None
    assert first["selected_action"] == first["plan_certificate"]["selected_action"]
    assert first["additional_model_label_count"] == 0
    assert development_episode["last_transition_step_id"] == first["transition_step_id"]


def test_v42_development_fixture_cannot_consume_formal_board_or_seed() -> None:
    with pytest.raises(campaign.ConstructionK7Standard2048FreshTerminalCampaignV42Error):
        campaign._run_episode(  # noqa: SLF001
            (
                "DEVELOPMENT_FIXTURE",
                0,
                campaign.pre.INITIAL_BOARDS[0],
                campaign.DEVELOPMENT_FIXTURE_SEED,
                1,
            )
        )


def test_v42_formal_entrypoint_is_private_and_rejects_foreign_authority_before_execution() -> None:
    assert "run_standard_2048_fresh_terminal_campaign_v42" not in campaign.__all__
    with pytest.raises(campaign.ConstructionK7Standard2048FreshTerminalCampaignV42Error):
        campaign._run_standard_2048_fresh_terminal_campaign_v42(  # noqa: SLF001
            formal_authority=object()  # type: ignore[arg-type]
        )


def test_v42_direct_issue_or_private_issuer_forge_cannot_bypass_fixed_consumption(
    tmp_path: Path,
) -> None:
    with pytest.raises((OSError, ValueError)):
        campaign._issue_formal_execution_authority_v42(  # noqa: SLF001
            repository_root=tmp_path,
            worker_authorization_secret=b"x" * 32,
        )
    forged = campaign._FormalExecutionAuthorityV42(  # noqa: SLF001
        campaign._FORMAL_AUTHORITY_ISSUER,  # noqa: SLF001
        {},
        {},
        {},
        {},
        {},
        str(tmp_path),
    )
    with pytest.raises((OSError, ValueError)):
        campaign._run_standard_2048_fresh_terminal_campaign_v42(  # noqa: SLF001
            formal_authority=forged
        )


def test_v42_two_step_fixture_derives_real_cross_decision_cache_reuse() -> None:
    episode = campaign.build_development_fixture_episode_v42(decision_limit=2)
    assert episode["steps"][1]["previous_step_id"] == episode["steps"][0][
        "transition_step_id"
    ]
    assert episode["steps"][1]["pre_state"] == episode["steps"][0]["next_state"]
    assert episode["cross_decision_subproof_cache_hit_count"] > 0
    assert episode["in_process_subproof_cache_reused"] is True

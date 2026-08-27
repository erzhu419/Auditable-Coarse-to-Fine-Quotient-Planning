from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp import construction_k7_standard_2048_fresh_terminal_campaign_v42 as campaign
from acfqp import construction_k7_standard_2048_fresh_terminal_independent_verifier_v42 as verifier


@pytest.fixture(scope="module")
def development_episode() -> dict:
    return campaign.build_development_fixture_episode_v42(decision_limit=1)


def _resign_episode(episode: dict) -> dict:
    payload = {
        key: value
        for key, value in episode.items()
        if key != "fresh_terminal_episode_id"
    }
    return {
        **payload,
        "fresh_terminal_episode_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_EPISODE_V42_DOMAIN, payload
        ),
    }


def _resign_first_step(episode: dict) -> dict:
    step = episode["steps"][0]
    certificate = step["plan_certificate"]
    certificate_payload = {
        key: value for key, value in certificate.items() if key != "plan_certificate_id"
    }
    certificate = {
        **certificate_payload,
        "plan_certificate_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_PLAN_CERTIFICATE_V42_DOMAIN,
            certificate_payload,
        ),
    }
    step["plan_certificate"] = certificate
    step_payload = {
        key: value for key, value in step.items() if key != "transition_step_id"
    }
    step = {
        **step_payload,
        "transition_step_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_TRANSITION_STEP_V42_DOMAIN, step_payload
        ),
    }
    episode["steps"][0] = step
    episode["last_transition_step_id"] = step["transition_step_id"]
    return _resign_episode(episode)


def test_v42_independent_verifier_replays_development_chain(
    development_episode: dict,
) -> None:
    totals = verifier.verify_development_fixture_episode_independently_v42(
        development_episode,
        initial_board=campaign.DEVELOPMENT_FIXTURE_BOARD,
        seed=campaign.DEVELOPMENT_FIXTURE_SEED,
        decision_limit=1,
    )
    assert totals["decision_count"] == 1
    assert totals["terminal"] is False
    assert totals["rows"] > 0
    assert totals["outcomes"] > 0


def test_v42_independent_verifier_replays_multi_step_state_id_action_and_cache_joins() -> None:
    episode = campaign.build_development_fixture_episode_v42(decision_limit=2)
    totals = verifier.verify_development_fixture_episode_independently_v42(
        episode,
        initial_board=campaign.DEVELOPMENT_FIXTURE_BOARD,
        seed=campaign.DEVELOPMENT_FIXTURE_SEED,
        decision_limit=2,
    )
    first, second = episode["steps"]
    assert second["previous_step_id"] == first["transition_step_id"]
    assert second["pre_state"] == first["next_state"]
    assert second["selected_action"] == second["plan_certificate"]["selected_action"]
    assert totals["decision_count"] == 2
    assert totals["cross"] > 0
    assert episode["in_process_subproof_cache_reused"] is True


def test_v42_independent_verifier_rejects_resigned_midgame_start(
    development_episode: dict,
) -> None:
    forged = deepcopy(development_episode)
    forged["initial_state"] = {
        "board_ranks": [2, 0, 0, 1, 1, 3, 1, 0, 9, 3, 6, 7, 3, 5, 10, 3],
        "status": "ACTIVE",
    }
    forged = _resign_episode(forged)
    with pytest.raises(
        verifier.ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error,
        match="registered initial identity",
    ):
        verifier.verify_development_fixture_episode_independently_v42(
            forged,
            initial_board=campaign.DEVELOPMENT_FIXTURE_BOARD,
            seed=campaign.DEVELOPMENT_FIXTURE_SEED,
            decision_limit=1,
        )


def test_v42_independent_verifier_rejects_resigned_broken_first_link(
    development_episode: dict,
) -> None:
    forged = deepcopy(development_episode)
    forged["steps"][0]["previous_step_id"] = "f" * 64
    forged["steps"][0]["plan_certificate"]["previous_step_id"] = "f" * 64
    forged = _resign_first_step(forged)
    with pytest.raises(
        verifier.ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error,
        match="previous-step",
    ):
        verifier.verify_development_fixture_episode_independently_v42(
            forged,
            initial_board=campaign.DEVELOPMENT_FIXTURE_BOARD,
            seed=campaign.DEVELOPMENT_FIXTURE_SEED,
            decision_limit=1,
        )


def test_v42_independent_verifier_rejects_resigned_outcome_tape_tamper(
    development_episode: dict,
) -> None:
    forged = deepcopy(development_episode)
    forged["steps"][0]["outcome_tape_sha256"] = "0" * 64
    forged = _resign_first_step(forged)
    with pytest.raises(
        verifier.ConstructionK7Standard2048FreshTerminalIndependentVerifierV42Error,
        match="independent exact replay",
    ):
        verifier.verify_development_fixture_episode_independently_v42(
            forged,
            initial_board=campaign.DEVELOPMENT_FIXTURE_BOARD,
            seed=campaign.DEVELOPMENT_FIXTURE_SEED,
            decision_limit=1,
        )


def test_v42_verifier_import_does_not_import_producer_or_runner() -> None:
    root = Path(__file__).resolve().parents[1]
    code = """
import sys
from acfqp import construction_k7_standard_2048_fresh_terminal_independent_verifier_v42
forbidden = (
    'fresh_terminal_campaign_v42',
    'run_v42_standard_2048',
    'adaptive_expression_target_v35',
    'observation_proposed_program_v14',
    'expression_planner_v1',
)
bad = [name for name in sys.modules if any(token in name for token in forbidden)]
print('\\n'.join(bad))
raise SystemExit(bool(bad))
"""
    completed = subprocess.run(
        (sys.executable, "-c", code),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

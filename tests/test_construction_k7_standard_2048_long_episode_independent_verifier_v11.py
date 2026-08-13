from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_standard_2048_long_episode_independent_verifier_v11
    as verifier,
)
from acfqp import (
    construction_k7_standard_2048_long_episode_preregistration_v11 as pre,
)
from acfqp.domains.standard_2048 import state_from_board_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


def test_independent_verifier_imports_no_long_campaign_producer() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    imported = {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {
        "construction_k7_standard_2048_long_episode_campaign_v11",
        "construction_k7_standard_2048_factored_operator_campaign_v9",
        "construction_k7_standard_2048_meta_prior_route_campaign_v10",
        "construction_k7_standard_2048_fresh_board_support_world_model_v2",
    }
    assert not imported & forbidden
    assert "producer_imported" in source


def test_independent_binding_and_no_transfer_are_frozen() -> None:
    binding, bounds, lower, upper = verifier._operator_binding()
    assert binding["long_operator_binding_id"] == (
        "d20ecf7186d8b37337e6c36212ac0aa7c9ee7f2b7e07f885d0c7e1cead330535"
    )
    assert binding["offline_observation_count"] == 192
    assert binding["additional_model_acquisition_observation_count"] == 0
    assert lower == 0
    assert upper == verifier.Fraction(41, 128)
    assert bounds[16] == ((verifier.Fraction(1, 16),) * 2,) * 16
    no_transfer = verifier._no_transfer_document()
    assert no_transfer["long_no_transfer_id"] == (
        "403e4d31830fd38e2ec8dab72266b492989805f34042e02b5dee5b404ecd6578"
    )
    assert no_transfer["operator_accessed"] is False
    assert no_transfer["target_execution_performed"] is False


def test_first_h3_certificate_replays_registered_factored_counts() -> None:
    binding, bounds, lower, upper = verifier._operator_binding()
    state = state_from_board_v1(pre.PREREGISTERED_INITIAL_BOARDS[0])
    rows = verifier._LazyRows(bounds, binding["long_operator_binding_id"])
    bellman = verifier._PersistentBellman(lower, upper)
    certificate = verifier._certificate_document(
        state, binding["long_operator_binding_id"], rows, bellman
    )
    assert certificate["long_route_certificate_id"] == (
        "53450cbf36ffcecfd5cb13e87526b91fcbb3440ca688ce055146846487ebe467"
    )
    assert certificate["virtual_row_invocation_count"] == 1519
    assert certificate["closed_subproof_cache_hit_count"] == 37492
    assert certificate["serialized_state_action_row_count"] == 0


def test_independent_verifier_rejects_noncanonical_or_foreign_input_fast() -> None:
    with pytest.raises(
        verifier.ConstructionK7Standard2048LongEpisodeIndependentVerifierV11Error
    ):
        verifier.verify_standard_2048_long_episode_campaign_bytes_independently_v11(
            b"{ }"
        )
    with pytest.raises(
        verifier.ConstructionK7Standard2048LongEpisodeIndependentVerifierV11Error
    ):
        verifier.verify_standard_2048_long_episode_campaign_bytes_independently_v11(  # type: ignore[arg-type]
            "not-bytes"
        )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_LONG_2048_REPLAY") != "1",
    reason="full producer and independent H3 replay are intentionally explicit",
)
def test_real_campaign_bytes_pass_full_producer_free_replay() -> None:
    from acfqp import construction_k7_standard_2048_long_episode_campaign_v11

    campaign = (
        construction_k7_standard_2048_long_episode_campaign_v11
        .run_standard_2048_long_episode_campaign_v11()
    )
    verified = (
        verifier.verify_standard_2048_long_episode_campaign_bytes_independently_v11(
            campaign.canonical_bytes
        )
    )
    assert verified.campaign_id == verifier.EXPECTED_CAMPAIGN_ID
    document = verified.to_document()
    assert document["exact_semantic_replay_passed"] is True
    assert document["producer_imported"] is False
    assert document["full_standard_2048_game_verified"] is False
    tampered = loads_canonical_json(campaign.canonical_bytes)
    tampered["offline_transition_observation_count"] = 193
    with pytest.raises(
        verifier.ConstructionK7Standard2048LongEpisodeIndependentVerifierV11Error
    ):
        verifier.verify_standard_2048_long_episode_campaign_bytes_independently_v11(
            canonical_json_bytes(tampered)
        )

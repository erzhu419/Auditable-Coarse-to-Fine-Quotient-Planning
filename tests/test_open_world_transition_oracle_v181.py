from __future__ import annotations

from copy import deepcopy

import pytest

from acfqp.open_world_transition_oracle_v181 import (
    OpenWorldTransitionOracleV181Error,
    manifest_commitment_v181,
    reveal_opaque_transition_oracle_v181,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _manifest():
    return {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 99,
        "reveal_salt": "9" * 64,
        "state_width": 4,
        "action_width": 1,
        "horizon": 5,
        "moduli": [5, 4, 3, 6],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["A", 0]], ["K", 5]],
            ["S", 1],
            ["MOD", ["ADD", ["S", 2], ["W", 0]], ["K", 3]],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 0]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1]],
        "iid_initial_seed_root": "development-only",
    }


def test_oracle_exposes_only_raw_sampled_transition_surface() -> None:
    manifest = _manifest()
    raw = canonical_json_bytes(manifest)
    oracle = reveal_opaque_transition_oracle_v181(
        manifest_bytes=raw,
        expected_commitment=manifest_commitment_v181(manifest),
    )
    state = oracle.initial_state(0)
    observation = oracle.query(
        occurrence_index=0,
        query_index=0,
        state=state,
        action=(2,),
    )
    assert len(observation.state) == 4
    assert len(observation.successor) == 4
    assert type(observation.terminal) is bool
    assert set(observation.to_document()) == {
        "schema",
        "occurrence_index",
        "query_index",
        "state",
        "action",
        "successor",
        "terminal",
        "observation_id",
    }


def test_same_query_is_replayable_and_iid_occurrences_are_distinct() -> None:
    manifest = _manifest()
    oracle = reveal_opaque_transition_oracle_v181(
        manifest_bytes=canonical_json_bytes(manifest),
        expected_commitment=manifest_commitment_v181(manifest),
    )
    first = oracle.query(
        occurrence_index=1,
        query_index=7,
        state=(1, 2, 0, 3),
        action=(1,),
    )
    second = oracle.query(
        occurrence_index=1,
        query_index=7,
        state=(1, 2, 0, 3),
        action=(1,),
    )
    assert first == second
    assert oracle.initial_state(1) != oracle.initial_state(2)


def test_resigned_or_crossed_manifest_is_rejected() -> None:
    manifest = _manifest()
    commitment = manifest_commitment_v181(manifest)
    forged = deepcopy(manifest)
    forged["horizon"] = 6
    with pytest.raises(OpenWorldTransitionOracleV181Error):
        reveal_opaque_transition_oracle_v181(
            manifest_bytes=canonical_json_bytes(forged),
            expected_commitment=commitment,
        )

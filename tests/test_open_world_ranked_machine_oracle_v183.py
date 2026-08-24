from __future__ import annotations

from acfqp.open_world_ranked_machine_oracle_v183 import (
    ranked_machine_manifest_commitment_v183,
    reveal_ranked_machine_oracle_v183,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _manifest() -> dict:
    return {
        "schema": "acfqp.opaque_ranked_machine_manifest.v183",
        "manifest_index": 99,
        "reveal_salt": "1" * 64,
        "state_width": 2,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "coordinate_0_multiplier": 2,
        "coordinate_0_action_offset": 0,
        "coordinate_0_stochastic_support": [0, 1],
        "coordinate_1_decrement": 1,
        "terminal_coordinate": 1,
        "iid_initial_seed_root": "2" * 64,
    }


def test_v183_oracle_is_deterministic_and_schema_opaque() -> None:
    manifest = _manifest()
    commitment = ranked_machine_manifest_commitment_v183(manifest)
    oracle = reveal_ranked_machine_oracle_v183(
        manifest_bytes=canonical_json_bytes(manifest),
        expected_commitment=commitment,
    )
    first = oracle.query(
        occurrence_index=1,
        query_index=2,
        state=(3, 2),
        action=(1,),
    )
    second = oracle.query(
        occurrence_index=1,
        query_index=2,
        state=(3, 2),
        action=(1,),
    )
    assert first == second
    assert first.successor[0] in {7, 8}
    assert first.successor[1] == 1
    assert first.terminal is False

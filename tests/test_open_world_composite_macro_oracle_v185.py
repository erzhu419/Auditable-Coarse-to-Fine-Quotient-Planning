import pytest

from acfqp.open_world_composite_macro_oracle_v185 import (
    OpenWorldCompositeMacroOracleV185Error,
    composite_macro_manifest_commitment_v185,
    reveal_composite_macro_oracle_v185,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _manifest(*, ood: bool = False) -> dict:
    return {
        "schema": "acfqp.opaque_composite_macro_manifest.v185",
        "manifest_index": 1 if ood else 0,
        "role": "FRESH_INCOMPATIBLE_SCHEMA_OOD" if ood else "FRESH_SOURCE",
        "reveal_salt": "1" * 64,
        "state_width": 9 if ood else 8,
        "action_width": 2,
        "legal_actions": [[0, 0], [0, 1], [1, 0], [1, 1]],
        "horizon": 4,
        "state_permutation": [3, 0, 7, 2, 5, 1, 6, 4],
        "action_permutation": [1, 0],
        "noise_support": [0, 1],
        "noise_seed_root": "2" * 64,
        "initial_seed_root": "3" * 64,
        "ood_rule": "OPAQUE_COUNTER_INCREMENT_MOD_13" if ood else None,
    }


def test_v185_oracle_hides_permuted_queue_buffer_structure() -> None:
    document = _manifest()
    commitment = composite_macro_manifest_commitment_v185(document)
    oracle = reveal_composite_macro_oracle_v185(
        manifest_bytes=canonical_json_bytes(document),
        expected_commitment=commitment,
    )
    state = oracle.initial_state(0)
    assert len(state) == 8
    row = oracle.query(
        occurrence_index=0,
        query_index=0,
        state=state,
        action=(1, 0),
    )
    assert len(row.successor) == 8
    assert oracle.query_count == 1
    assert row.terminal is oracle.terminal(row.successor)


def test_v185_ood_schema_is_distinct_and_manifest_tampering_is_rejected() -> None:
    document = _manifest(ood=True)
    commitment = composite_macro_manifest_commitment_v185(document)
    oracle = reveal_composite_macro_oracle_v185(
        manifest_bytes=canonical_json_bytes(document),
        expected_commitment=commitment,
    )
    assert oracle.schema_signature()[0] == 9
    tampered = dict(document)
    tampered["horizon"] = 5
    with pytest.raises(OpenWorldCompositeMacroOracleV185Error):
        reveal_composite_macro_oracle_v185(
            manifest_bytes=canonical_json_bytes(tampered),
            expected_commitment=commitment,
        )

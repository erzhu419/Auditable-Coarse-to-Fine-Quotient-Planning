from acfqp.open_world_fair_expression_oracle_v184 import (
    fair_expression_manifest_commitment_v184,
    reveal_fair_expression_oracle_v184,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _manifest(width: int) -> dict:
    return {
        "schema": "acfqp.opaque_fair_expression_manifest.v184",
        "manifest_index": width,
        "role": "TEST",
        "reveal_salt": "1" * 64,
        "state_width": width,
        "action_width": 1,
        "legal_actions": [[0], [1]],
        "horizon": 3,
        "noise_support": [0, 1],
        "noise_seed_root": "2" * 64,
        "initial_seed_root": "3" * 64,
        "ood_extra_coordinate_rule": "INCREMENT_MOD_11" if width == 4 else None,
    }


def test_v184_oracle_is_partial_stochastic_and_opaque() -> None:
    manifest = _manifest(3)
    commitment = fair_expression_manifest_commitment_v184(manifest)
    left = reveal_fair_expression_oracle_v184(
        manifest_bytes=canonical_json_bytes(manifest),
        expected_commitment=commitment,
    )
    right = reveal_fair_expression_oracle_v184(
        manifest_bytes=canonical_json_bytes(manifest),
        expected_commitment=commitment,
    )
    state = (4, 3, 7)
    row_left = left.query(
        occurrence_index=184,
        query_index=5,
        state=state,
        action=(1,),
    )
    row_right = right.query(
        occurrence_index=184,
        query_index=5,
        state=state,
        action=(1,),
    )
    assert row_left == row_right
    assert row_left.successor[1] == 2
    assert row_left.successor[2] == 6
    assert row_left.successor[0] in {5, 6}
    assert left.query_count == 1


def test_v184_ood_schema_is_distinct_before_any_query() -> None:
    matched_manifest = _manifest(3)
    ood_manifest = _manifest(4)
    matched = reveal_fair_expression_oracle_v184(
        manifest_bytes=canonical_json_bytes(matched_manifest),
        expected_commitment=fair_expression_manifest_commitment_v184(matched_manifest),
    )
    ood = reveal_fair_expression_oracle_v184(
        manifest_bytes=canonical_json_bytes(ood_manifest),
        expected_commitment=fair_expression_manifest_commitment_v184(ood_manifest),
    )
    assert matched.schema_signature() != ood.schema_signature()
    assert matched.query_count == ood.query_count == 0

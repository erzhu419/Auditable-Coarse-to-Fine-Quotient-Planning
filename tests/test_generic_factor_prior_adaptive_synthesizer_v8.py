from __future__ import annotations

import hashlib

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_factor_prior_adaptive_synthesizer_v8 import (
    enumerate_anonymous_factor_candidates_v8,
    infer_factor_slots_v8,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _row(index: int, pre: tuple[int, int], action: FlatRawActionV4, post0: int):
    return FlatRawTransitionV4(
        0,
        index,
        pre,
        (0, 1),
        action,
        (post0, pre[1]),
        (0, 1),
        None,
    )


def test_v8_candidates_are_finite_anonymous_and_deterministic() -> None:
    first = enumerate_anonymous_factor_candidates_v8(2, 2)
    second = enumerate_anonymous_factor_candidates_v8(2, 2)
    assert first == second
    assert first
    assert len({row["candidate_id"] for row in first}) == len(first)
    assert all("semantic" not in canonical_json_bytes(row).decode() for row in first)


def test_v8_only_factor_signature_multiplier_changes_between_arms() -> None:
    catalogue = (FlatRawActionV4(0, (1, 20)), FlatRawActionV4(1, (2, 30)))
    rows = (
        _row(0, (0, 7), catalogue[0], 1),
        _row(1, (0, 7), catalogue[1], 2),
    )
    signature = hashlib.sha256(
        canonical_json_bytes(
            {
                "result_type": "INT",
                "normalized_expression": ["E05", ["S", "SELF"], ["A", 0]],
            }
        )
    ).hexdigest()
    kwargs = dict(
        rows=rows,
        catalogue=catalogue,
        factor_slots={0: "INT"},
        prior_signature_sha256=frozenset((signature,)),
        prior_weight=64,
        posterior_numerator=4,
        posterior_denominator=5,
    )
    enabled = infer_factor_slots_v8(factor_prior_enabled=True, **kwargs)
    disabled = infer_factor_slots_v8(factor_prior_enabled=False, **kwargs)
    assert enabled["candidate_count"] == disabled["candidate_count"]
    assert enabled["observed_support_count"] == disabled["observed_support_count"]
    assert [row["survivor_count"] for row in enabled["selections"]] == [
        row["survivor_count"] for row in disabled["selections"]
    ]
    assert enabled["factor_prior_weight"] == 64
    assert disabled["factor_prior_weight"] == 1
    assert enabled["selections"][0]["selected_candidate"]["expression"] == [
        "E05",
        ["E00", 0],
        ["E01", 0],
    ]
    assert enabled["all_factor_slots_stopped"] is True
    assert disabled["all_factor_slots_stopped"] is False

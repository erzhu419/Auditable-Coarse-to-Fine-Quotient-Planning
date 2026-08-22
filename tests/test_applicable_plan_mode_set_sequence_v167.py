import copy

import pytest

from acfqp.applicable_plan_mode_set_sequence_v167 import (
    DIRECT_MODE,
    MEMOIZED_MODE,
    annotate_applicable_plan_mode_set_sequence_v167,
)


def _sequence(*, direct: int, memoized: int):
    plans = []
    for index in range(direct):
        plans.append(
            {
                "raw_state": [index],
                "abstract_plan": {
                    "schema": "acfqp.generic_legality_conditioned_quotient_plan.v106",
                    "planning_source": "COMPILED_FACTOR_PROGRAM_FALLBACK",
                },
            }
        )
    for index in range(memoized):
        plans.append(
            {
                "raw_state": [direct + index],
                "abstract_plan": {
                    "schema": "acfqp.generic_projected_program_memo_plan.v115",
                    "planning_source": "COMPILED_FACTOR_PROGRAM_MEMOIZED",
                },
            }
        )
    actual = [
        {
            "schema": "acfqp.generic_dependency_revalidated_execution_receipt.v109",
            "receipt_is_observation_not_safety_authority": True,
            "query_local_exact_overlay_remains_only_safety_authority": True,
            "quotient_plan_receipt": plans[0],
        }
    ]
    payload = {
        "schema": "acfqp.certified_memoized_planner_sequence.v154",
        "episodes": [{"abstract_plan_receipts": plans}],
        "direct_generic_factor_program_plan_count": direct,
        "v115_memoized_compiled_program_plan_receipt_count": memoized,
        "all_actual_legality_conditioned_execution_receipts": actual,
        "actual_legality_conditioned_execution_receipt_count": 1,
        "execution_step_count": 1,
    }
    from acfqp import construction_k7_domain_registry_extension_v154 as domains

    from acfqp.phase3e_ids import canonical_json_bytes
    import hashlib

    identity = hashlib.sha256(
        domains.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN.encode()
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return {**payload, "sequence_id": identity}


@pytest.mark.parametrize(
    ("direct", "memoized", "expected"),
    ((1, 0, [DIRECT_MODE]), (1, 1, [DIRECT_MODE, MEMOIZED_MODE])),
)
def test_v167_accepts_single_or_temporally_mixed_registered_mode_set(
    direct, memoized, expected
):
    document = annotate_applicable_plan_mode_set_sequence_v167(
        _sequence(direct=direct, memoized=memoized)
    )
    assert document["applicable_plan_receipt_modes"] == expected
    assert document["mixed_registered_plan_mode_sequence"] is (len(expected) > 1)
    assert document["registered_plan_mode_set_is_safety_authority"] is False
    assert document["all_executed_actions_have_v109_receipts"] is True


def test_v167_rejects_count_tamper_even_with_mixed_mode_set():
    source = _sequence(direct=1, memoized=1)
    source["direct_generic_factor_program_plan_count"] = 2
    with pytest.raises(ValueError, match="source V154 sequence changed"):
        annotate_applicable_plan_mode_set_sequence_v167(source)


def test_v167_rejects_missing_v109_execution_receipt():
    source = _sequence(direct=1, memoized=1)
    tampered = copy.deepcopy(source)
    tampered["all_actual_legality_conditioned_execution_receipts"] = []
    from acfqp import construction_k7_domain_registry_extension_v154 as domains
    from acfqp.phase3e_ids import canonical_json_bytes
    import hashlib

    payload = {key: value for key, value in tampered.items() if key != "sequence_id"}
    tampered["sequence_id"] = hashlib.sha256(
        domains.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN.encode()
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    with pytest.raises(ValueError, match="actual V109"):
        annotate_applicable_plan_mode_set_sequence_v167(tampered)

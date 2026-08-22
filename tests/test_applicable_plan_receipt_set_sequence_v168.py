import copy
import hashlib

import pytest

from acfqp import construction_k7_domain_registry_extension_v154 as domains_v154
from acfqp.applicable_plan_receipt_set_sequence_v168 import (
    DIRECT_MODE,
    DIRECT_ONLY,
    MEMOIZED_MODE,
    MEMOIZED_ONLY,
    MIXED,
    NONE,
    annotate_applicable_plan_receipt_set_sequence_v168,
)
from acfqp.phase3e_ids import canonical_json_bytes


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
    if not plans:
        plans.append(
            {
                "raw_state": [0],
                "abstract_plan": {
                    "schema": "acfqp.query_local_exact_overlay_plan.v1",
                    "planning_source": "QUERY_LOCAL_EXACT_CERTIFICATE_FALLBACK",
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
    identity = hashlib.sha256(
        domains_v154.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN.encode()
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return {**payload, "sequence_id": identity}


@pytest.mark.parametrize(
    ("direct", "memoized", "expected_modes", "expected_class"),
    (
        (1, 0, [DIRECT_MODE], DIRECT_ONLY),
        (0, 1, [MEMOIZED_MODE], MEMOIZED_ONLY),
        (1, 1, [DIRECT_MODE, MEMOIZED_MODE], MIXED),
        (0, 0, [], NONE),
    ),
)
def test_v168_totalizes_all_four_registered_receipt_set_classes(
    direct, memoized, expected_modes, expected_class
):
    document = annotate_applicable_plan_receipt_set_sequence_v168(
        _sequence(direct=direct, memoized=memoized)
    )
    assert document["applicable_plan_receipt_modes"] == expected_modes
    assert document["registered_plan_receipt_set_class"] == expected_class
    assert document["registered_plan_receipt_set_totalized"] is True
    assert document["empty_registered_plan_mode_set_is_failure"] is False
    assert document["none_path_defers_to_v109_and_query_local_certificate"] is (
        expected_class == NONE
    )
    assert document["all_executed_actions_have_v109_receipts"] is True
    assert document["registered_plan_mode_set_is_safety_authority"] is False


def test_v168_rejects_missing_v109_receipt_even_on_none_path():
    source = copy.deepcopy(_sequence(direct=0, memoized=0))
    source["all_actual_legality_conditioned_execution_receipts"] = []
    payload = {key: value for key, value in source.items() if key != "sequence_id"}
    source["sequence_id"] = hashlib.sha256(
        domains_v154.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN.encode()
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    with pytest.raises(ValueError, match="actual V109"):
        annotate_applicable_plan_receipt_set_sequence_v168(source)


def test_v168_rejects_registered_count_tamper():
    source = _sequence(direct=1, memoized=1)
    source["direct_generic_factor_program_plan_count"] = 2
    with pytest.raises(ValueError, match="source V154"):
        annotate_applicable_plan_receipt_set_sequence_v168(source)

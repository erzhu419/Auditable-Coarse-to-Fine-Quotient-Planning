import copy

import pytest

from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_abstract_execution_receipt_v103 import (
    build_abstract_execution_receipt_v103,
    verify_abstract_execution_receipt_v103,
)


def test_v103_receipt_binds_actual_action_to_admitted_abstract_proposal():
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(7,), partial_proposal=(7,), legal_action_keys=(7, 9)
    )
    receipt = build_abstract_execution_receipt_v103(
        decision_index=2,
        raw_state=(3, 4, 5),
        chosen_action_key=7,
        abstract_proposal=(7,),
        partial_proposal=(7,),
        legal_action_keys=(7, 9),
        shield_receipt=shield,
    )
    assert verify_abstract_execution_receipt_v103(receipt) == receipt
    assert receipt["chosen_action_matches_admitted_abstract_proposal"] is True
    assert receipt["receipt_is_observation_not_safety_authority"] is True


def test_v103_receipt_rejects_rehashed_semantic_mismatch():
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(7,), partial_proposal=(7,), legal_action_keys=(7, 9)
    )
    receipt = build_abstract_execution_receipt_v103(
        decision_index=0,
        raw_state=(1,),
        chosen_action_key=7,
        abstract_proposal=(7,),
        partial_proposal=(7,),
        legal_action_keys=(7, 9),
        shield_receipt=shield,
    )
    forged = copy.deepcopy(receipt)
    forged["chosen_action_matches_admitted_abstract_proposal"] = False
    with pytest.raises(Exception):
        verify_abstract_execution_receipt_v103(forged)


def test_v103_disagreement_receipt_cannot_claim_abstract_match():
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(9,), partial_proposal=(7,), legal_action_keys=(7, 9)
    )
    receipt = build_abstract_execution_receipt_v103(
        decision_index=0,
        raw_state=(1,),
        chosen_action_key=7,
        abstract_proposal=(9,),
        partial_proposal=(7,),
        legal_action_keys=(7, 9),
        shield_receipt=shield,
    )
    assert receipt["abstract_partial_exact_action_agreement"] is False
    assert receipt["chosen_action_matches_admitted_abstract_proposal"] is False

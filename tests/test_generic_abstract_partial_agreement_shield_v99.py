import copy

import pytest

from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    replay_abstract_action_order_shield_v99,
    shield_abstract_action_order_v99,
)


def test_v99_shield_admits_only_abstract_partial_agreement():
    agreed = shield_abstract_action_order_v99(
        abstract_proposal=(8,), partial_proposal=(8,), legal_action_keys=(0, 8, 2)
    )
    disagreed = shield_abstract_action_order_v99(
        abstract_proposal=(2,), partial_proposal=(8,), legal_action_keys=(0, 8, 2)
    )
    assert agreed["shielded_action_order"] == [8, 0, 2]
    assert agreed["abstract_proposal_admitted_to_action_order"] is True
    assert disagreed["shielded_action_order"] == [8, 0, 2]
    assert disagreed["abstract_disagreement_abstained"] is True
    assert disagreed[
        "abstract_proposal_can_precede_partial_without_agreement"
    ] is False
    assert replay_abstract_action_order_shield_v99(agreed) == agreed


def test_v99_shield_rejects_rehashed_claim_flip():
    receipt = shield_abstract_action_order_v99(
        abstract_proposal=(2,), partial_proposal=(8,), legal_action_keys=(0, 8, 2)
    )
    forged = copy.deepcopy(receipt)
    forged["abstract_proposal_admitted_to_action_order"] = True
    with pytest.raises(Exception):
        replay_abstract_action_order_shield_v99(forged)

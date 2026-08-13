from __future__ import annotations

from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as pre
from acfqp import construction_k7_standard_2048_adaptive_expression_target_v35 as target
from acfqp.phase3e_ids import content_id


def test_revealed_semantics_exactly_open_the_prior_commitment() -> None:
    payload = target.target_semantics_payload_v35()
    document = target.target_semantics_document_v35()
    assert target.verify_target_commitment_v35() == pre.TARGET_KERNEL_COMMITMENT_ID
    assert document["target_kernel_id"] == pre.TARGET_KERNEL_COMMITMENT_ID
    assert content_id(pre.FUTURE_DOMAINS["target"], payload) == document["target_kernel_id"]


def test_reveal_is_a_generic_expression_program_not_a_state_table() -> None:
    document = target.target_semantics_document_v35()
    assert document["spawn_rank_support"] == [1, 2]
    assert document["override_expression_ast"]["operator"] == "COUNT_EQ"
    assert document["override_relation"] == "LESS_THAN_OR_EQUAL"
    assert "state_action_probability_table" not in document

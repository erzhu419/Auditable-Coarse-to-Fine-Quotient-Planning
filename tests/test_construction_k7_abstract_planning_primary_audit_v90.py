import os

import pytest

from acfqp.construction_k7_abstract_planning_primary_audit_v90 import (
    AUDIT_ID,
    run_abstract_planning_primary_audit_v90,
)


def test_v90_audit_identity_is_frozen():
    assert AUDIT_ID == (
        "1470de5895af6fb5215bfc34c29aa14f14f49af375ba003665ebc008d555e503"
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_ABSTRACT_PRIMARY_V90") != "1",
    reason="explicit registered V90 deterministic audit",
)
def test_v90_registered_audit_closes_abstract_primary_gate():
    document = run_abstract_planning_primary_audit_v90().to_document()
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["proposal_mismatch_count"] == 0
    assert document["registered_gate"]["non_proposed_ground_action_query_count"] == 0
    assert document["multi_step_planning_primarily_in_abstract_model_verified"] is True
    assert document["official_scalar_cost"] is None

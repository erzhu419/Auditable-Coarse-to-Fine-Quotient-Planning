import pytest

from acfqp import construction_k7_source_model_acceptance_v91r3 as acceptance


def test_v91r3_frozen_acceptance_refuses_reconstruction():
    if acceptance.ACCEPTANCE_ID == "0" * 64:
        pytest.skip("V91r3 acceptance not frozen yet")
    with pytest.raises(
        acceptance.ConstructionK7SourceModelAcceptanceV91R3Error,
        match="same identity will not be rerun",
    ):
        acceptance.run_source_model_acceptance_v91r3(b"")

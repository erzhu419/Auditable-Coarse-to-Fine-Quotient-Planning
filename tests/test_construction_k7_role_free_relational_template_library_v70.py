import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V70_LIBRARY") != "1",
    reason="explicit V70 frozen role-free template library",
)
def test_v70_library_erases_source_column_and_token_identities():
    from acfqp.construction_k7_role_free_relational_template_library_v70 import (
        freeze_role_free_relational_template_library_v70,
        verify_role_free_relational_template_library_v70,
    )

    value = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    document = value.to_document()
    library = document["compiled_template_library"]
    assert library["role_free_template_count"] > 0
    assert document["raw_column_numbers_retained"] is False
    assert document["source_status_tokens_retained"] is False
    assert document["future_target_prediction_authority_present"] is False

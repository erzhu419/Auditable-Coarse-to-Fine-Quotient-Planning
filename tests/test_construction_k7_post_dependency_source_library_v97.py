import hashlib
from pathlib import Path

from acfqp import construction_k7_post_dependency_source_library_v97 as source


def test_v97_source_library_abstracts_structure_not_source_bindings():
    value = source.freeze_post_dependency_source_library_v97(
        Path(".tmp/exact-freeze/v96_persistent_multi_residual_campaign.json").read_bytes(),
        Path(".tmp/exact-freeze/v96_persistent_multi_residual_verification.json").read_bytes(),
    )
    document = value.to_document()
    assert value.source_library_artifact_id == source.SOURCE_LIBRARY_ARTIFACT_ID
    assert len(value.canonical_bytes) == source.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == source.EXPECTED_CANONICAL_SHA256
    assert document["source_occurrence_support_count"] == 2
    assert all(
        row["source_specific_bindings_not_transferred"] is True
        for row in document["source_occurrences"]
    )
    library = document["compiled_structure_library"]
    assert library["source_target_columns_transferred"] is False
    assert library["source_driver_columns_transferred"] is False
    assert library["source_thresholds_transferred"] is False
    assert library["source_leaf_values_transferred"] is False
    assert document["evidence_boundary"]["fresh_target_outcomes_observed"] is False
    assert document["official_execution_allowed"] is False

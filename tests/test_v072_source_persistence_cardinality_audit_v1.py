from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import v072_source_persistence_cardinality_audit_v1 as audit


def test_naive_source_snapshot_is_rejected_by_a_proven_gigabyte_lower_bound() -> None:
    result = audit.freeze_source_persistence_cardinality_audit_v1()
    assert result.source_snapshot_lower_bound_bytes == 1_053_818_880
    assert result.source_snapshot_upper_estimate_bytes == 5_620_367_360
    assert result.graph_family_snapshot_lower_bound_bytes == 3_741_057_024
    assert result.graph_family_snapshot_upper_estimate_bytes == 19_952_304_128
    assert (
        result.source_snapshot_lower_bound_bytes
        > result.deployment_cap_bytes
    )
    assert result.full_snapshot_deployable is False
    assert result.recommended_persistence == (
        "CONTENT_ADDRESSED_DETERMINISTIC_RECONSTRUCTION_RECIPE"
    )


def test_cardinality_audit_is_deterministic_nonauthorizing_and_content_addressed() -> None:
    first = audit.freeze_source_persistence_cardinality_audit_v1()
    second = audit.freeze_source_persistence_cardinality_audit_v1()
    assert first == second
    assert first.audit_id == second.audit_id
    document = first.to_document()
    assert document["raw_observation_ids_persisted"] is False
    assert document["new_observer_draws"] == 0
    assert document["official_execution_allowed"] is False
    assert len(document["audit_id"]) == 64
    with pytest.raises(ValueError, match="cardinality audit changed"):
        replace(first, full_snapshot_deployable=True)


def test_marginal_json_bound_counts_quotes_commas_and_hex_bytes() -> None:
    assert audit.CONTENT_ID_HEX_CHARACTERS == 64
    assert audit.CANONICAL_JSON_MARGINAL_BYTES_PER_ID == 67
    assert audit.PROVEN_MINIMUM_ID_OCCURRENCES == 3
    assert audit.CONSERVATIVE_UPPER_ID_OCCURRENCES == 16

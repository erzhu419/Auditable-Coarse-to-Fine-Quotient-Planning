from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_formalization_readiness_v180 as readiness
from acfqp import construction_k7_all_path_formalization_independent_verifier_v180 as verifier
from acfqp.phase3e_ids import canonical_json_bytes


def _values():
    return (
        contract.freeze_all_path_formalization_contract_v180(),
        readiness.freeze_all_path_formalization_readiness_v180(),
    )


def test_readiness_is_exhaustive_and_does_not_promote_historical_results() -> None:
    _, value = _values()
    document = value.to_document()
    assert document["terminal_code_count"] == 10
    assert document["prior_profile_formal_chain_implementation_count"] == 6
    assert document["current_v9_formal_chain_implementation_count"] == 2
    assert document["fresh_v180_observed_occurrence_count"] == 0
    assert document["fresh_v180_missing_occurrence_count"] == 10
    assert document["historical_summary_promoted_to_v180_evidence"] is False
    assert all(
        row["fresh_v180_observed_occurrence_present"] is False
        for row in document["terminal_rows"]
    )


def test_independent_verifier_rehashes_sources_and_keeps_gates_locked() -> None:
    contract_value, readiness_value = _values()
    result = verifier.verify_all_path_formalization_readiness_independently_v180(
        contract_bytes=contract_value.canonical_bytes,
        readiness_bytes=readiness_value.canonical_bytes,
    ).to_document()
    assert result["source_bytes_rehashed"] is True
    assert result["readiness_rows_reconstructed_without_producer_import"] is True
    assert result["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert result["official_execution_allowed"] is False


def test_retained_readiness_and_verification_bytes_are_exact() -> None:
    contract_value, readiness_value = _values()
    verified = verifier.verify_all_path_formalization_readiness_independently_v180(
        contract_bytes=contract_value.canonical_bytes,
        readiness_bytes=readiness_value.canonical_bytes,
    )
    root = Path(__file__).resolve().parents[1] / ".tmp" / "exact-freeze"
    assert (
        root / "v180_all_path_formalization_readiness.json"
    ).read_bytes() == readiness_value.canonical_bytes
    assert (
        root / "v180_all_path_formalization_readiness_verification.json"
    ).read_bytes() == verified.canonical_bytes


@pytest.mark.parametrize(
    ("row_index", "field", "value"),
    (
        (0, "fresh_v180_observed_occurrence_present", True),
        (1, "accounting_registry_version", "9.0.1"),
        (3, "complete_counter_record_work_vector_comparison_vector_chain_implemented", True),
    ),
)
def test_resigned_readiness_claims_are_rejected(
    row_index: int, field: str, value: object
) -> None:
    contract_value, readiness_value = _values()
    forged = deepcopy(readiness_value.to_document())
    forged["terminal_rows"][row_index][field] = value
    payload = {
        key: item
        for key, item in forged.items()
        if key != "formalization_readiness_audit_id"
    }
    from acfqp import construction_k7_domain_registry_extension_v180 as domains

    forged["formalization_readiness_audit_id"] = domains.extension_content_id_v180(
        domains.CONSTRUCTION_K7_READINESS_AUDIT_V180_DOMAIN,
        payload,
    )
    with pytest.raises(
        verifier.ConstructionK7AllPathFormalizationIndependentVerifierV180Error
    ):
        verifier.verify_all_path_formalization_readiness_independently_v180(
            contract_bytes=contract_value.canonical_bytes,
            readiness_bytes=canonical_json_bytes(forged),
        )

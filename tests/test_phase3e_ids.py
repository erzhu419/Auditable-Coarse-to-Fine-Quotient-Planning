from fractions import Fraction
import hashlib

import pytest

from acfqp.artifacts import object_id
from acfqp.phase3e_ids import (
    CARDINALITY_EVIDENCE_DOMAIN,
    CAUSAL_EVIDENCE_DOMAIN,
    COMPARISON_PROFILE_DOMAIN,
    COUNTER_REGISTRY_DOMAIN,
    DECISION_POINT_DOMAIN,
    FRONTIER_SNAPSHOT_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    PRESELECTION_NOT_APPLICABLE_BINDING_DOMAIN,
    ROUTE_CAP_PROFILE_DOMAIN,
    ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN,
    TRANSACTION_DOMAIN,
    Phase3EIdentityError,
    canonical_json,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
    verify_content_id,
)


def test_registry_contains_all_normative_fq3_domains() -> None:
    assert {
        "acfqp:route-upper-bound-envelope:v1",
        "acfqp:comparison-profile:v1",
        "acfqp:counter-registry:v1",
        "acfqp:cardinality-evidence:v1",
        "acfqp:route-cap-profile:v1",
        "acfqp:frontier-snapshot:v1",
        "acfqp:causal-evidence:v1",
        "acfqp:decision-point:v1",
        "acfqp:transaction:v1",
    }.issubset(PHASE3E_DOMAIN_TAGS)
    assert {
        ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN,
        COMPARISON_PROFILE_DOMAIN,
        COUNTER_REGISTRY_DOMAIN,
        CARDINALITY_EVIDENCE_DOMAIN,
        ROUTE_CAP_PROFILE_DOMAIN,
        FRONTIER_SNAPSHOT_DOMAIN,
        CAUSAL_EVIDENCE_DOMAIN,
        DECISION_POINT_DOMAIN,
        TRANSACTION_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)


def test_registry_includes_routing_and_accounting_v1_domains() -> None:
    assert {
        "acfqp:route-decision-context:v1",
        "acfqp:route-decision:v1",
        "acfqp:trusted-budget-replay:v1",
        "acfqp:terminal-artifact:v1",
        "acfqp:typed-verification-attestation:v1",
        "acfqp:counter-record:v1",
        "acfqp:work-vector:v1",
        "acfqp:comparison-vector:v1",
        "acfqp:native-zero-attestation:v1",
        "acfqp:reconciliation-proof:v1",
        "acfqp:actual-projection-profile:v1",
        "acfqp:actual-projection-proof:v1",
        "acfqp:occurrence-work-sum:v1",
        "acfqp:workload-vector-spec:v1",
        "acfqp:workload-vector-prefix:v1",
        "acfqp:workload-vector-analysis:v1",
        "acfqp:logical-occurrence:v1",
        "acfqp:route-attempt:v1",
        "acfqp:rebuild-policy:v1",
        "acfqp:rebuild-event:v1",
        "acfqp:campaign-occurrence-closure:v1",
        "acfqp:campaign-summary:v1",
        PRESELECTION_NOT_APPLICABLE_BINDING_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)


def test_canonical_json_is_sorted_compact_utf8_and_reduces_fractions() -> None:
    left = {
        "中文": "商空间",
        "probability": Fraction(2, 6),
        "nested": [{"z": 2, "a": 1}],
    }
    right = {
        "nested": [{"a": 1, "z": 2}],
        "probability": Fraction(1, 3),
        "中文": "商空间",
    }

    expected = (
        '{"nested":[{"a":1,"z":2}],"probability":'
        '{"denominator":3,"numerator":1},"中文":"商空间"}'
    )
    assert canonical_json(left) == expected
    assert canonical_json_bytes(left) == expected.encode("utf-8")
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert loads_canonical_json(expected.encode("utf-8")) == right


def test_content_id_is_the_normative_full_domain_separated_sha256() -> None:
    document = {"query_id": "query-1", "limit": Fraction(1, 20)}
    expected = hashlib.sha256(
        ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(document)
    ).hexdigest()

    identifier = content_id(ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN, document)
    assert identifier == expected
    assert len(identifier) == 64
    assert identifier == identifier.lower()
    assert parse_content_id(identifier) == identifier
    assert verify_content_id(
        ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN, document, identifier
    )


def test_equal_json_in_different_domains_cannot_reuse_an_id() -> None:
    document = {"schema_version": "1.0.0", "payload": []}
    upper_id = content_id(ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN, document)
    decision_id = content_id(DECISION_POINT_DOMAIN, document)

    assert upper_id != decision_id
    assert not verify_content_id(DECISION_POINT_DOMAIN, document, upper_id)


@pytest.mark.parametrize(
    "bad_value",
    (
        float("nan"),
        float("inf"),
        float("-inf"),
        {"nested": float("nan")},
    ),
)
def test_nonfinite_numbers_are_rejected(bad_value: object) -> None:
    with pytest.raises(Phase3EIdentityError, match="non-finite"):
        canonical_json_bytes(bad_value)


@pytest.mark.parametrize(
    "bad_value",
    (
        (1, 2),
        {1, 2},
        b"bytes",
        {1: "non-string-key"},
        object(),
    ),
)
def test_unsupported_python_values_are_rejected(bad_value: object) -> None:
    with pytest.raises(Phase3EIdentityError):
        canonical_json_bytes(bad_value)


@pytest.mark.parametrize(
    "bad_value",
    (
        {"numerator": 2, "denominator": 4},
        {"numerator": 1, "denominator": -3},
        {"numerator": True, "denominator": 3},
        {"numerator": 1},
        {"numerator": 1, "denominator": 3, "extra": 0},
    ),
)
def test_noncanonical_rational_records_are_rejected(bad_value: object) -> None:
    with pytest.raises(Phase3EIdentityError, match="rational"):
        canonical_json_bytes(bad_value)


@pytest.mark.parametrize(
    "bad_json",
    (
        '{"b":2,"a":1}',
        '{"a":1, "b":2}',
        '{"a":1}\n',
        '{"a":1,"a":1}',
        '{"a":NaN}',
        '{"a":1e0}',
        '{"denominator":4,"numerator":2}',
    ),
)
def test_strict_loader_rejects_noncanonical_or_unsafe_json(bad_json: str) -> None:
    with pytest.raises(Phase3EIdentityError):
        loads_canonical_json(bad_json)


def test_strict_loader_rejects_non_utf8_bytes() -> None:
    with pytest.raises(Phase3EIdentityError, match="UTF-8"):
        loads_canonical_json(b'"\xff"')


def test_unregistered_domains_and_noncanonical_ids_are_rejected() -> None:
    with pytest.raises(Phase3EIdentityError, match="unregistered"):
        content_id("acfqp:unregistered:v1", {"a": 1})
    for invalid in ("0" * 63, "0" * 65, "A" * 64, "obj-" + "0" * 64, 7):
        with pytest.raises(Phase3EIdentityError, match="64 lowercase"):
            parse_content_id(invalid)  # type: ignore[arg-type]


def test_exact_field_helper_rejects_missing_extra_and_non_string_fields() -> None:
    require_exact_fields({"a": 1, "b": 2}, ("a", "b"), context="fixture")

    with pytest.raises(
        Phase3EIdentityError,
        match=r"missing=\['b'\].*unexpected=\['c'\]",
    ):
        require_exact_fields({"a": 1, "c": 3}, ("a", "b"), context="fixture")
    with pytest.raises(Phase3EIdentityError, match="field names must be strings"):
        require_exact_fields({1: "bad"}, ("a",), context="fixture")  # type: ignore[dict-item]


def test_cycles_are_rejected_instead_of_recursing_forever() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    with pytest.raises(Phase3EIdentityError, match="cyclic"):
        canonical_json_bytes(cyclic)


def test_phase3e_module_does_not_change_legacy_object_ids() -> None:
    assert object_id(
        {"probability": Fraction(1, 3), "states": [1, 2, 3]}
    ) == "obj-79957ed5a3639f5e"

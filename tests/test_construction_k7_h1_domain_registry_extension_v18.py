from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v12 as v12
from acfqp import construction_k7_h1_domain_registry_extension_v15 as v15
from acfqp import construction_k7_h1_domain_registry_extension_v16 as v16
from acfqp import construction_k7_h1_domain_registry_extension_v17 as v17
from acfqp import construction_k7_h1_domain_registry_extension_v18 as v18
from acfqp.phase3e_ids import canonical_json_bytes


OLDER_EXTENSIONS = (v12, v15, v16, v17)
EXPECTED_REGISTRY = {
    "construction_k7_h1_two_birth_execution_source_closure_v1": (
        "acfqp:construction-k7-h1-two-birth-execution-source-closure:v1"
    ),
    "construction_k7_h1_nested_probe_credential_observation_bundle_v1": (
        "acfqp:construction-k7-h1-nested-probe-credential-observation-bundle:v1"
    ),
    "construction_k7_h1_live_two_birth_prefix_checkpoint_v1": (
        "acfqp:construction-k7-h1-live-two-birth-prefix-checkpoint:v1"
    ),
    "construction_k7_h1_two_birth_protocol_failure_closure_v1": (
        "acfqp:construction-k7-h1-two-birth-protocol-failure-closure:v1"
    ),
}


def test_v18_registry_contains_exactly_the_four_two_birth_domains() -> None:
    registry = v18.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V18
    assert dict(registry) == EXPECTED_REGISTRY
    assert len(registry) == 4
    assert len(set(registry.values())) == len(registry)
    assert v18.K7_H1_DOMAIN_TAG_EXTENSION_V18 == frozenset(
        EXPECTED_REGISTRY.values()
    )


def test_v18_domains_are_disjoint_from_v12_v15_v16_and_v17() -> None:
    for older in OLDER_EXTENSIONS:
        older_domains = getattr(
            older,
            next(
                name
                for name in vars(older)
                if name.startswith("K7_H1_DOMAIN_TAG_EXTENSION_V")
                and not name.startswith("K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY")
            ),
        )
        assert v18.K7_H1_DOMAIN_TAG_EXTENSION_V18.isdisjoint(older_domains)


@pytest.mark.parametrize("domain", sorted(v18.K7_H1_DOMAIN_TAG_EXTENSION_V18))
def test_v18_content_ids_are_exact_and_domain_separated(domain: str) -> None:
    payload = {"schema": "acfqp.test.v1", "value": 18}
    expected = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    assert v18.extension_content_id_v18(domain, payload) == expected
    for other in v18.K7_H1_DOMAIN_TAG_EXTENSION_V18 - {domain}:
        assert v18.extension_content_id_v18(other, payload) != expected


@pytest.mark.parametrize(
    "invalid_domain",
    [
        "acfqp:unregistered:v1",
        1,
        *[
            domain
            for older in OLDER_EXTENSIONS
            for domain in getattr(
                older,
                next(
                    name
                    for name in vars(older)
                    if name.startswith("K7_H1_DOMAIN_TAG_EXTENSION_V")
                    and not name.startswith("K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY")
                ),
            )
        ],
    ],
)
def test_v18_rejects_unregistered_and_cross_version_domains(
    invalid_domain: object,
) -> None:
    with pytest.raises(ValueError):
        v18.extension_content_id_v18(invalid_domain, {"x": 1})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("older", "function_name"),
    [
        (v12, "extension_content_id_v12"),
        (v15, "extension_content_id_v15"),
        (v16, "extension_content_id_v16"),
        (v17, "extension_content_id_v17"),
    ],
)
def test_older_extensions_reject_v18_domains(older: object, function_name: str) -> None:
    content_id = getattr(older, function_name)
    for domain in v18.K7_H1_DOMAIN_TAG_EXTENSION_V18:
        with pytest.raises(ValueError):
            content_id(domain, {"x": 1})

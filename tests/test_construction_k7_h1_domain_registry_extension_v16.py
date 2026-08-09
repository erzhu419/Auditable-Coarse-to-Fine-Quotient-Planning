from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v15 as v15
from acfqp import construction_k7_h1_domain_registry_extension_v16 as v16
from acfqp.phase3e_ids import canonical_json_bytes


def test_v16_domains_are_unique_and_disjoint_from_v15() -> None:
    registry = v16.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V16
    assert len(registry) == 4
    assert len(set(registry.values())) == len(registry)
    assert set(registry.values()).isdisjoint(v15.K7_H1_DOMAIN_TAG_EXTENSION_V15)
    assert all(tag.startswith("acfqp:construction-k7-h1-") for tag in registry.values())


@pytest.mark.parametrize(
    "domain",
    sorted(v16.K7_H1_DOMAIN_TAG_EXTENSION_V16),
)
def test_v16_content_ids_are_exact_and_domain_separated(domain: str) -> None:
    payload = {"schema": "acfqp.test.v1", "value": 7}
    expected = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    assert v16.extension_content_id_v16(domain, payload) == expected
    other = next(
        candidate
        for candidate in v16.K7_H1_DOMAIN_TAG_EXTENSION_V16
        if candidate != domain
    )
    assert v16.extension_content_id_v16(other, payload) != expected


def test_v16_rejects_unregistered_or_cross_version_domains() -> None:
    for domain in (
        "acfqp:unregistered:v1",
        next(iter(v15.K7_H1_DOMAIN_TAG_EXTENSION_V15)),
        1,
    ):
        with pytest.raises(ValueError):
            v16.extension_content_id_v16(domain, {"x": 1})  # type: ignore[arg-type]

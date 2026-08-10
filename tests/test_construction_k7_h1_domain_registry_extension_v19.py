from __future__ import annotations

import importlib

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v19 as v19


def test_v19_registry_is_complete_unique_and_disjoint_from_v1_through_v18() -> None:
    assert len(v19.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V19) == 19
    assert len(v19.K7_H1_DOMAIN_TAG_EXTENSION_V19) == 19
    assert set(v19.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V19.values()) == set(
        v19.K7_H1_DOMAIN_TAG_EXTENSION_V19
    )
    earlier: set[str] = set()
    for version in range(1, 19):
        module = importlib.import_module(
            f"acfqp.construction_k7_h1_domain_registry_extension_v{version}"
        )
        earlier.update(getattr(module, f"K7_H1_DOMAIN_TAG_EXTENSION_V{version}"))
    assert earlier.isdisjoint(v19.K7_H1_DOMAIN_TAG_EXTENSION_V19)


def test_v19_content_ids_are_role_separated_and_registry_only() -> None:
    payload = {"schema": "test.v1", "value": 1}
    identifiers = {
        v19.extension_content_id_v19(domain, payload)
        for domain in v19.K7_H1_DOMAIN_TAG_EXTENSION_V19
    }
    assert len(identifiers) == len(v19.K7_H1_DOMAIN_TAG_EXTENSION_V19)
    with pytest.raises(ValueError, match="absent"):
        v19.extension_content_id_v19("acfqp:not-registered:v1", payload)
    with pytest.raises(ValueError, match="absent"):
        v19.extension_content_id_v19(
            next(iter(v19.K7_H1_DOMAIN_TAG_EXTENSION_V19)) + "\x00cross-role",
            payload,
        )

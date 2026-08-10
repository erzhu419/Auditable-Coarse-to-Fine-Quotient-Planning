from __future__ import annotations

import importlib

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v20 as v20


def test_v20_registry_is_unique_complete_and_disjoint_from_v1_through_v19() -> None:
    assert len(v20.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V20) == 10
    assert len(v20.K7_H1_DOMAIN_TAG_EXTENSION_V20) == 10
    assert set(v20.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V20.values()) == set(
        v20.K7_H1_DOMAIN_TAG_EXTENSION_V20
    )
    earlier: set[str] = set()
    for version in range(1, 20):
        module = importlib.import_module(
            f"acfqp.construction_k7_h1_domain_registry_extension_v{version}"
        )
        earlier.update(getattr(module, f"K7_H1_DOMAIN_TAG_EXTENSION_V{version}"))
    assert earlier.isdisjoint(v20.K7_H1_DOMAIN_TAG_EXTENSION_V20)


def test_v20_roles_are_separated_and_registry_only() -> None:
    payload = {"schema": "test.v1", "value": 1}
    identifiers = {
        v20.extension_content_id_v20(domain, payload)
        for domain in v20.K7_H1_DOMAIN_TAG_EXTENSION_V20
    }
    assert len(identifiers) == 10
    with pytest.raises(ValueError, match="absent"):
        v20.extension_content_id_v20("acfqp:not-registered:v1", payload)
    with pytest.raises(ValueError, match="absent"):
        v20.extension_content_id_v20(
            next(iter(v20.K7_H1_DOMAIN_TAG_EXTENSION_V20)) + "\x00cross-role",
            payload,
        )


def test_v20_explicitly_reserves_each_future_atomic_consume_role() -> None:
    keys = set(v20.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V20)
    for fragment in (
        "consumer_evidence",
        "activation_successor",
        "prebound_native_edge_source_closure",
        "prebound_native_edge_capsule",
        "prebound_native_edge_activation",
        "prebound_native_edge_cancellation",
        "consumed_lease",
        "consumed_closure",
        "slot_transfer",
        "consume_failure_closure",
    ):
        assert any(fragment in key for key in keys)

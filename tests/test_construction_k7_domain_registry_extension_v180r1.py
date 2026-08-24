from __future__ import annotations

from acfqp import construction_k7_domain_registry_extension_v180 as v180
from acfqp import construction_k7_domain_registry_extension_v180r1 as v180r1


def test_v180r1_domains_are_fresh_and_additive() -> None:
    assert len(v180r1.K7_DOMAIN_TAG_EXTENSION_V180R1) == 5
    assert not (
        v180r1.K7_DOMAIN_TAG_EXTENSION_V180R1
        & v180.K7_DOMAIN_TAG_EXTENSION_V180
    )
    assert set(v180r1.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R1) == {
        "terminal_observation",
        "terminal_measurement",
        "terminal_bundle",
        "campaign_bundle",
        "verification",
    }


def test_v180r1_content_ids_are_domain_separated() -> None:
    payload = {"same": "payload"}
    ids = {
        v180r1.extension_content_id_v180r1(domain, payload)
        for domain in v180r1.K7_DOMAIN_TAG_EXTENSION_V180R1
    }
    assert len(ids) == 5

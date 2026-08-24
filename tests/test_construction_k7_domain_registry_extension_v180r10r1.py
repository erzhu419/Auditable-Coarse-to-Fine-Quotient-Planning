from acfqp import construction_k7_domain_registry_extension_v180r10r1 as domains


def test_v180r10r1_domains_are_distinct_and_closed() -> None:
    rows = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R10R1
    assert len(rows) == 5
    assert len(set(rows.values())) == 5
    assert all(value.endswith(":v180r10r1") for value in rows.values())
    for value in rows.values():
        assert len(domains.extension_content_id_v180r10r1(value, {"x": 1})) == 64


import pytest

from acfqp import construction_k7_domain_registry_extension_v55 as domains
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v55_extension_is_closed_unique_and_disjoint_from_historical_registry():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V55) == 11
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V55) == 11
    assert domains.K7_DOMAIN_TAG_EXTENSION_V55.isdisjoint(PHASE3E_DOMAIN_TAGS)


def test_v55_extension_content_id_is_domain_separated_and_closed():
    first = next(iter(domains.K7_DOMAIN_TAG_EXTENSION_V55))
    second = next(row for row in domains.K7_DOMAIN_TAG_EXTENSION_V55 if row != first)
    assert domains.extension_content_id_v55(first, {"x": 1}) != (
        domains.extension_content_id_v55(second, {"x": 1})
    )
    with pytest.raises(ValueError):
        domains.extension_content_id_v55("acfqp:unregistered:v55", {"x": 1})

import pytest

from acfqp import construction_k7_domain_registry_extension_v85 as v85
from acfqp import construction_k7_domain_registry_extension_v85r1 as domains


def test_v85r1_domains_are_additive_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V85R1) == 4
    assert domains.K7_DOMAIN_TAG_EXTENSION_V85R1.isdisjoint(
        v85.K7_DOMAIN_TAG_EXTENSION_V85
    )
    domain = domains.CONSTRUCTION_K7_V84_TEMPLATE_LIBRARY_V85R1_DOMAIN
    assert domains.extension_content_id_v85r1(domain, {"x": 1}) == domains.extension_content_id_v85r1(domain, {"x": 1})
    with pytest.raises(ValueError):
        domains.extension_content_id_v85r1("acfqp:foreign", {})

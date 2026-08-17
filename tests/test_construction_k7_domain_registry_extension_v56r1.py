import pytest

from acfqp import construction_k7_domain_registry_extension_v55 as v55
from acfqp import construction_k7_domain_registry_extension_v56 as v56
from acfqp import construction_k7_domain_registry_extension_v56r1 as v56r1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v56r1_domains_are_minimal_unique_and_disjoint():
    assert len(v56r1.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V56R1) == 5
    assert len(v56r1.K7_DOMAIN_TAG_EXTENSION_V56R1) == 5
    assert v56r1.K7_DOMAIN_TAG_EXTENSION_V56R1.isdisjoint(PHASE3E_DOMAIN_TAGS)
    assert v56r1.K7_DOMAIN_TAG_EXTENSION_V56R1.isdisjoint(
        v55.K7_DOMAIN_TAG_EXTENSION_V55
    )
    assert v56r1.K7_DOMAIN_TAG_EXTENSION_V56R1.isdisjoint(
        v56.K7_DOMAIN_TAG_EXTENSION_V56
    )


def test_v56r1_content_id_is_closed():
    domain = next(iter(v56r1.K7_DOMAIN_TAG_EXTENSION_V56R1))
    assert len(v56r1.extension_content_id_v56r1(domain, {"x": 1})) == 64
    with pytest.raises(ValueError):
        v56r1.extension_content_id_v56r1("acfqp:unknown:v56r1", {})

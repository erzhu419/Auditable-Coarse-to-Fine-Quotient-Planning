import pytest

from acfqp import construction_k7_domain_registry_extension_v56r1 as v56r1
from acfqp import construction_k7_domain_registry_extension_v57 as v57
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v57_domains_are_unique_and_disjoint():
    assert len(v57.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V57) == 5
    assert len(v57.K7_DOMAIN_TAG_EXTENSION_V57) == 5
    assert v57.K7_DOMAIN_TAG_EXTENSION_V57.isdisjoint(PHASE3E_DOMAIN_TAGS)
    assert v57.K7_DOMAIN_TAG_EXTENSION_V57.isdisjoint(
        v56r1.K7_DOMAIN_TAG_EXTENSION_V56R1
    )


def test_v57_content_id_is_closed():
    domain = next(iter(v57.K7_DOMAIN_TAG_EXTENSION_V57))
    assert len(v57.extension_content_id_v57(domain, {"x": 1})) == 64
    with pytest.raises(ValueError):
        v57.extension_content_id_v57("acfqp:unknown:v57", {})

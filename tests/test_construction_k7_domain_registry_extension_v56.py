import pytest

from acfqp import construction_k7_domain_registry_extension_v55 as v55
from acfqp import construction_k7_domain_registry_extension_v56 as v56
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v56_extension_is_closed_unique_and_disjoint_from_predecessors():
    assert len(v56.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V56) == 11
    assert len(v56.K7_DOMAIN_TAG_EXTENSION_V56) == 11
    assert v56.K7_DOMAIN_TAG_EXTENSION_V56.isdisjoint(PHASE3E_DOMAIN_TAGS)
    assert v56.K7_DOMAIN_TAG_EXTENSION_V56.isdisjoint(
        v55.K7_DOMAIN_TAG_EXTENSION_V55
    )


def test_v56_extension_content_id_is_domain_separated_and_closed():
    first, second, *_ = v56.K7_DOMAIN_TAG_EXTENSION_V56
    assert v56.extension_content_id_v56(first, {"x": 1}) != (
        v56.extension_content_id_v56(second, {"x": 1})
    )
    with pytest.raises(ValueError):
        v56.extension_content_id_v56("acfqp:unregistered:v56", {"x": 1})

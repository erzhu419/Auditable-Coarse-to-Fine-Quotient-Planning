from __future__ import annotations

from acfqp import construction_k7_layout_factorization_preregistration_v50 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, content_id


def test_v50_domains_are_registered_unique_and_pairwise_disjoint() -> None:
    values = list(pre.FUTURE_DOMAINS.values())
    assert len(values) == len(set(values)) == 12
    assert set(values) <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "acfqp.v50.domain.probe", "value": 1}
    assert len({content_id(domain, payload) for domain in values}) == len(values)

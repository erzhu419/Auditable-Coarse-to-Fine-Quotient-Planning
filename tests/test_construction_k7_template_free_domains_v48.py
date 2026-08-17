from acfqp import construction_k7_template_free_preregistration_v48 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, content_id


def test_v48_domains_are_registered_and_role_separated() -> None:
    domains = tuple(pre.FUTURE_DOMAINS.values())
    assert len(domains) == len(set(domains)) == 12
    assert set(domains) <= PHASE3E_DOMAIN_TAGS
    assert len({content_id(domain, {"same": "payload"}) for domain in domains}) == 12


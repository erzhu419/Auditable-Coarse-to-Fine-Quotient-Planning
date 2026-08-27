from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v42_domain_registry_is_fresh_complete_and_content_addressed() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V42) == 18
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V42) == 18
    assert domains.K7_DOMAIN_TAG_EXTENSION_V42.isdisjoint(PHASE3E_DOMAIN_TAGS)
    assert all(tag.endswith(":v42") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V42)

    payload = {"schema": "acfqp.v42.domain-separation-test"}
    identifiers = {
        domains.extension_content_id_v42(tag, payload)
        for tag in domains.K7_DOMAIN_TAG_EXTENSION_V42
    }
    assert len(identifiers) == len(domains.K7_DOMAIN_TAG_EXTENSION_V42)


def test_v42_domain_helper_rejects_unregistered_tags() -> None:
    try:
        domains.extension_content_id_v42("acfqp:foreign:v42", {})
    except ValueError as error:
        assert "absent from V42" in str(error)
    else:  # pragma: no cover
        raise AssertionError("unregistered V42 domain was accepted")

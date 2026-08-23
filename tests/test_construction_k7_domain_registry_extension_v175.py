from acfqp.construction_k7_domain_registry_extension_v175 import (
    K7_DOMAIN_TAG_EXTENSION_REGISTRY_V175,
    K7_DOMAIN_TAG_EXTENSION_V175,
    extension_content_id_v175,
)


def test_v175_domain_registry_is_disjoint_and_content_addressed():
    assert len(K7_DOMAIN_TAG_EXTENSION_REGISTRY_V175) == 9
    assert len(K7_DOMAIN_TAG_EXTENSION_V175) == 9
    assert all(tag.endswith(":v175") for tag in K7_DOMAIN_TAG_EXTENSION_V175)
    domain = K7_DOMAIN_TAG_EXTENSION_REGISTRY_V175["certificate_delta"]
    assert extension_content_id_v175(domain, {"x": 1}) == extension_content_id_v175(
        domain, {"x": 1}
    )


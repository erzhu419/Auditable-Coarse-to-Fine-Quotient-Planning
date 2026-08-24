from __future__ import annotations

from acfqp import construction_k7_domain_registry_extension_v181r1 as v181r1
from acfqp import construction_k7_domain_registry_extension_v181r2 as v181r2


def test_v181r2_domain_registry_is_fresh_and_additive() -> None:
    assert len(v181r2.K7_DOMAIN_TAG_EXTENSION_V181R2) == 9
    assert not (
        v181r2.K7_DOMAIN_TAG_EXTENSION_V181R2
        & v181r1.K7_DOMAIN_TAG_EXTENSION_V181R1
    )

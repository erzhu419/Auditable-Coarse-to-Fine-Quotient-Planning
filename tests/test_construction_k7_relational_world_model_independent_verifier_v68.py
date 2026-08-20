import os

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V68") != "1",
    reason="explicit frozen V68 producer-free verification",
)
def test_v68_producer_free_verification_is_frozen_and_replayable():
    from acfqp.construction_k7_relational_world_model_campaign_v68 import (
        run_relational_world_model_campaign_v68,
    )
    from acfqp.construction_k7_relational_world_model_independent_verifier_v68 import (
        verify_relational_world_model_campaign_bytes_v68,
    )

    campaign = run_relational_world_model_campaign_v68()
    first = verify_relational_world_model_campaign_bytes_v68(campaign.canonical_bytes)
    second = verify_relational_world_model_campaign_bytes_v68(campaign.canonical_bytes)
    assert first == second
    document = loads_canonical_json(first)
    assert document["status"] == "PRODUCER_FREE_RELATIONAL_WORLD_MODEL_LEDGER_VERIFIED"
    assert document["producer_imported"] is False
    assert document["v28_source_rows_not_fully_retained_by_v68"] is True


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V68") != "1",
    reason="explicit frozen V68 producer-free verification attack",
)
def test_v68_independent_verifier_rejects_rehashed_claim_flip():
    from acfqp import construction_k7_domain_registry_extension_v68 as domains
    from acfqp.construction_k7_relational_world_model_campaign_v68 import (
        run_relational_world_model_campaign_v68,
    )
    from acfqp.construction_k7_relational_world_model_independent_verifier_v68 import (
        ConstructionK7RelationalWorldModelIndependentVerifierV68Error,
        verify_relational_world_model_campaign_bytes_v68,
    )

    document = run_relational_world_model_campaign_v68().to_document()
    document["relational_abstract_plan_used_as_safety_authority"] = True
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = domains.extension_content_id_v68(
        domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_CAMPAIGN_V68_DOMAIN,
        payload,
    )
    with pytest.raises(ConstructionK7RelationalWorldModelIndependentVerifierV68Error):
        verify_relational_world_model_campaign_bytes_v68(canonical_json_bytes(document))

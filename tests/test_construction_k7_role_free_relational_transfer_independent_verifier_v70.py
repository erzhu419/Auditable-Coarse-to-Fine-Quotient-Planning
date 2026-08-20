import os

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V70") != "1",
    reason="explicit V70 producer-free transfer verification",
)
def test_v70_producer_free_verification_replays_target_exactness():
    from acfqp.construction_k7_role_free_relational_transfer_campaign_v70 import (
        run_role_free_relational_transfer_campaign_v70,
    )
    from acfqp.construction_k7_role_free_relational_transfer_independent_verifier_v70 import (
        verify_role_free_relational_transfer_campaign_bytes_v70,
    )

    campaign = run_role_free_relational_transfer_campaign_v70()
    first = verify_role_free_relational_transfer_campaign_bytes_v70(
        campaign.canonical_bytes
    )
    second = verify_role_free_relational_transfer_campaign_bytes_v70(
        campaign.canonical_bytes
    )
    assert first == second
    document = loads_canonical_json(first)
    assert document["target_exact_context_terminal_programs_reconstructed"] == 6
    assert document["transferred_terminal_programs_target_rows_replayed"] == 2
    assert document["template_library_membership_not_independently_opened"] is True
    assert document["producer_imported"] is False


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V70") != "1",
    reason="explicit V70 transfer claim attack",
)
def test_v70_rejects_rehashed_transfer_safety_claim_flip():
    from acfqp import construction_k7_domain_registry_extension_v70 as domains
    from acfqp.construction_k7_role_free_relational_transfer_campaign_v70 import (
        run_role_free_relational_transfer_campaign_v70,
    )
    from acfqp.construction_k7_role_free_relational_transfer_independent_verifier_v70 import (
        ConstructionK7RoleFreeRelationalTransferIndependentVerifierV70Error,
        verify_role_free_relational_transfer_campaign_bytes_v70,
    )

    document = run_role_free_relational_transfer_campaign_v70().to_document()
    document["transferred_abstract_plan_used_as_safety_authority"] = True
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = domains.extension_content_id_v70(
        domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_CAMPAIGN_V70_DOMAIN,
        payload,
    )
    with pytest.raises(ConstructionK7RoleFreeRelationalTransferIndependentVerifierV70Error):
        verify_role_free_relational_transfer_campaign_bytes_v70(
            canonical_json_bytes(document)
        )

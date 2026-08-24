from pathlib import Path

from acfqp import construction_k7_standard_2048_expression_full_accounted_campaign_v34 as campaign
from acfqp import construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34 as verifier
from acfqp import construction_k7_v34_retained_campaign_reconstructor_v180r11 as reconstructor


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / ".tmp" / "exact-freeze" / "v180r5_v34_production_output"


def test_v180r11_reconstructs_exact_v34_campaign_and_verification() -> None:
    recovered = reconstructor.reconstruct_retained_v34_campaign_v180r11(RETAINED)
    assert recovered.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert recovered.verification_id == verifier.EXPECTED_VERIFICATION_ID
    assert recovered.to_document()["operational_work_vector_count"] == 45
    assert recovered.to_document()["evaluation_work_vector_count"] == 34
    assert recovered.to_document()["complete_decision_count"] == 3187

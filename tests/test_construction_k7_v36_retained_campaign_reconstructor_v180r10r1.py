from pathlib import Path

from acfqp import construction_k7_v36_retained_campaign_reconstructor_v180r10r1 as reconstructor


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / ".tmp" / "exact-freeze" / "v180r10_v36_resource_successor_output"


def test_v180r10r1_reconstructs_exact_v35_and_v36_documents() -> None:
    recovered = reconstructor.reconstruct_retained_v36_campaign_v180r10r1(RETAINED)
    assert recovered.campaign_id == reconstructor.V36_CAMPAIGN_ID
    assert recovered.verification_id == reconstructor.V36_VERIFICATION_ID
    assert recovered.semantic_replay_performed is False
    assert len(recovered.v35_campaign_bytes) == 2_295_086
    assert len(recovered.v35_verification_bytes) == 2_052
    assert len(recovered.v36_campaign_bytes) == 250_414
    assert len(recovered.v36_verification_bytes) == 2_457
    assert recovered.to_document()["complete_decision_count"] == 512
    assert recovered.to_document()["operational_target_probability_label_query_count"] == 6


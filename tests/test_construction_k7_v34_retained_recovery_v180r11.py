from pathlib import Path

from acfqp import construction_k7_v34_retained_recovery_independent_verifier_v180r11 as verifier
from acfqp import construction_k7_v34_retained_recovery_terminal_v180r11 as producer
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / ".tmp" / "exact-freeze" / "v180r5_v34_production_output"


def test_v180r11_finish_forward_replays_without_scientific_rerun() -> None:
    authorization_id = "f" * 64
    terminal = producer.finish_forward_retained_v34_occurrence_v180r11(
        RETAINED,
        recovery_authorization_id=authorization_id,
    )
    verification = verifier.verify_v34_retained_recovery_bytes_independently_v180r11(
        terminal.canonical_bytes,
        RETAINED,
        recovery_authorization_id=authorization_id,
    )
    assert verification["v34_retained_terminal_id"] == terminal.terminal_id
    assert verification["operational_work_vector_count"] == 45
    assert verification["counter_record_count"] == 45 * 269
    assert verification["scientific_occurrence_rerun"] is False
    assert verification["source_campaign_replayed_without_recovery_producer_import"] is True
    assert verification["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert verification["official_execution_allowed"] is False


def test_v180r11_independent_verifier_rejects_terminal_tamper() -> None:
    authorization_id = "e" * 64
    terminal = producer.finish_forward_retained_v34_occurrence_v180r11(
        RETAINED,
        recovery_authorization_id=authorization_id,
    )
    document = terminal.to_document()
    document["scientific_occurrence_rerun_by_successor"] = True
    try:
        verifier.verify_v34_retained_recovery_bytes_independently_v180r11(
            canonical_json_bytes(document),
            RETAINED,
            recovery_authorization_id=authorization_id,
        )
    except verifier.ConstructionK7V34RetainedRecoveryIndependentVerifierV180r11Error:
        pass
    else:
        raise AssertionError("tampered V180r11 terminal was accepted")

import copy
import os

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V69") != "1",
    reason="explicit V69 producer-free reconstruction",
)
def test_v69_independently_reconstructs_all_terminal_programs():
    from acfqp.construction_k7_source_complete_relational_campaign_v69 import (
        run_source_complete_relational_campaign_v69,
    )
    from acfqp.construction_k7_source_complete_relational_independent_verifier_v69 import (
        verify_source_complete_relational_campaign_bytes_v69,
    )

    campaign = run_source_complete_relational_campaign_v69()
    first = verify_source_complete_relational_campaign_bytes_v69(
        campaign.canonical_bytes
    )
    second = verify_source_complete_relational_campaign_bytes_v69(
        campaign.canonical_bytes
    )
    assert first == second
    document = loads_canonical_json(first)
    assert document["independently_reconstructed_terminal_program_count"] == 12
    assert document["decision_tree_frontiers_rederived"] is True
    assert document["v28_imported"] is False
    assert document["producer_imported"] is False


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V69") != "1",
    reason="explicit V69 source-row attack",
)
def test_v69_rejects_rehashed_retained_source_tamper():
    from acfqp import construction_k7_domain_registry_extension_v69 as domains
    from acfqp.construction_k7_source_complete_relational_campaign_v69 import (
        run_source_complete_relational_campaign_v69,
    )
    from acfqp.construction_k7_source_complete_relational_independent_verifier_v69 import (
        ConstructionK7SourceCompleteRelationalIndependentVerifierV69Error,
        verify_source_complete_relational_campaign_bytes_v69,
    )

    document = run_source_complete_relational_campaign_v69().to_document()
    forged = copy.deepcopy(document)
    envelope = forged["occurrences"][0]["prior_episode"]
    evidence = envelope["terminal_program_source_evidence"]
    status_target = envelope["predecessor_v30_episode"][
        "final_relational_terminal_program"
    ]["status_target_column"]
    evidence["common_partial_raw_transition_rows"][0]["post_vector"][
        status_target
    ] += 1000
    evidence["raw_transition_rows"][0] = copy.deepcopy(
        evidence["common_partial_raw_transition_rows"][0]
    )
    evidence_payload = {
        key: value for key, value in evidence.items() if key != "source_evidence_id"
    }
    evidence["source_evidence_id"] = __import__("hashlib").sha256(
        b"acfqp:source-complete-terminal-program-evidence:v31\x00"
        + canonical_json_bytes(evidence_payload)
    ).hexdigest()
    envelope["source_evidence_id"] = evidence["source_evidence_id"]
    episode_payload = {
        key: value for key, value in envelope.items() if key != "source_complete_episode_id"
    }
    envelope["source_complete_episode_id"] = __import__("hashlib").sha256(
        b"acfqp:generic-source-complete-relational-world-model:v31\x00"
        + canonical_json_bytes(episode_payload)
    ).hexdigest()
    occurrence = forged["occurrences"][0]
    occurrence_payload = {
        key: value for key, value in occurrence.items() if key != "occurrence_id"
    }
    occurrence["occurrence_id"] = domains.extension_content_id_v69(
        domains.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_OCCURRENCE_V69_DOMAIN,
        occurrence_payload,
    )
    campaign_payload = {
        key: value for key, value in forged.items() if key != "campaign_id"
    }
    forged["campaign_id"] = domains.extension_content_id_v69(
        domains.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_CAMPAIGN_V69_DOMAIN,
        campaign_payload,
    )
    with pytest.raises(ConstructionK7SourceCompleteRelationalIndependentVerifierV69Error):
        verify_source_complete_relational_campaign_bytes_v69(
            canonical_json_bytes(forged)
        )

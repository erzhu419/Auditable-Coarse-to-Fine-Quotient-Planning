from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v181r1 as domains
from acfqp import construction_k7_open_world_protocol_successor_v181r1 as successor


def test_v181r1_domains_are_fresh_and_complete() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V181R1) == 6
    assert all(tag.endswith(":v181r1") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V181R1)


def test_successor_preserves_failure_and_freezes_fresh_denominator() -> None:
    document = successor.freeze_open_world_protocol_successor_v181r1().to_document()
    assert len(document["manifest_commitments"]) == 3
    assert document["manifest_reveal_bytes_embedded"] is False
    assert document["target_outcomes_accessed"] is False
    assert document["target_denominator"]["total_episode_count"] == 72
    assert document["preserved_v181_failure_id"]


def test_successor_reuses_generic_implementation_without_positive_claims() -> None:
    document = successor.freeze_open_world_protocol_successor_v181r1().to_document()
    assert document["predecessor_implementation_source_bytes_reused_without_mutation"] is True
    assert document["whole_program_candidate_catalog_present"] is False
    assert document["named_target_family_registry_present"] is False
    locks = document["claim_locks"]
    assert locks["open_ended_world_model_invention_claimed"] is False
    assert locks["broad_iid_sample_efficiency_claimed"] is False
    assert locks["official_execution_allowed"] is False


def test_retained_successor_bytes_are_exact() -> None:
    value = successor.freeze_open_world_protocol_successor_v181r1()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r1_open_world_protocol_successor.json"
    )
    assert path.read_bytes() == value.canonical_bytes

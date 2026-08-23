import hashlib

from acfqp import construction_k7_domain_registry_extension_v178r1 as prior_domains
from acfqp import construction_k7_domain_registry_extension_v179 as domains
from acfqp import construction_k7_finite_objective_completion_contract_v179 as subject


def test_v179_contract_is_outcome_free_and_keeps_broad_claims_locked():
    frozen = subject.freeze_finite_objective_completion_contract_v179()
    document = frozen.to_document()
    assert document["target_outcomes_accessed"] is False
    assert len(document["required_evidence"]) == 5
    assert document["completion_rule"][
        "registered_finite_central_objective_may_be_marked_complete"
    ] is True
    assert document["claim_locks"]["complete_ground_world_model_synthesized"] is False
    assert document["claim_locks"]["arbitrary_unseen_domain_transfer_claimed"] is False
    assert document["claim_locks"]["official_execution_allowed"] is False
    assert document["claim_locks"]["official_scalar_cost"] is None
    assert document["claim_locks"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v179_domains_are_fresh_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V179) == 3
    assert domains.K7_DOMAIN_TAG_EXTENSION_V179.isdisjoint(
        prior_domains.K7_DOMAIN_TAG_EXTENSION_V178R1
    )


def test_v179_contract_constants_match_when_frozen():
    frozen = subject.freeze_finite_objective_completion_contract_v179()
    if subject.EXPECTED_CONTRACT_ID == "0" * 64:
        return
    assert frozen.completion_contract_id == subject.EXPECTED_CONTRACT_ID
    assert len(frozen.canonical_bytes) == subject.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == subject.EXPECTED_CANONICAL_SHA256

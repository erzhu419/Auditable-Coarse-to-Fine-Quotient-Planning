from __future__ import annotations

import hashlib

from acfqp import construction_k7_atomic_composition_preregistration_v49r2 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v49r2_freezes_fresh_relation_transport_successor() -> None:
    frozen = pre.freeze_atomic_composition_preregistration_v49r2()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert pre.verify_atomic_composition_preregistration_v49r2(frozen) is frozen
    document = frozen.to_document()
    predecessor = document["frozen_predecessor"]
    assert predecessor["v49_failure_id"] == pre.V49_FAILURE_ID
    assert predecessor["v49r1_failure_id"] == pre.V49R1_FAILURE_ID
    assert predecessor["both_failed_predecessors_preserved_without_correction"] is True
    assert document["fresh_v49r2_outcome_execution_performed"] is False


def test_v49r2_protocol_is_local_bounded_and_domains_are_fresh() -> None:
    document = pre.freeze_atomic_composition_preregistration_v49r2().to_document()
    protocol = document["protocol"]
    assert protocol["changed_occurrence_constant_invalidates_relation_transport_certificate"] is True
    assert protocol["one_witness_blind_support_exemplar_per_anonymous_relation_input"] is True
    assert protocol["maximum_target_relation_exemplar_labels"] == 4
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert len(set(pre.FUTURE_DOMAINS.values())) == 13
    assert document["generic_atomic_search"]["specialized_discovery_pattern_count"] == 0
    assert document["official_execution_allowed"] is False


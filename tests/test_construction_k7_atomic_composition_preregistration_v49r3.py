from __future__ import annotations

import hashlib

from acfqp import construction_k7_atomic_composition_preregistration_v49r3 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v49r3_freezes_ast_complete_fresh_successor() -> None:
    frozen = pre.freeze_atomic_composition_preregistration_v49r3()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert pre.verify_atomic_composition_preregistration_v49r3(frozen) is frozen
    document = frozen.to_document()
    assert document["frozen_predecessor"]["v49r2_failure_id"] == pre.V49R2_FAILURE_ID
    assert document["source_closure"]["frozen_before_any_v49r3_source_or_target_outcome"] is True
    assert document["fresh_v49r3_outcome_execution_performed"] is False


def test_v49r3_certificate_covers_e00_and_e03_ast_dependencies() -> None:
    document = pre.freeze_atomic_composition_preregistration_v49r3().to_document()
    protocol = document["protocol"]
    assert "E00_AND_E03" in protocol["relation_transport_dependency_extraction"]
    assert protocol["certificate_must_fail_if_any_dependent_leaf_changes"] is True
    assert document["recovery_correction"]["development_registered_outcomes_used"] is False
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert len(set(pre.FUTURE_DOMAINS.values())) == 13
    assert document["official_execution_allowed"] is False


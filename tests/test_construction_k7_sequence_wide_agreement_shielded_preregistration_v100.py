import copy
import hashlib

import pytest

from acfqp import construction_k7_sequence_wide_agreement_shielded_preregistration_v100 as pre


def test_v100_preregistration_is_outcome_free_and_fresh():
    frozen = pre.freeze_sequence_wide_agreement_shielded_preregistration_v100()
    verified = pre.verify_sequence_wide_agreement_shielded_preregistration_v100(
        frozen
    )
    document = verified.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )
    assert document["frozen_predecessors"]["v99_registered_gate_passed"] is False
    assert document["construction_contract"]["only_changed_variable"] == (
        "REGISTERED_SHIELD_PATH_COVERAGE_WINDOW"
    )
    assert document["construction_contract"]["v100_path_coverage_window"] == (
        "COMPLETE_PERSISTENT_SEQUENCE"
    )
    assert document["claim_boundary"]["registered_v100_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v100_preregistration_binds_fresh_seeds_and_two_workers():
    config = pre.campaign_config_v100()
    assert config["target_occurrences"] == [
        {"family": family, "seed": seed}
        for family, seed in pre.TARGET_OCCURRENCES
    ]
    assert tuple(config["target_episode_indices"]) == pre.TARGET_EPISODE_INDICES
    assert config["target_worker_count"] == 2
    assert len({seed for _family, seed in pre.TARGET_OCCURRENCES}) == 4


def test_v100_preregistration_rejects_copy_and_source_drift(monkeypatch):
    frozen = pre.freeze_sequence_wide_agreement_shielded_preregistration_v100()
    with pytest.raises(Exception):
        pre.verify_sequence_wide_agreement_shielded_preregistration_v100(
            copy.copy(frozen)
        )
    facts = list(pre.FROZEN_SOURCE_FACTS)
    path, count, digest = facts[0]
    monkeypatch.setattr(
        pre,
        "FROZEN_SOURCE_FACTS",
        ((path, count, "f" * 64), *facts[1:]),
    )
    pre._CACHE = None
    with pytest.raises(Exception):
        pre.freeze_sequence_wide_agreement_shielded_preregistration_v100()
    assert digest != hashlib.sha256(b"forged").hexdigest()

from pathlib import Path
import hashlib

from acfqp.anonymous_relational_factor_bank_v146 import (
    BANK_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    freeze_anonymous_relational_factor_bank_v146,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_anonymous_relational_factor_bank_v146(
        (ROOT / "v145_certificate_local_recovery_union_campaign.json").read_bytes(),
        (ROOT / "v145_certificate_local_recovery_union_verification.json").read_bytes(),
    )


def test_v146_alpha_normalizes_and_selects_reusable_relations():
    document = loads_canonical_json(_freeze())
    assert document["source_occurrence_count"] == 6
    assert document["constant_and_relation_names_alpha_normalized"] is True
    assert document["selected_relational_template_count"] > 0
    assert any(
        row["relation_symbol_count"] > 0 for row in document["selected_subprograms"]
    )
    assert document["new_target_outcomes_accessed"] is False
    assert document["historical_v121_instantiator_claimed_to_consume_relational_symbols"] is False
    assert document["new_relational_instantiator_required_before_target_use"] is True
    assert document["official_scalar_cost"] is None


def test_v146_frozen_bank_bytes_when_registered():
    raw = _freeze()
    if BANK_ID != "0" * 64:
        assert loads_canonical_json(raw)["bank_id"] == BANK_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256

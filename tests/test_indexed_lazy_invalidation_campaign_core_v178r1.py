from copy import deepcopy

from acfqp.indexed_lazy_invalidation_campaign_core_v178r1 import _correct_gate


def _base(*, invalidations, lookups):
    return {
        "registered_gate": {
            "passed": False,
            "receipt_reverse_indices_are_live": False,
            "other_required_gate": True,
        },
        "indexed_lazy_invalidation_metrics": {
            "graph_invalidations": invalidations,
            "program_invalidations": 0,
            "receipt_reverse_index_lookups": lookups,
            "receipt_reverse_index_updates": 8,
        },
    }


def test_v178r1_accepts_zero_lookup_only_when_no_invalidation_exists():
    gate = _correct_gate(_base(invalidations=0, lookups=0))
    assert gate["passed"] is True
    assert gate["zero_invalidation_requires_zero_receipt_lookup"] is True


def test_v178r1_requires_positive_lookup_for_positive_invalidation():
    gate = _correct_gate(_base(invalidations=1, lookups=0))
    assert gate["passed"] is False
    corrected = deepcopy(_base(invalidations=1, lookups=1))
    assert _correct_gate(corrected)["passed"] is True

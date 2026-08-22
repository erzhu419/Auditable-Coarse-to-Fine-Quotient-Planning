import copy
from functools import lru_cache

import pytest

from acfqp.construction_k7_occurrence_factor_bank_update_independent_verifier_v141 import (
    FROZEN_BANK_ID,
)
from acfqp.fifth_family_factor_bank_transfer_acquisition_v144 import (
    _validated_projection,
)
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    build_maintenance_cascade_adapter_v144,
    maintenance_cascade_config_v144,
)
from acfqp.generic_relational_factor_execution_projection_v144 import (
    GenericRelationalFactorExecutionProjectionV144Error,
    _lower_expression,
    compile_relational_factor_execution_projection_v144,
)
from acfqp.phase3e_ids import loads_canonical_json
from acfqp.robust_factor_dictionary_acquisition_v131r2 import (
    synthesize_robust_dictionary_factor_candidate_v131r2,
)
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import (
    fair_witness_blind_path_first_stream_v129r1,
)
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@lru_cache(maxsize=1)
def _candidate():
    config = maintenance_cascade_config_v144()
    adapter = build_maintenance_cascade_adapter_v144(1_044_003, config)
    batches = tuple(fair_witness_blind_path_first_stream_v129r1(adapter))
    rows = tuple(row for batch in batches[:72] for row in batch)
    dictionary = loads_canonical_json(
        (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes()
    )
    verification = loads_canonical_json(
        (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes()
    )
    assert dictionary["bank_id"] == FROZEN_BANK_ID
    projection = _validated_projection(dictionary, verification)
    candidate, _compute = synthesize_robust_dictionary_factor_candidate_v131r2(
        rows,
        adapter.catalogue,
        projection,
        support_label_count=72,
        factor_prior_enabled=False,
        layout_domain=config["generic_domains"]["layout"],
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
    )
    return candidate, rows, adapter.catalogue


def test_v144_lowers_anonymous_relation_to_v121_v122_expression():
    candidate, rows, catalogue = _candidate()
    projected = compile_relational_factor_execution_projection_v144(
        candidate, rows, catalogue
    )
    document = projected.public_document
    assert document["source_relational_candidate_id"] == candidate.public_document[
        "candidate_id"
    ]
    assert document["finite_relations_lowered_to_typed_conditionals"] is True
    assert any(
        "E12" in repr(row["expression"]) for row in projected.assignments
    )
    assert all("E04" not in repr(row["expression"]) for row in projected.assignments)
    assert all("E03" not in repr(row["expression"]) for row in projected.assignments)


def test_v144_rejects_incomplete_relation_support():
    candidate, rows, catalogue = _candidate()
    expression = next(
        row["expression"]
        for row in candidate.assignments
        if "E04" in repr(row["expression"])
    )

    def relation_node(value):
        if type(value) is list:
            if value[:1] == ["E04"]:
                return value
            for item in value[1:]:
                found = relation_node(item)
                if found is not None:
                    return found
        return None

    relation = relation_node(expression)
    assert relation is not None
    binding = {
        "constants": {},
        "relations": {relation[1]: [[catalogue[0].fields[0], 1]]},
    }
    with pytest.raises(GenericRelationalFactorExecutionProjectionV144Error):
        _lower_expression(copy.deepcopy(expression), binding, catalogue)

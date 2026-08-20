import hashlib
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_action_applicability_model_v87 import (
    MODEL_ARTIFACT_ID,
    load_action_applicability_model_v87,
)
from acfqp.generic_action_applicability_compiler_v58 import (
    compile_action_applicability_program_v58,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v87_action_applicability_artifact_is_source_only_and_exact():
    document = load_action_applicability_model_v87()
    assert document["model_artifact_id"] == MODEL_ARTIFACT_ID
    assert document["target_outcome_input_present"] is False
    assert document["applicability_used_as_safety_authority"] is False
    program = document["action_applicability_program"]
    assert program["training_exact_candidate_count"] == 1
    assert program["training_exact"] is True
    assert program["heldout_exact"] is True
    assert program["selected_program"] == {
        "schema": "acfqp.generic_action_applicability_relation.v58",
        "opcode": "EQ",
        "state_column": 4,
        "action_field": 4,
        "result_type": "BOOL",
        "semantic_names_used": False,
    }
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_ACTION_APPLICABILITY_V87") != "1",
    reason="explicit reconstruction from frozen V85r1 source bytes",
)
def test_v87_action_applicability_reconstructs_from_frozen_source():
    source_path = Path(
        ".tmp/exact-freeze/v85r1_projected_disagreement_campaign.json"
    )
    raw = source_path.read_bytes()
    source = loads_canonical_json(raw)
    expected = load_action_applicability_model_v87()[
        "action_applicability_program"
    ]
    actual = compile_action_applicability_program_v58(
        source,
        source_campaign_id=source["campaign_id"],
        source_campaign_sha256=hashlib.sha256(raw).hexdigest(),
        source_model_id=expected["source_model_id"],
    )
    assert actual == expected

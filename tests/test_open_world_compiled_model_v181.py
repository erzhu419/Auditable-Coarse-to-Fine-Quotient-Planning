from __future__ import annotations

from acfqp.open_world_compiled_model_v181 import (
    certify_receding_action_v181,
    compile_world_model_v181,
)
from acfqp.open_world_transition_oracle_v181 import (
    manifest_commitment_v181,
    reveal_opaque_transition_oracle_v181,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _manifest():
    return {
        "schema": "acfqp.opaque_transition_manifest.v181",
        "manifest_index": 98,
        "reveal_salt": "8" * 64,
        "state_width": 4,
        "action_width": 1,
        "horizon": 5,
        "moduli": [5, 4, 3, 6],
        "transition_programs": [
            ["MOD", ["ADD", ["S", 0], ["A", 0]], ["K", 5]],
            ["S", 1],
            ["MOD", ["ADD", ["S", 2], ["W", 0]], ["K", 3]],
            ["MAX", ["K", 0], ["SUB", ["S", 3], ["K", 1]]],
        ],
        "terminal_program": [
            "AND",
            ["EQ", ["S", 0], ["K", 0]],
            ["EQ", ["S", 3], ["K", 0]],
        ],
        "support": [[0], [1]],
        "iid_initial_seed_root": "compiled-development-only",
    }


def _observations():
    manifest = _manifest()
    oracle = reveal_opaque_transition_oracle_v181(
        manifest_bytes=canonical_json_bytes(manifest),
        expected_commitment=manifest_commitment_v181(manifest),
    )
    rows = []
    query_index = 0
    for s0 in range(5):
        for s2 in range(3):
            for s3 in range(3):
                action = ((s0 + s2 + s3) % 3,)
                rows.append(
                    oracle.query(
                        occurrence_index=0,
                        query_index=query_index,
                        state=(s0, (s0 + s2) % 4, s2, s3),
                        action=action,
                    )
                )
                query_index += 1
                rows.append(
                    oracle.query(
                        occurrence_index=0,
                        query_index=query_index,
                        state=(s0, (s0 + s2) % 4, s2, s3),
                        action=action,
                    )
                )
                query_index += 1
    return oracle, tuple(rows)


def test_compiler_derives_program_factors_and_partial_support() -> None:
    oracle, rows = _observations()
    model = compile_world_model_v181(
        rows,
        maximum_enumeration_events_per_expression=500_000,
    )
    assert model.state_width == 4
    assert model.action_width == 1
    assert model.source_label_count == len(rows)
    assert model.factor_boundaries
    assert any(not row.exact_on_source for row in model.coordinates)
    assert model.to_document()["finite_candidate_program_catalog_used"] is False
    state = oracle.initial_state(3)
    assert model.predict_support(state, (1,))


def test_higher_horizon_planner_consumes_only_compiled_model() -> None:
    oracle, rows = _observations()
    model = compile_world_model_v181(
        rows,
        maximum_enumeration_events_per_expression=500_000,
    )
    certificate = certify_receding_action_v181(
        model,
        state=(1, 0, 0, 2),
        legal_actions=oracle.legal_actions(),
        horizon=5,
    )
    assert certificate.certified is True
    assert certificate.selected_action is not None
    assert certificate.horizon == 5
    assert certificate.planning_compute_events > 0


def test_archive_references_are_generic_subexpressions_not_program_templates() -> None:
    _, rows = _observations()
    first = compile_world_model_v181(
        rows,
        maximum_enumeration_events_per_expression=500_000,
    )
    second = compile_world_model_v181(
        rows,
        maximum_enumeration_events_per_expression=500_000,
        archive=first.reusable_subprogram_archive(),
    )
    assert second.archive_reference_count > 0
    assert second.to_document()["whole_program_template_used"] is False

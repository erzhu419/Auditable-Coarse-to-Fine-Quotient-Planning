from acfqp.open_world_composite_macro_machine_v185 import (
    discover_composite_macro_library_v185,
    synthesize_composite_macro_scalar_program_v185,
)
from acfqp.open_world_universal_machine_v182 import MachineSynthesisRowV182


def _source_model_document(repetitions: int = 12) -> dict:
    expression = [
        "SUBSAT",
        ["ADD", ["INPUT", 0], ["INPUT", 2]],
        ["INPUT", 1],
    ]
    coordinates = [
        {
            "expression": expression,
            "program_id": f"{index + 1:064x}",
        }
        for index in range(repetitions)
    ]
    return {
        "schema": "acfqp.fair_ranked_compiled_world_model.v184",
        "compiled_model_id": "a" * 64,
        "source_observation_ids": ["b" * 64, "c" * 64],
        "coordinates": coordinates,
        "terminal_synthesis": {
            "expression": ["ISZERO", ["INPUT", 1]],
            "program_id": "d" * 64,
        },
        "candidate_language_countably_infinite": True,
        "finite_candidate_catalog_used": False,
        "new_primitive_opcode_invented": False,
    }


def test_v185_discovers_only_positive_mdl_anonymous_composite_operators() -> None:
    library = discover_composite_macro_library_v185((_source_model_document(),))
    document = library.to_document()
    assert library.macros
    selected = next(
        row
        for row in document["macros"]
        if row["body"]
        == [
            "SUBSAT",
            ["ADD", ["ARG", 0], ["ARG", 1]],
            ["ARG", 2],
        ]
    )
    assert selected["mdl_gain_tokens"] > 0
    assert selected["leaf_roles_anonymized"] is True
    assert selected["predeclared_reusable_factor_slot_used"] is False
    assert selected["reusable_composite_operator_invented"] is True
    assert selected["new_low_level_primitive_opcode_invented"] is False
    assert document["predeclared_reusable_factor_slots"] == []
    assert document["predeclared_macro_bodies"] == []
    assert document["arbitrary_domain_transfer_claimed"] is False


def test_v185_macro_is_rebound_and_exactly_revalidated_on_current_rows() -> None:
    library = discover_composite_macro_library_v185((_source_model_document(),))
    rows = tuple(
        MachineSynthesisRowV182(
            (x, y),
            (action,),
            max(x + action - y, 0),
        )
        for x, y, action in (
            (0, 0, 0),
            (0, 1, 1),
            (1, 0, 1),
            (1, 2, 0),
            (2, 1, 0),
            (2, 2, 1),
            (3, 0, 0),
            (3, 2, 1),
        )
    )
    result = synthesize_composite_macro_scalar_program_v185(
        rows,
        macro_library=library,
        maximum_macro_candidate_evaluations=500,
        maximum_fair_enumeration_events=20_000,
        resource_step_cap=64,
        register_count=6,
        maximum_residual_support=1,
    )
    document = result.to_document()
    assert result.selected_macro_id is not None
    assert result.residual_values == ()
    assert document["macro_candidate_selected"] is True
    assert document["fair_fallback_used"] is False
    assert document["target_rows_revalidated_exactly"] is True
    assert document["reusable_composite_operator_used"] is True
    assert document["new_low_level_primitive_opcode_invented"] is False


def test_v185_rejects_non_mdl_macro_without_upgrading_failure_to_infeasibility() -> None:
    library = discover_composite_macro_library_v185(
        (_source_model_document(repetitions=3),)
    )
    assert library.macros == ()
    document = library.to_document()
    assert document["reusable_composite_operator_invented"] is False
    assert document["arbitrary_domain_transfer_claimed"] is False

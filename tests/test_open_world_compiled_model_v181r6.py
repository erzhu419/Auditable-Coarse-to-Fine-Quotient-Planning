from acfqp.open_world_compiled_model_v181r6 import compile_world_model_v181r6
from acfqp.open_world_transition_oracle_v181 import RawTransitionObservationV181


def _rows() -> tuple[RawTransitionObservationV181, ...]:
    rows = []
    query = 0
    for state0 in range(5):
        for state1 in range(3):
            for action in range(3):
                for noise in (0, 1):
                    successor = (
                        (state0 + action) % 5,
                        (state1 + action + noise) % 3,
                    )
                    rows.append(
                        RawTransitionObservationV181(
                            0,
                            query,
                            (state0, state1),
                            (action,),
                            successor,
                            successor[0] == 0,
                            f"{query:064x}",
                        )
                    )
                    query += 1
    return tuple(rows)


def test_compiler_models_deterministic_and_partial_cyclic_coordinates() -> None:
    rows = _rows()
    model = compile_world_model_v181r6(
        rows,
        maximum_enumeration_events_per_expression=500_000,
    )
    assert model.observed_carrier_moduli == (5, 3)
    assert model.coordinates[0].residual_values == (0,)
    assert model.coordinates[1].residual_values == (0, 1)
    assert all(
        row.successor in model.predict_support(row.state, row.action)
        for row in rows
    )
    assert all(model.terminal(row.successor) is row.terminal for row in rows)
    document = model.to_document()
    assert document["cyclic_residual_search_applied_to_every_integer_coordinate"] is True
    assert document["finite_candidate_program_catalog_used"] is False
    assert document["archive_mdl_discount_used"] is False
    assert document["archive_reference_revalidated_on_current_rows"] is True


def test_compiled_support_wraps_inside_observed_carrier() -> None:
    model = compile_world_model_v181r6(
        _rows(),
        maximum_enumeration_events_per_expression=500_000,
    )
    support = model.predict_support((4, 2), (2,))
    assert support == ((1, 1), (1, 2))

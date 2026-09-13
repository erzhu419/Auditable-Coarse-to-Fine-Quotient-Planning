"""Small explicit graph: recursive equality, risk separation, and paid routing."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_compositional_contract_v69 import (
    build_model, load_model, model_payload, route_observation,
)
from acfqp.science.controlled_predictive_quotient_v1 import Query, plan


LEDGER = dict(builds=[], routing=[], planner_calls=0)


class ToyRule:
    """Two different H2 states have recursively identical action consequences."""
    def classify(self, board, work):
        work['toy_classifications'] += 1
        state = board[0]
        if state == 8:
            return 'LOST', ()
        if state == 9:
            return 'WON', ()
        graph = {0: (('LEFT', 1, 0), ('RIGHT', 2, 0)),
                 1: (('SAFE', 3, 0), ('RISK', 4, 0)),
                 2: (('SAFE', 5, 0), ('RISK', 6, 0)),
                 3: (('GO', 9, 4),), 5: (('GO', 9, 4),),
                 4: (('GO', 8, 8),), 6: (('GO', 8, 8),),
                 7: (('GO', 9, 0),)}
        return 'ACTIVE', tuple((a, (s,), r) for a, s, r in graph[state])

    def successors_from_afterstate(self, moved, score, work):
        work['toy_spawn_calls'] += 1
        if moved == (1,):
            support = ((Fraction(1, 3), (1,)), (Fraction(2, 3), (2,)))
        elif moved == (9,) and score == 4:
            support = ((Fraction(1, 3), (9,)), (Fraction(2, 3), (7,)))
        else:
            support = ((Fraction(1), moved),)
        return tuple((p, s, Fraction(score, 2048)) for p, s in support)

    def to_payload(self):
        return {'toy': 'recursive-contract'}

    @classmethod
    def from_payload(cls, payload):
        assert payload == {'toy': 'recursive-contract'}
        return cls()


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_compositional_contract_v69.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    payload['attempts'].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
                                   scope='explicit toy graph only; no source or main target boards', **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def build(variant, max_states=200_000):
    result = build_model((0,), 3, ToyRule(), variant, max_states)
    LEDGER['builds'].append(dict(variant=variant, counts=result.counts, elapsed_seconds=result.elapsed_seconds))
    return result


def test_composition_merges_higher_layers_and_preserves_risk_dependent_decisions():
    full, composed = build('FULL'), build('COMPOSED')
    assert full.counts['concrete_states'] == composed.counts['concrete_states']
    assert full.counts['concrete_action_rows'] == composed.counts['concrete_action_rows']
    assert full.counts['h0_boards_generated'] == composed.counts['h0_boards_generated'] > 0
    assert full.counts['active_cells_by_h'][2] == 2
    assert composed.counts['active_cells_by_h'][2] == 1
    assert composed.encoding[2, (1,)] == composed.encoding[2, (2,)]
    assert composed.encoding[1, (3,)] != composed.encoding[1, (4,)]
    observed = []
    for query, expected in ((Query(), 8/2048), (Query(1, 1, 1), 1/3 + 4/2048)):
        solutions = []
        for result in (full, composed):
            compiled, _ = load_model(model_payload(result), ToyRule)
            solutions.append(plan(compiled, query))
            LEDGER['planner_calls'] += 1
        assert solutions[0].values[full.model.roots[0]] == pytest.approx(expected)
        for key, old_state in full.encoding.items():
            assert solutions[0].values[old_state] == pytest.approx(solutions[1].values[composed.encoding[key]])
        observed.append(solutions[1].policy[composed.encoding[2, (1,)]])
    assert observed == ['RISK', 'SAFE']


def test_portable_rows_keep_exact_probabilities_and_route_without_members():
    result = build('COMPOSED')
    payload = json.loads(json.dumps(model_payload(result)))
    assert set(payload) == {'schema', 'variant', 'rule', 'cells', 'roots', 'rows'}
    assert any(q == 3 for _, _, row in payload['rows'] for _, q, _, _, _ in row)
    compiled, rule = load_model(payload, ToyRule)
    assert all(cell.members == () for cell in compiled.cells.values())
    for (h, board), state in result.encoding.items():
        work = Counter()
        assert route_observation(board, h, rule, compiled, work) == state
        LEDGER['routing'].append(dict(horizon=h, board=board, counts=dict(work)))
        assert work['routing_index_cells'] == len(compiled.cells)
        if h:
            assert work['routing_concrete_states'] > 1
    assert result.model.terminal[result.encoding[0, (7,)]] == 'CUTOFF'
    assert result.model.terminal[result.encoding[0, (8,)]] == 'LOST'
    assert result.model.terminal[result.encoding[0, (9,)]] == 'WON'


def test_resource_cap_charges_concrete_support_even_when_cells_merge():
    with pytest.raises(ValueError, match='max_states=5') as caught:
        build_model((0,), 3, ToyRule(), 'COMPOSED', max_states=5)
    assert caught.value.counts['concrete_states'] == 5
    assert caught.value.elapsed_seconds > 0
    LEDGER['cap_failure'] = dict(counts=caught.value.counts,
                                elapsed_seconds=caught.value.elapsed_seconds)

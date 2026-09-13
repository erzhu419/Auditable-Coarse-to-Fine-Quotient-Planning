"""Tiny independent kernels exercise compositional novelty and terminal auditing."""
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.science.controlled_predictive_causal_audit_v67 import compute_reference
from acfqp.science.controlled_predictive_compositional_audit_v69 import audit
from acfqp.science.controlled_predictive_learned_audit_v68 import recursive_support
from acfqp.science.controlled_predictive_quotient_v1 import (
    FiniteModel, Outcome, Query, build_quotient, compile_full_state, plan,
)

WORK = Counter()


@pytest.fixture(scope='session', autouse=True)
def ledger():
    yield
    root = Path(__file__).resolve().parents[1]
    (root/'reports/controlled_predictive_compositional_v69.audit_checks.json').write_text(
        json.dumps(dict(schema='acfqp.compositional_audit_checks.v69', counts=dict(WORK),
            main_cohort_roots=0, environment_samples=0, learning_updates=0,
            scope='Two tiny hand kernels, including deliberately corrupted terminal semantics.'), indent=2)+'\n')


def fixture():
    ground = FiniteModel({0:2, 1:2, 2:1, 3:1, 4:0, 5:0, 6:0},
        {0:'ACTIVE', 1:'ACTIVE', 2:'ACTIVE', 3:'ACTIVE', 4:'WON', 5:'LOST', 6:'CUTOFF'},
        {(0,'risk'):(Outcome(1.,2,0.),), (0,'safe'):(Outcome(1.,3,0.),),
         (1,'risk'):(Outcome(1.,2,0.),), (1,'safe'):(Outcome(1.,3,0.),),
         (2,'finish'):(Outcome(.5,4,2.), Outcome(.5,5,2.)),
         (3,'finish'):(Outcome(1.,6,1.),)}, (0,1))
    boards = {s: (s,)*16 for s in ground.layers}
    closure = SimpleNamespace(model=ground, boards=boards, root_names=('first','second'))
    teacher = FiniteModel({s:h for s,h in ground.layers.items() if h < 2},
        {s:t for s,t in ground.terminal.items() if ground.layers[s] < 2},
        {(s,a):row for (s,a),row in ground.rows.items() if ground.layers[s] < 2}, (2,3))
    support = recursive_support(teacher)
    quotient = build_quotient(ground)
    candidate = FiniteModel({s:d.layer for s,d in quotient.cells.items()},
        {s:d.terminal for s,d in quotient.cells.items()}, quotient.rows, quotient.roots)
    encoding = {(ground.layers[s],boards[s]):quotient.state_to_cell[s] for s in ground.layers}
    WORK['tiny_source_support_calls'] += 1
    WORK['tiny_quotient_calls'] += 1
    return closure, SimpleNamespace(model=candidate, encoding=encoding), support


def checked(closure, build, support):
    queries = {'reward':Query(), 'risk':Query(failure_penalty=4.)}
    compiled = compile_full_state(build.model)
    solutions = {n:plan(compiled,q) for n,q in queries.items()}
    reference = compute_reference(closure, queries)
    result = audit(build, compiled, closure, queries, solutions, reference, support)
    WORK.update(reference.counts)
    WORK.update(result['counts'])
    for p in solutions.values():
        WORK.update({'planning_' + k:v for k,v in p.counts.items()})
    WORK['audit_calls'] += 1
    return result


def test_new_two_step_semantics_can_be_correct_and_merged():
    closure, build, support = fixture()
    before = dict(support.registry)
    result = checked(closure, build, support)
    assert result['engineering_complete'] and result['scientific_correct']
    assert result['strict_query_switches'] == dict(required=2, violations=0, preserved=True)
    assert result['by_horizon']['2']['candidate_active_cells'] == 1
    assert result['by_horizon']['2']['collapsed_concrete_states'] == 1
    assert result['novel_semantics']['2']['source_unsupported_states'] == 2
    assert result['novel_semantics']['2']['new_recursive_correct_and_all_query_optimal_states'] == 2
    assert result['novel_semantics']['1']['source_unsupported_states'] == 0
    assert support.registry == before


def test_terminal_corruption_invalidates_recursive_novelty():
    closure, build, support = fixture()
    goal = next(s for s,t in build.model.terminal.items() if t == 'WON')
    build.model = replace(build.model, terminal={**build.model.terminal, goal:'LOST'})
    result = checked(closure, build, support)
    assert result['engineering_complete'] and not result['scientific_correct']
    assert result['errors']['layer_or_terminal_difference'] == 1
    assert result['novel_semantics']['2']['new_recursive_correct_states'] == 0

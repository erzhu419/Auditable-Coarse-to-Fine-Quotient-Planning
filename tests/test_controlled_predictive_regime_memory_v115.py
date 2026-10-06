"""Causal spawn-only learning, local routing and exact retained-state resumption."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest
from acfqp.science import controlled_predictive_regime_memory_v115 as m
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

WORK = Counter()
A = [2] * 26 + [1] * 230
B = [2] * 20 + [1] * 44
RETURN = [2] * 6 + [1] * 58


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_regime_memory_v115.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), environment_transitions=0, model_transitions=0,
        neural_model_fits=0, optimizer_steps=0, neural_candidate_predictions=0,
        scope='Fixed synthetic post-action rank sequences; no environment sampling or planning.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def consume(memory, ranks):
    before = memory.counts.copy()
    predictions, events = [], []
    for rank in ranks:
        predictions.append(memory.predict())
        event = memory.observe(rank)
        if event is not None:
            events.append(event)
    WORK.update({key: value - before[key] for key, value in memory.counts.items()})
    return predictions, events


def test_all_methods_start_without_probability_information_and_share_warmup():
    expected = []
    fours = 0
    for index, rank in enumerate(A):
        expected.append((1 + fours) / (2 + index))
        fours += rank == 2
    for method in m.METHODS:
        memory = m.SpawnMemory(method)
        predictions, events = consume(memory, A)
        assert predictions == expected and predictions[0] == .5
        assert len(events) == 1 and events[0]['kind'] == 'initialized'
        assert events[0]['obs_index'] == events[0]['block_n'] == 256
        assert events[0]['block_fours'] == 26
        assert memory.modules == [dict(id=0, alpha=27, beta=231, visits=1)]
        assert memory.module_id == 0 and memory.counts['beta_updates'] == 256
    template = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(1, 1000)), (2, Fraction(999, 1000))), 'uniform')
    rule = memory.to_rule(template)
    assert rule.program is template.program and rule.spawn_location == template.spawn_location
    assert rule.goal_rank == template.goal_rank
    assert rule.spawn_distribution == ((1, Fraction(231, 258)), (2, Fraction(27, 258)))
    assert template.spawn_distribution[1][1] == Fraction(999, 1000)


def test_frozen_pool_and_recent_preserve_their_declared_evidence():
    for method, represented in (('FROZEN', A), ('POOLED', A + B), ('RECENT', (A + B)[-256:])):
        memory = m.SpawnMemory(method)
        consume(memory, A + B)
        active = memory.modules[0]
        assert active['alpha'] == 1 + represented.count(2)
        assert active['beta'] == 1 + represented.count(1)
        payload = memory.to_payload()
        assert payload['stored_observation_counts']['statistics'] == len(represented)
        assert payload['stored_observation_counts']['pending'] == 0
        assert payload['stored_observation_counts']['raw'] == (256 if method == 'RECENT' else 0)
        assert memory.counts['routing_blocks'] == memory.counts['module_creations'] == 0
        assert memory.counts['observations_received'] == 320


def test_changed_block_is_local_and_return_reactivates_unchanged_old_module():
    memory = m.SpawnMemory('LIBRARY'); consume(memory, A)
    old = deepcopy(memory.modules[0])
    predictions, events = consume(memory, B)
    assert predictions == [float(Fraction(27, 258))] * 64
    assert len(events) == 1 and events[0]['kind'] == 'created'
    assert events[0]['obs_index'] == 320 and memory.module_id == 1
    assert memory.modules[0] == old
    assert memory.modules[1] == dict(id=1, alpha=21, beta=45, visits=1)
    saved_new = deepcopy(memory.modules[1])
    predictions, events = consume(memory, RETURN)
    assert predictions == [float(Fraction(21, 66))] * 64
    assert len(events) == 1 and events[0]['kind'] == 'reactivated'
    assert events[0]['previous_module_id'] == 1 and events[0]['module_id'] == 0
    assert memory.modules[1] == saved_new
    assert memory.modules[0] == dict(id=0, alpha=33, beta=289, visits=2)
    assert memory.counts['routing_blocks'] == 2 and memory.counts['candidate_predictive_scores'] == 5
    assert memory.counts['module_creations'] == memory.counts['module_reactivations'] == 1
    assert memory.counts['beta_updates'] == 384


@pytest.mark.parametrize('method', m.METHODS)
def test_serialization_preserves_partial_blocks_and_chunk_independent_future(method):
    memory = m.SpawnMemory(method)
    consume(memory, A[:113]); consume(memory, A[113:] + B[:17])
    payload = memory.to_payload(); saved = deepcopy(payload)
    resumed = m.SpawnMemory.from_payload(json.loads(json.dumps(payload)))
    assert resumed.to_payload() == payload
    if method == 'LIBRARY':
        assert payload['pending'] == dict(n=17, fours=17)
        assert payload['stored_observation_counts'] == dict(statistics=256, pending=17, raw=0)
    before = consume(memory, B[17:] + RETURN)
    after_a = consume(resumed, B[17:] + RETURN[:7])
    after_b = consume(resumed, RETURN[7:])
    assert before == (after_a[0] + after_b[0], after_a[1] + after_b[1])
    assert memory.to_payload() == resumed.to_payload()
    assert payload == saved


def test_existing_score_tie_keeps_older_module_id():
    memory = m.SpawnMemory('LIBRARY'); consume(memory, A)
    memory.modules.append(dict(memory.modules[0], id=1))
    memory.active_module_id = 1
    _, events = consume(memory, RETURN)
    assert events[0]['existing_log_scores'][0]['log_score'] == events[0]['existing_log_scores'][1]['log_score']
    assert events[0]['kind'] == 'reactivated' and memory.module_id == 0
    assert memory.counts['module_creations'] == 0

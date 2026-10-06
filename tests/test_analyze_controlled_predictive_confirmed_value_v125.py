"""Independent accounting catches causal/queue mutations and incomplete cohorts."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from acfqp.science.controlled_predictive_confirmed_value_v125 import ConfirmedValueBank
from scripts import analyze_controlled_predictive_confirmed_value_v125 as analysis

ROOT = Path(__file__).resolve().parents[1]
INITIAL = [2] * 26 + [1] * 230
BOARD = [1, 1] + [0] * 14


class ValueFixture:
    def __init__(self):
        self.rule = SimpleNamespace(goal_rank=11)
        self.weights = np.zeros(1)
        self.counts, self.setup_counts = Counter(), Counter()
        self.updates, self.setup_seconds = 0, 0.

    def update(self, board, target, alpha):
        self.updates += 1
        self.counts.update(td_updates=1, table_update_occurrences=32)


def make_row(model, ranks, status='CUTOFF'):
    before = dict(model.counts)
    row = dict(method='DELAY', query='risk_goal', spawned_ranks=list(ranks),
        context_ids=[], bank_ids=[], routing_events=[], commit_events=[],
        td_targets=[], target_context_ids=[], result=dict(steps=len(ranks), status=status,
            router_observations_before=model.router.observations_seen,
            pending_before=len(model.pending_transitions)))
    for index, rank in enumerate(ranks):
        origin = model.context_id
        row['context_ids'].append(origin); row['bank_ids'].append(0)
        event = model.observe(rank)
        if event is not None: row['routing_events'].append(dict(event, observed_action_index=index))
        final = index == len(ranks) - 1
        target = (-4. if status == 'LOST' else None) if final else 1.
        target_context = None if final else model.context_id
        row['td_targets'].append(target); row['target_context_ids'].append(target_context)
        commit = model.finish_transition(BOARD if target is not None else None, origin, target, target_context)
        if commit is not None: row['commit_events'].append(dict(commit, observed_action_index=index))
    row['final_context_id'] = model.context_id
    row['result'].update(router_observations_after=model.router.observations_seen,
        pending_after=len(model.pending_transitions),
        learning_counts={key: value - before.get(key, 0) for key, value in model.counts.items()
                         if value != before.get(key, 0)})
    return row


def test_independent_replay_matches_confirmed_censor_and_target_counts():
    model = ConfirmedValueBank(ValueFixture(), INITIAL, ROOT / 'reports', method='DELAY')
    row = make_row(model, [2] * 192)
    state = analysis.initial_state(INITIAL, 0, 'DELAY')
    result = analysis.replay_game(row, state)
    assert all(result['checks'].values())
    assert result['applied'] == 63 and result['censored'] == 128
    assert state['updates'] == model.updates
    assert state['router'].to_payload() == model.router.to_payload()


def test_action_or_bootstrap_context_tampering_fails_causal_checks():
    model = ConfirmedValueBank(ValueFixture(), INITIAL, ROOT / 'reports', method='DELAY')
    row = make_row(model, [2] * 128)
    changed = deepcopy(row); changed['context_ids'][127] = 1
    result = analysis.replay_game(changed, analysis.initial_state(INITIAL, 0, 'DELAY'))
    assert not result['checks']['causal_contexts']
    changed = deepcopy(row); changed['target_context_ids'][0] = 1
    result = analysis.replay_game(changed, analysis.initial_state(INITIAL, 0, 'DELAY'))
    assert not result['checks']['td_targets']


def test_commit_censor_mutation_and_loss_target_mutation_are_rejected():
    model = ConfirmedValueBank(ValueFixture(), INITIAL, ROOT / 'reports', method='DELAY')
    row = make_row(model, [2] * 128, status='LOST')
    changed = deepcopy(row); changed['commit_events'][0]['censored'] -= 1
    result = analysis.replay_game(changed, analysis.initial_state(INITIAL, 0, 'DELAY'))
    assert not result['checks']['commit_events']
    changed = deepcopy(row); changed['td_targets'][-1] = 0.
    result = analysis.replay_game(changed, analysis.initial_state(INITIAL, 0, 'DELAY'))
    assert not result['checks']['td_targets']


def test_pending_evidence_survives_game_boundary_and_matches_manifest():
    model = ConfirmedValueBank(ValueFixture(), INITIAL, ROOT / 'reports', method='DELAY')
    first = make_row(model, [2] * 70)
    second = make_row(model, [2] * 58, status='LOST')
    state = analysis.initial_state(INITIAL, 0, 'DELAY')
    assert all(analysis.replay_game(first, state)['checks'].values())
    assert len(state['pending']) == 70
    assert all(analysis.replay_game(second, state)['checks'].values())
    assert not state['pending']
    assert state['router'].to_payload() == model.to_payload()['router']
    assert state['bank_updates'] == {row['bank_id']: row['updates'] for row in model.to_payload()['banks']}


def test_missing_outer_game_invalidates_lifecycle_and_aggregate_comparison():
    indexed, valid, cps = {}, {}, {}
    for phase in analysis.PHASES:
        for method in ('FROZEN_A',) + analysis.METHODS:
            for label in ((0,) if method == 'FROZEN_A' else analysis.LABELS):
                for query in analysis.QUERIES:
                    for life in analysis.LIVES:
                        cps[life, query, phase, method, label] = dict(transitions=label)
                        for replica in range(analysis.REPLICAS):
                            key = life, query, phase, method, label, replica
                            indexed[key] = dict(result=dict(score=2048, utility=1., steps=100,
                                                           seconds=.01, status='LOST'))
                            valid[key] = True
    missing = (0, 'reward', 'B', 'BANK', analysis.BUDGET, 7)
    del indexed[missing]
    result = analysis.summaries(indexed, valid, cps)
    summary = result['methods']['B']['BANK'][str(analysis.BUDGET)]['reward']
    assert not summary['complete'] and summary['lifecycle_mean']['utility'] is None
    assert result['comparisons']['B']['BANK_final_minus_CONT']['reward']['mean_deltas']['utility'] is None


def test_evaluation_charges_private_views_and_preserves_pending_router(monkeypatch):
    model = ConfirmedValueBank(ValueFixture(), INITIAL, ROOT / 'reports', method='DELAY')
    make_row(model, [2] * 70)
    manifest = model.to_payload()
    actor = model.evaluation_copy()
    row = dict(method='DELAY', query='risk_goal', spawned_ranks=[2] * 58,
        context_ids=[], bank_ids=[], routing_events=[], commit_events=[],
        td_targets=[], target_context_ids=[], result=dict(steps=58, status='LOST',
            router_observations_before=actor.router.observations_seen, pending_before=0))
    for index, rank in enumerate(row['spawned_ranks']):
        row['context_ids'].append(actor.context_id); row['bank_ids'].append(0)
        event = actor.observe(rank)
        if event is not None: row['routing_events'].append(dict(event, observed_action_index=index))
    row['final_context_id'] = actor.context_id
    row['result'].update(router_observations_after=actor.router.observations_seen,
        pending_after=0, learning_counts=dict(actor.counts))
    monkeypatch.setattr(analysis, 'DENSE_BYTES', actor.banks[0].weights.nbytes)
    state = analysis.initial_state([], model.updates, 'DELAY', manifest)
    result = analysis.replay_game(row, state, False)
    assert all(result['checks'].values())
    assert state['updates'] == model.updates
    assert model.to_payload() == manifest
    changed = deepcopy(row); changed['result']['learning_counts']['evaluation_weight_views'] = 0
    result = analysis.replay_game(changed, analysis.initial_state([], model.updates, 'DELAY', manifest), False)
    assert not result['checks']['replay_counters']

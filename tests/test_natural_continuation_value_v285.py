import gzip
import json

from acfqp.science.natural_continuation_value_v285 import continuation_seed, select_states, tail_calibration
from acfqp.science.natural_model_revision_v281 import PHASES


def test_all_predeclared_seeds_are_disjoint():
    seeds = [continuation_seed(life, phase, slot, batch, replica)
        for life in range(16) for phase in range(3) for slot in range(8)
        for batch in range(2) for replica in range(32)]
    assert len(seeds) == len(set(seeds)) == 24576


def test_retained_selection_ignores_future_outcomes(tmp_path):
    records, changed = tmp_path/'records.gz', tmp_path/'changed.gz'
    rows, switches = [], []
    for life in range(16):
        for phase, _ in PHASES:
            steps = [dict(board=[index]+[0]*15, action='DOWN', score=0) for index in range(16)]
            decisions = [dict(action='DOWN', value=1., p_four=.1, observations_before=i)
                for i in range(16)]
            rows.append(dict(kind='ONLINE', arm='LIBRARY_H2', episode_index=0,
                lifecycle=life, parent=life%4, phase=phase,
                episode=dict(seed=life, steps=steps, return_score=0, status='LOST'),
                decisions=decisions))
            switches.extend(dict(episode_index=0, lifecycle=life, phase=phase, decision=i,
                full_actions=dict(ORACLE_P='DOWN'), short_actions=dict(ORACLE_P='UP'))
                for i in range(16))
    def save(path, values):
        with gzip.open(path, 'wt') as stream:
            for value in values:
                stream.write(json.dumps(value)+'\n')
    save(records, rows)
    save(changed, switches)
    before = select_states(records, changed)
    for row in rows:
        row['episode']['return_score'] = 999999
        row['episode']['status'] = 'WON'
        for step in row['episode']['steps']:
            step['score'] = 999999
            step['next_board'] = [11]*16
    save(records, rows)
    assert select_states(records, changed) == before
    assert len(before) == 384
    assert {s['decision'] for s in before if s['group'] == 'uniform'} == {0, 4, 8, 12}
    assert {s['decision'] for s in before if s['group'] == 'competition'} == {1, 5, 9, 13}


def test_tail_calibration_removes_immediate_reward():
    states = [dict(state_id=f'{group}/{phase}', group=group, phase=phase, lifecycle=0,
        proxy_action='DOWN', full_tail_scores=dict(DOWN=7.),
        validation_means=dict(DOWN=8.), immediate_scores=dict(DOWN=4096))
        for group in ('uniform', 'competition') for phase, _ in PHASES]
    result = tail_calibration(states)
    assert all(row['mean_proxy_tail_bias'] == 1. for row in result.values())
    assert all(row['by_lifecycle'] == {'0': 1.} for row in result.values())

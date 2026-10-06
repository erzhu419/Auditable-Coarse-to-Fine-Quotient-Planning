"""Synthetic paired-half selection and history-weighting checks, without sampling."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from statistics import mean

import pytest

from acfqp.science.controlled_predictive_module_split_half_v157 import (
    METRICS, MODES, build_pairs, build_selection_rows, summarize)

TEMP = Path(__file__).resolve().parents[1]/'reports/v157_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'; data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, synthetic_work=dict(WORK), production_data_reads=0,
        environment_samples=0, model_samples=0, native_calls=0, training_updates=0))
    path.write_text(json.dumps(data, indent=2)+'\n')


def root(life=0, query='risk1', source='H2', slot=0, accept=False):
    return dict(root_id=f'{life}:{query}:{source}:{slot}', life=life, query=query,
        source_method=source, slot=slot, board=[1, 1]+[0]*14, prediction=dict(accept=accept))


def outcomes(roots, values=None):
    if values is None:
        def values(item, suffix, target):
            if target == 'H2': return (item['life']+item['slot']+1)*(1. if suffix < 8 else -1.)
            return -(item['life']+1.) if suffix < 8 else 2.*(item['life']+1)+(item['source_method'] == 'LEARN8')
    rows = []
    for index, item in enumerate(roots):
        for suffix in range(16):
            rewards = dict(H_H2=100.+suffix, M_H2=100.+suffix+values(item, suffix, 'H2'),
                H_GATE=80.+suffix, M_GATE=80.+suffix+values(item, suffix, 'GATE'))
            for mode in MODES:
                rows.append(dict(branch_id=f'{item["root_id"]}:{suffix}:{mode}', root_id=item['root_id'],
                    **{key: item[key] for key in ('life', 'query', 'source_method', 'slot')},
                    suffix=suffix, mode=mode, seed=100000+index*100+suffix,
                    root_board=list(item['board']), score=rewards[mode]*2048., steps=10+suffix,
                    status='WON', components=[rewards[mode], 0., 1.]))
    WORK['synthetic_outcomes_generated'] += len(rows)
    return list(reversed(rows))


def pair_rows(roots, data):
    WORK['build_pairs_calls'] += 1; WORK['paired_input_rows'] += len(data)
    return build_pairs(roots, data)


def selections(roots, pairs):
    WORK['build_selection_calls'] += 1
    return build_selection_rows(roots, pairs)


def summary(rows):
    WORK['summarize_calls'] += 1
    return summarize(rows)


def full_roots():
    return [root(life, query, source, slot, accept=slot % 2 == 0)
        for life in range(4) for query in ('risk1', 'risk8') for source in ('H2', 'LEARN8') for slot in range(4)]


def test_three_paired_components_recompose_each_query_instead_of_subtracting_scores_only():
    roots = [root(query=q) for q in ('risk1', 'risk8')]; data = outcomes(roots)
    for row in data:
        components = {'H_H2': [10., 0., 1.], 'M_H2': [12., 1., 0.],
            'H_GATE': [7., 1., 0.], 'M_GATE': [8., 0., 1.]}[row['mode']]
        row.update(components=components, score=components[0]*2048., status='LOST' if components[1] else 'WON')
    pairs = pair_rows(roots, data)
    assert len(pairs) == 32
    for pair in pairs:
        assert pair['components'] == dict(H2=[2., 1., -1.], GATE=[1., -1., 1.])
        assert pair['advantages'] == (dict(H2=0., GATE=3.) if pair['query'] == 'risk1' else dict(H2=-14., GATE=17.))
        assert pair['old_accept'] is False


def test_heldout_half_never_changes_training_selection_and_zero_is_rejected():
    roots = [root()]
    data = outcomes(roots, lambda item, suffix, target: (0. if suffix < 8 else 2.) if target == 'H2' else (1. if suffix < 8 else -1.))
    before = deepcopy(data); pairs = pair_rows(roots, data); rows = selections(roots, pairs)
    assert data == before and len(rows) == 4
    lookup = {(row['direction'], row['target']): row for row in rows}
    assert not lookup['A_to_B', 'H2']['accept'] and lookup['A_to_B', 'H2']['train_advantage'] == 0.
    assert lookup['B_to_A', 'H2']['accept'] and lookup['B_to_A', 'H2']['train_advantage'] == 2.
    assert lookup['A_to_B', 'H2']['train_half'] == 'A' and lookup['A_to_B', 'H2']['eval_half'] == 'B'
    changed = deepcopy(data)
    for record in changed:
        if record['suffix'] >= 8 and record['mode'] == 'M_H2':
            record['components'][0] += 10.; record['score'] += 10.*2048.
    altered = selections(roots, pair_rows(roots, changed))
    for row in altered:
        old = lookup[row['direction'], row['target']]
        if row['direction'] == 'A_to_B':
            assert row['accept'] == old['accept'] and row['train_advantage'] == old['train_advantage']
            assert row['train_components'] == old['train_components'] and row['train_advantages'] == old['train_advantages']
            assert row['eval_advantages']['H2'] == old['eval_advantages']['H2']+10.
        else:
            assert row['eval_components'] == old['eval_components']
            assert row['train_advantages']['H2'] == old['train_advantages']['H2']+10.


@pytest.mark.parametrize('corruption', ['missing', 'duplicate', 'cutoff', 'unpaired_seed'])
def test_incomplete_duplicate_or_unpaired_quartets_are_not_silently_selected(corruption):
    roots = [root()]; data = outcomes(roots)
    if corruption == 'missing': data.pop()
    elif corruption == 'duplicate': data.append(deepcopy(data[0]))
    elif corruption == 'cutoff': data[0]['status'] = 'CUTOFF'
    else: data[0]['seed'] += 1
    with pytest.raises(ValueError): pair_rows(roots, data)


def expected_row_metrics(row, eval_target):
    a, old = int(row['accept']), int(row['old_accept'])
    heldout = row['eval_advantages'][eval_target]; apparent = row['train_advantages'][eval_target]
    return dict(accept_rate=a, old_accept_rate=old, decision_change_rate=int(a != old),
        train_eval_sign_agreement=int(bool(a) == (heldout > 0.)), train_advantage=row['train_advantage'],
        eval_advantage=heldout, gain_vs_old=(a-old)*heldout, gain_vs_reject=a*heldout,
        gain_vs_accept=(a-1)*heldout, apparent_gain_vs_old=(a-old)*apparent,
        selection_optimism=(a-old)*(apparent-heldout))


def identity(cell):
    return tuple(cell[key] for key in ('query', 'target', 'eval_target', 'source_method', 'direction'))


def test_all_groups_keep_zero_change_roots_and_use_root_then_history_weights():
    roots = full_roots(); rows = selections(roots, pair_rows(roots, outcomes(roots)))
    results = summary(rows)
    assert len(rows) == 256 and len(results) == len({identity(cell) for cell in results}) == 72
    for cell in results:
        selected = [r for r in rows if r['query'] == cell['query'] and r['target'] == cell['target']
            and (cell['source_method'] == 'ALL' or r['source_method'] == cell['source_method'])
            and (cell['direction'] == 'ALL' or r['direction'] == cell['direction'])]
        assert cell['roots'] == len({r['root_id'] for r in selected})
        assert cell['row_count'] == len(selected)
        if cell['direction'] == 'ALL': assert cell['row_count'] == 2*cell['roots']
        else: assert cell['row_count'] == cell['roots']
        history_metrics = []
        for life, history in enumerate(cell['per_history']):
            local = [r for r in selected if r['life'] == life]
            by_root = {key: [expected_row_metrics(r, cell['eval_target']) for r in local if r['root_id'] == key]
                for key in {r['root_id'] for r in local}}
            expected = {key: mean(mean(x[key] for x in values) for values in by_root.values()) for key in METRICS}
            history_metrics.append(expected)
            assert history['life'] == life and history['roots'] == len(by_root) and history['row_count'] == len(local)
            for key, value in expected.items(): assert history[key] == pytest.approx(value)
        for key in METRICS: assert cell[key] == pytest.approx(mean(h[key] for h in history_metrics))
        assert cell['selection_optimism'] == pytest.approx(cell['apparent_gain_vs_old']-cell['gain_vs_old'])
        assert cell['decision_change_rate'] == .5  # Unchanged roots remain in the denominator.
    cross = next(c for c in results if identity(c) == ('risk1', 'H2', 'GATE', 'ALL', 'ALL'))
    own = next(c for c in results if identity(c) == ('risk1', 'H2', 'H2', 'ALL', 'ALL'))
    assert cross['train_eval_sign_agreement'] == 1. and own['train_eval_sign_agreement'] == 0.
    assert own['gain_vs_old'] < 0. and own['apparent_gain_vs_old'] > 0. and own['selection_optimism'] > 0.
    assert not any('ci95' in key or 'standard_error' in key or 'p_value' in key for cell in results for key in cell)


def test_swapping_halves_swaps_directions_and_leaves_all_direction_summary_unchanged():
    roots = full_roots(); data = outcomes(roots)
    original = summary(selections(roots, pair_rows(roots, data)))
    swapped = deepcopy(data)
    for row in swapped: row['suffix'] = (row['suffix']+8) % 16
    reverse = summary(selections(roots, pair_rows(roots, swapped)))
    indexed = {identity(c): c for c in original}
    for cell in reverse:
        old_id = identity(cell)
        opposite = {'ALL': 'ALL', 'A_to_B': 'B_to_A', 'B_to_A': 'A_to_B'}[cell['direction']]
        expected = indexed[(*old_id[:-1], opposite)]
        assert cell['roots'] == expected['roots'] and cell['row_count'] == expected['row_count']
        for key in METRICS: assert cell[key] == pytest.approx(expected[key])
        assert cell['per_history'] == expected['per_history']


def test_no_change_cohort_retains_every_root_and_zero_selection_gain():
    roots = full_roots()
    data = outcomes(roots, lambda item, suffix, target: 2. if item['prediction']['accept'] else 0.)
    rows = selections(roots, pair_rows(roots, data)); results = summary(rows)
    assert all(r['accept'] == r['old_accept'] for r in rows)
    for cell in results:
        assert cell['roots'] > 0 and cell['row_count'] > 0
        assert cell['accept_rate'] == cell['old_accept_rate'] == .5
        assert cell['decision_change_rate'] == cell['gain_vs_old'] == cell['apparent_gain_vs_old'] == cell['selection_optimism'] == 0.
        assert cell['train_eval_sign_agreement'] == 1.
        assert cell['gain_vs_reject'] == 1. and cell['gain_vs_accept'] == 0.

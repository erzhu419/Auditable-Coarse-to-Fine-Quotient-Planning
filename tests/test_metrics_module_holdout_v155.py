"""Synthetic grouped holdout summaries; folds never count as independent samples."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from statistics import mean

import pytest

from scripts import analyze_controlled_predictive_module_holdout_v155 as analysis

TEMP = Path(__file__).resolve().parents[1]/'reports/v155_runtime_tmp'
WORK = Counter()
ARMS = ('REPAIR_H2', 'REPAIR_GATE')
QUERIES = ('risk1', 'risk8')


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'metrics_checks.json'; result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, synthetic_work=dict(WORK), production_data_reads=0,
        environment_samples=0, model_samples=0, native_planner_calls=0, training_updates=0))
    path.write_text(json.dumps(result, indent=2)+'\n')


def utility(components, query):
    weight = 1. if query == 'risk1' else 8.
    return components[0]-weight*components[1]+weight*components[2]


def prediction(value):
    return dict(components=[float(value), 0., 0.], advantage=float(value), accept=value > 0.)


def synthetic_rows():
    result = []
    for life in (3, 0, 2, 1):
        for query in reversed(QUERIES):
            for heldout in range(4):
                fold_id = f'{life}:{query}:{4*heldout}'
                for arm in ARMS:
                    for slot in range(4):
                        for source in ('H2', 'LEARN8'):
                            old = [0., 2., -1., 1.][slot]
                            new = [0., 0., 1., 2.][slot] if arm == 'REPAIR_H2' else [0., -1., 0., 2.][slot]
                            new += .25*heldout+(.125 if source == 'LEARN8' else 0.)
                            # Opposite source and history effects prevent accidental source pooling.
                            reward = .25*life+(.5 if source == 'H2' else -.5)+slot/4.
                            targets = dict(REPAIR_H2=[reward+1., .25, 0.], REPAIR_GATE=[reward-.5, 0., .125])
                            result.append(dict(fold_id=fold_id, life=life, query=query, replica=4*heldout,
                                arm=arm, root_id=f'{life}:{query}:{source}:{slot}', source_method=source,
                                split='heldout' if slot == heldout else 'train', old_prediction=prediction(old),
                                prediction=prediction(new), targets=targets))
    WORK['synthetic_rows_generated'] += len(result)
    return result


def aggregate(rows):
    WORK['aggregate_calls'] += 1
    return analysis.aggregate(rows)


def selected(rows, split, query, source, arm, life=None):
    return [r for r in rows if r['split'] == split and r['query'] == query and r['arm'] == arm
        and (source == 'ALL' or r['source_method'] == source) and (life is None or r['life'] == life)]


def expected_metrics(rows):
    values = {}
    for row in rows:
        old, new = row['old_prediction']['advantage'], row['prediction']['advantage']
        old_accept, new_accept = old > 0., new > 0.
        h2, gate = (utility(row['targets'][key], row['query']) for key in ARMS)
        own = h2 if row['arm'] == 'REPAIR_H2' else gate
        metrics = {}
        for name, target in (('h2', h2), ('gate', gate), ('own', own)):
            old_error, new_error = (old-target)**2, (new-target)**2
            metrics.update({f'old_mse_{name}': old_error, f'new_mse_{name}': new_error,
                f'mse_change_{name}': new_error-old_error})
        metrics.update(policy_gain_change_h2=(int(new_accept)-int(old_accept))*h2,
            policy_gain_change_gate=(int(new_accept)-int(old_accept))*gate,
            old_accept_rate=float(old_accept), new_accept_rate=float(new_accept), changed_rate=float(old_accept != new_accept))
        for key, value in metrics.items(): values.setdefault(key, []).append(value)
    return {key: mean(cells) for key, cells in values.items()}


def expected_counts(rows):
    return dict(old_accepts=sum(r['old_prediction']['advantage'] > 0. for r in rows),
        new_accepts=sum(r['prediction']['advantage'] > 0. for r in rows),
        gate_changes=sum((r['old_prediction']['advantage'] > 0.) != (r['prediction']['advantage'] > 0.) for r in rows))


def test_all_source_split_and_history_summaries_match_independent_targets_and_signs():
    rows = synthetic_rows(); before = deepcopy(rows); result = aggregate(rows)
    assert rows == before and len(rows) == 512 and result['primary_complete']
    for split in ('heldout', 'train'):
        for query in QUERIES:
            for source in ('ALL', 'H2', 'LEARN8'):
                for arm in ARMS:
                    subset = selected(rows, split, query, source, arm)
                    cell = result['groups'][split][query][source][arm]
                    assert cell['complete'] and cell['records'] == len(subset)
                    assert cell['unique_roots'] == len({r['root_id'] for r in subset})
                    assert cell['counts'] == expected_counts(subset)
                    histories = [selected(subset, split, query, source, arm, life) for life in range(4)]
                    reference = [expected_metrics(history) for history in histories]
                    for name in reference[0]:
                        assert cell['means'][name] == pytest.approx(mean(h[name] for h in reference))
                    for life, history in enumerate(cell['lifecycles']):
                        assert history['life'] == life and history['records'] == len(histories[life])
                        assert history['counts'] == expected_counts(histories[life])
                        assert history['means'] == pytest.approx(reference[life])
            for arm in ARMS:
                by_source = result['groups'][split][query]
                for key, actual in by_source['ALL'][arm]['means'].items():
                    assert actual == pytest.approx((by_source['H2'][arm]['means'][key]+by_source['LEARN8'][arm]['means'][key])/2)
    for arm in ARMS:
        assert sum(result['groups']['heldout'][q]['ALL'][arm]['records'] for q in QUERIES) == 64
        assert sum(result['groups']['train'][q]['ALL'][arm]['records'] for q in QUERIES) == 192
        assert sum(result['groups']['train'][q]['ALL'][arm]['unique_roots'] for q in QUERIES) == 64


def test_each_replica_keeps_both_sources_in_one_heldout_group_and_six_training_rows():
    rows = synthetic_rows(); result = aggregate(rows)
    for split in ('heldout', 'train'):
        for query in QUERIES:
            for source in ('ALL', 'H2', 'LEARN8'):
                expected_size = (2 if split == 'heldout' else 6)//(1 if source == 'ALL' else 2)
                for arm in ARMS:
                    for cell in result['groups'][split][query][source][arm]['lifecycles']:
                        assert [f['replica'] for f in cell['folds']] == [0, 4, 8, 12]
                        for fold in cell['folds']:
                            matching = [r for r in selected(rows, split, query, source, arm, cell['life'])
                                if r['replica'] == fold['replica']]
                            assert fold['records'] == len(matching) == expected_size
                            assert fold['fold_id'] == f'{cell["life"]}:{query}:{fold["replica"]}'
                            assert fold['means'] == pytest.approx(expected_metrics(matching))
                            assert fold['counts'] == expected_counts(matching)
    # Repeated training roots remain repeated fit diagnostics, not independent heldout roots.
    training = result['groups']['train']['risk1']['ALL']['REPAIR_GATE']
    heldout = result['groups']['heldout']['risk1']['ALL']['REPAIR_GATE']
    assert training['records'] == 3*training['unique_roots']
    assert heldout['records'] == heldout['unique_roots']
    forbidden = {'conditional_seed_se', 'conditional_suffix_se', 'conditional_seed_ci95',
        'conditional_suffix_ci95', 'standard_error', 'confidence_interval', 'p_value', 'n_independent_folds'}
    def visit(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(result)


def test_strict_positive_changes_include_unchanged_roots_and_keep_mse_gain_directions_separate():
    rows = synthetic_rows()
    for row in rows:
        slot = int(row['root_id'].rsplit(':', 1)[1])
        old, new = [0., 2., -1., 1.][slot], [0., 0., 1., 2.][slot]
        row['old_prediction'], row['prediction'] = prediction(old), prediction(new)
        # Metadata correctness is audited elsewhere: numeric summaries must independently use >0.
        row['old_prediction']['accept'] = not (old > 0.)
        row['prediction']['accept'] = not (new > 0.)
        gate = [100., -4., 3., -20.][slot]
        row['targets'] = dict(REPAIR_H2=[-gate, 0., 0.], REPAIR_GATE=[gate, 0., 0.])
    result = aggregate(rows)
    for split in ('heldout', 'train'):
        for query in QUERIES:
            for source in ('ALL', 'H2', 'LEARN8'):
                for arm in ARMS:
                    cell = result['groups'][split][query][source][arm]; m = cell['means']
                    assert m['policy_gain_change_gate'] == 1.75  # (0 + 4 + 3 + 0)/4, not changed-only 3.5.
                    assert m['policy_gain_change_h2'] == -1.75
                    assert m['old_accept_rate'] == m['new_accept_rate'] == m['changed_rate'] == .5
                    assert cell['counts'] == dict.fromkeys(('old_accepts', 'new_accepts', 'gate_changes'), cell['records']//2)
                    assert m['mse_change_h2'] == -3.25  # new minus old: a negative change is an improvement.
                    assert m['mse_change_gate'] == 2.75
                    assert m['mse_change_own'] == (-3.25 if arm == 'REPAIR_H2' else 2.75)
                    assert m['new_mse_gate']-m['old_mse_gate'] == 2.75


def test_zero_gate_changes_keep_the_full_cohort_and_report_exact_zero_local_gain():
    rows = synthetic_rows()
    for row in rows:
        row['prediction'] = deepcopy(row['old_prediction'])
    result = aggregate(rows)
    assert result['primary_complete']
    for split in result['groups'].values():
        for query in split.values():
            for source in query.values():
                for cell in source.values():
                    assert cell['records'] > 0 and cell['complete']
                    assert cell['counts']['gate_changes'] == 0
                    for name in ('policy_gain_change_gate', 'policy_gain_change_h2', 'mse_change_h2', 'mse_change_gate', 'mse_change_own', 'changed_rate'):
                        assert cell['means'][name] == 0.

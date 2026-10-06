"""Synthetic V158 seed and phase-order checks without environment sampling."""
from collections import Counter
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts import run_controlled_predictive_module_precision_v158 as runner

TEMP = Path(__file__).resolve().parents[1] / 'reports/v158_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP / 'runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before,
        production_source_reads=0, environment_samples=0, native_calls=0,
        synthetic_work=dict(WORK),
        scope='Seed roster and synthetic phase-order wiring; no physical branches.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_', dir=TEMP) as folder:
        yield Path(folder)


def synthetic_roots():
    return [dict(root_id=f'{life}:{query}:{method}:{slot}', life=life, query=query,
        source_method=method, slot=slot, board=[1, 2, 1, 0] + [0] * 12,
        prediction=dict(components=[0., 0., 0.], advantage=0., accept=False))
        for life in range(4) for query in ('risk1', 'risk8')
        for method in ('H2', 'LEARN8') for slot in range(4)]


def test_paired_seed_roster_is_disjoint_across_phases_roots_and_v153():
    roots = synthetic_roots()
    roster = runner.branch_roster(roots)
    WORK['roster_rows'] += len(roster)
    assert len(roster) == 8192
    assert len({row['branch_id'] for row in roster}) == 8192
    root_index = {root['root_id']: root for root in roots}
    groups = {}
    for row in roster:
        key = (row['root_id'], row['split'], row['suffix'])
        groups.setdefault(key, []).append(row)
        assert row['seed'] == runner.branch_seed(root_index[row['root_id']], row['split'], row['suffix'])
    assert len(groups) == 4096
    assert {row['split'] for row in roster} == {'TRAIN', 'EVAL'}
    assert {row['suffix'] for row in roster} == set(range(32))
    seeds = []
    for group in groups.values():
        assert len(group) == 2 and {row['mode'] for row in group} == {'H_GATE', 'M_GATE'}
        assert group[0]['seed'] == group[1]['seed']
        seeds.append(group[0]['seed'])
    assert len(set(seeds)) == 4096
    v153_seeds = {153 * 100000000 + 20000000 + root['life'] * 1000000
        + ('risk1', 'risk8').index(root['query']) * 100000
        + ('H2', 'LEARN8').index(root['source_method']) * 10000 + root['slot'] * 100 + suffix
        for root in roots for suffix in range(16)}
    assert set(seeds).isdisjoint(v153_seeds)


def test_all_training_and_selectors_are_frozen_before_evaluation(local_tmp, monkeypatch):
    roots = synthetic_roots()
    capsule = dict(roots=roots, snapshots=[], models=[], cost_refs=[{'path': 'synthetic'}])
    output = local_tmp / 'experiment'
    events, saved, phase_results = [], {}, {}
    selectors = [dict(root_id=root['root_id'], budget=budget, accept=budget > 8)
                 for root in roots for budget in (8, 16, 32)]

    def source(directory):
        assert directory == output
        events.append('source')
        return capsule

    def snapshot(directory):
        assert runner.read(directory / 'source_capsule.json') == capsule
        path = directory / 'source/synthetic.py'
        path.parent.mkdir()
        path.write_text('# synthetic snapshot\n')
        events.append('snapshot')

    def sample(split, received, directory):
        assert received == capsule and directory == output
        WORK['sample_phase_stubs'] += 1
        state = runner.read(directory / 'run.json')
        if split == 'TRAIN':
            assert events == ['source', 'snapshot']
            assert state['status'] == 'training' and state['phases'] == {}
            frozen = runner.read(directory / 'frozen_inputs.json')
            assert frozen['status'] == 'frozen' and frozen['roots'] == roots
            assert len(frozen['branch_roster']) == 8192
            assert (directory / 'source/synthetic.py').exists()
            assert not (directory / 'frozen_selectors.json').exists()
            saved['inputs'] = (directory / 'frozen_inputs.json').read_bytes()
        else:
            assert events == ['source', 'snapshot', 'TRAIN_complete', 'TRAIN_pairs', 'selectors']
            assert state['status'] == 'selectors_frozen' and state['selectors'] == 192
            assert state['phases'] == {'TRAIN': phase_results['TRAIN']}
            assert runner.read(directory / 'train_pairs.json') == [{'split': 'TRAIN', 'rows': 8}]
            assert runner.read(directory / 'frozen_selectors.json') == selectors
            saved['selectors'] = (directory / 'frozen_selectors.json').read_bytes()
        lifecycles = []
        for life in range(4):
            outcomes = [dict(life=life, split=split, mode=mode, steps=life + 1,
                status='cutoff' if split == 'EVAL' and life == 0 and mode == 'M_GATE' else 'loss')
                for mode in ('H_GATE', 'M_GATE')]
            ref = f'{split.lower()}/life_{life}/outcomes.json'
            path = directory / ref
            path.parent.mkdir(parents=True)
            runner.save(path, outcomes)
            lifecycles.append(dict(life=life, split=split, outcomes_ref=ref,
                physical_branches=2, environment_counts={'transitions': 2 * (life + 1)},
                statuses=dict(Counter(row['status'] for row in outcomes))))
        result = dict(split=split, lifecycles=lifecycles, seconds=0.)
        phase_results[split] = result
        events.append(f'{split}_complete')
        return result

    def pairs(received_roots, outcomes, split):
        assert received_roots == roots and events[-1] == f'{split}_complete'
        assert len(outcomes) == 8 and {row['life'] for row in outcomes} == set(range(4))
        assert all(row['split'] == split for row in outcomes)
        WORK['synthetic_compact_rows_read'] += len(outcomes)
        events.append(f'{split}_pairs')
        return [{'split': split, 'rows': len(outcomes)}]

    def freeze(received_roots, train_pairs):
        assert events[-1] == 'TRAIN_pairs' and received_roots == roots
        assert train_pairs == [{'split': 'TRAIN', 'rows': 8}]
        assert not (output / 'eval').exists()
        events.append('selectors')
        return selectors

    def evaluate(received_selectors, eval_pairs):
        assert events[-1] == 'EVAL_pairs' and received_selectors == selectors
        assert eval_pairs == [{'split': 'EVAL', 'rows': 8}]
        assert (output / 'frozen_selectors.json').read_bytes() == saved['selectors']
        events.append('evaluated')
        return [{'evaluation': True}], [{'summary': True}], [{'comparison': True}]

    monkeypatch.setattr(runner, 'extract_source', source)
    monkeypatch.setattr(runner, 'snapshot_code', snapshot)
    monkeypatch.setattr(runner, 'sample_phase', sample)
    monkeypatch.setattr(runner, 'build_pairs', pairs)
    monkeypatch.setattr(runner, 'freeze_selectors', freeze)
    monkeypatch.setattr(runner, 'evaluate', evaluate)
    runner.run(output)
    result = runner.read(output / 'run.json')
    assert events == ['source', 'snapshot', 'TRAIN_complete', 'TRAIN_pairs', 'selectors',
                      'EVAL_complete', 'EVAL_pairs', 'evaluated']
    assert result['status'] == 'complete' and result['phases'] == phase_results
    assert result['phases']['EVAL']['lifecycles'][0]['statuses'] == {'loss': 1, 'cutoff': 1}
    assert (output / 'frozen_inputs.json').read_bytes() == saved['inputs']
    assert (output / 'frozen_selectors.json').read_bytes() == saved['selectors']
    assert runner.read(output / 'evaluation_rows.json') == [{'evaluation': True}]
    assert runner.read(output / 'summary.json') == [{'summary': True}]
    assert runner.read(output / 'comparisons.json') == [{'comparison': True}]


def test_existing_output_is_refused_before_source_reads(local_tmp, monkeypatch):
    output = local_tmp / 'existing'
    output.mkdir()
    original = b'{"status":"retained_result"}\n'
    (output / 'run.json').write_bytes(original)
    monkeypatch.setattr(runner, 'extract_source', lambda *_: pytest.fail('existing output must fail before source reads'))
    with pytest.raises(FileExistsError):
        runner.run(output)
    assert (output / 'run.json').read_bytes() == original
    assert list(output.iterdir()) == [output / 'run.json']

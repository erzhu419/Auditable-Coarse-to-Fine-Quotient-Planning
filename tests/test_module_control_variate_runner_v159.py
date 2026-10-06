"""Synthetic critic loading and frozen-stage wiring, without native execution."""
from collections import Counter
from fractions import Fraction
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_module_control_variate_v159 as runner

TEMP = Path(__file__).resolve().parents[1] / 'reports/v159_runtime_tmp'
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
        failures=request.session.testsfailed - before, environment_samples=0,
        native_calls=0, production_source_reads=0, synthetic_work=dict(WORK),
        scope='Critic loader stubs, frozen stage order and existing output refusal.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_', dir=TEMP) as folder:
        yield Path(folder)


def test_direct_single_critic_is_frozen_and_keeps_target_query_during_other_policy_prefix(local_tmp, monkeypatch):
    source = dict(life=0, leaves={query: {'SINGLE': dict(model_ref=f'{query}.npz')}
                                 for query in ('risk1', 'risk8')})
    loaded = []
    parents = {}

    def parent_loader(received, query, folder):
        assert received == source and folder.name == query
        parent = SimpleNamespace(query=query, updates=9,
            source=SimpleNamespace(weights=SimpleNamespace(flags=SimpleNamespace(writeable=False))))
        parents[query] = parent
        return parent, dict(source_policy=query, load_counts={'checkpoint_loads': 1})

    class Leaf:
        def __init__(self, parent):
            self.parent = parent
            self.rule = SimpleNamespace(spawn_distribution=((1, Fraction(5, 8)), (2, Fraction(3, 8))), spawn_location='uniform')
            self.weights = SimpleNamespace(flags=SimpleNamespace(writeable=True))
            self.updates, self.kind, self.offset = 12, 'PRIOR', .5
            self.setup_counts, self.setup_seconds = {'checkpoint_loaded_parameters': 8}, 0.
            self.load_counts = {'checkpoint_loads': 1, 'inner_checkpoint_loads': 1, 'inner_checkpoint_loaded_parameters': 8}
            self.last_load_seconds = 0.
            self.counts = Counter(self.load_counts)

        @classmethod
        def load(cls, path, parent, build):
            assert path == f'{parent.query}.npz' and build.name == 'build'
            leaf = cls(parent)
            loaded.append(leaf)
            return leaf

        def freeze(self):
            self.weights.flags.writeable = False

        def choose(self, board, query):
            assert not self.weights.flags.writeable
            assert query == runner.QUERIES[self.parent.query]
            self.counts.update(choose_calls=1, inner_learned_swipe_calls=4)
            WORK['critic_choose_stubs'] += 1
            return {'value': query['failure_penalty'] + board[0]}

    monkeypatch.setattr(runner, 'load_parent', parent_loader)
    monkeypatch.setattr(runner, 'QueryTD', Leaf)
    trace = local_tmp / 'synthetic.jsonl.gz'
    with gzip.open(trace, 'wt') as stream:
        for query in ('risk1', 'risk8'):
            row = dict(branch_id=f'0:{query}:LEARN8:0:TRAIN:0:M_GATE', root_id=f'0:{query}:LEARN8:0',
                life=0, query=query, source_method='LEARN8', slot=0, split='TRAIN', suffix=0, mode='M_GATE',
                choices=[{'policy_key': 'risk8' if query == 'risk1' else 'risk1'}])
            stream.write(json.dumps(row) + '\n')

    def correction(row, value):
        first, second = value([1] + [0] * 15), value([2] + [0] * 15)
        assert first == runner.QUERIES[row['query']]['failure_penalty'] + 1
        assert second == first + 1
        WORK['synthetic_trace_rows_read'] += 1
        return dict(**{k: row[k] for k in ('branch_id', 'root_id', 'life', 'query', 'source_method',
                                          'slot', 'split', 'suffix', 'mode')},
                    correction=second - first, counts={'critic_calls': 2})

    monkeypatch.setattr(runner, 'branch_correction', correction)
    result = runner.lifecycle(source, {'path': str(trace)}, 'TRAIN', local_tmp)
    assert len(loaded) == 2 and result['source_rows_read'] == 2
    assert result['counts'] == {'critic_calls': 4}
    assert result['new_environment_samples'] == result['new_training_updates'] == 0
    for query, metadata in result['critics'].items():
        assert metadata['reference'] == source['leaves'][query]['SINGLE']
        assert metadata['leaf_before'] == metadata['leaf_after']
        assert metadata['parent_before'] == metadata['parent_after']
        assert metadata['leaf_before']['readonly']
        assert metadata['counts'] == {'choose_calls': 2, 'inner_learned_swipe_calls': 8}
        assert metadata['leaf_load']['load_counts'] == loaded[0].load_counts
    assert all(leaf.counts['checkpoint_loads'] == 1 for leaf in loaded)
    assert [row['correction'] for row in runner.read(local_tmp / result['corrections_ref'])] == [1, 1]


def test_inputs_freeze_before_corrections_and_train_only_selectors_freeze_before_eval(local_tmp, monkeypatch):
    output = local_tmp / 'experiment'
    raw_train, raw_eval, raw_selected = [{'raw': 'TRAIN'}], [{'raw': 'EVAL'}], [{'raw_selector': True}]
    refs = {}
    for name, value in (('raw_train_pairs_ref', raw_train), ('raw_eval_pairs_ref', raw_eval), ('raw_selectors_ref', raw_selected)):
        path = local_tmp / f'{name}.json'
        runner.save(path, value)
        refs[name] = str(path)
    capsule = dict(roots=[{'root_id': 'synthetic'}], cost_refs=[], **refs)
    events, frozen, phases = [], {}, {}
    selected = [{'cv_selector': 'TRAIN_only'}]

    def snapshot(directory):
        assert runner.read(directory / 'source_capsule.json') == capsule
        (directory / 'source').mkdir()
        (directory / 'source/synthetic.py').write_text('# synthetic snapshot\n')
        events.append('snapshot')

    def correct(split, received, directory):
        assert received == capsule and directory == output
        state = runner.read(directory / 'run.json')
        if split == 'TRAIN':
            assert events == ['snapshot'] and state['status'] == 'frozen'
            assert (directory / 'source/synthetic.py').exists()
            frozen['inputs'] = (directory / 'frozen_inputs.json').read_bytes()
            assert runner.read(directory / 'frozen_inputs.json') == state
            assert not (directory / 'frozen_cv_selectors.json').exists()
        else:
            assert events == ['snapshot', 'TRAIN_complete', 'TRAIN_pairs', 'selected']
            assert state['status'] == 'selectors_frozen' and state['phases'] == {'TRAIN': phases['TRAIN']}
            assert runner.read(directory / 'frozen_cv_selectors.json') == selected
            frozen['selectors'] = (directory / 'frozen_cv_selectors.json').read_bytes()
        ref = f'{split.lower()}_corrections.json'
        runner.save(directory / ref, [{'correction_split': split}])
        phase = dict(split=split, lifecycles=[dict(life=0, corrections_ref=ref)], seconds=0.)
        phases[split] = phase
        events.append(f'{split}_complete')
        WORK['phase_correction_stubs'] += 1
        return phase

    def adjusted(raw, corrections):
        split = raw[0]['raw']
        assert events[-1] == f'{split}_complete' and corrections == [{'correction_split': split}]
        events.append(f'{split}_pairs')
        return [{'adjusted': split}]

    def select(roots, pairs):
        assert roots == capsule['roots'] and pairs == [{'adjusted': 'TRAIN'}]
        assert events[-1] == 'TRAIN_pairs' and 'EVAL' not in phases
        events.append('selected')
        return selected

    def evaluate(raw_selectors, cv_selectors, evaluation):
        assert raw_selectors == raw_selected and cv_selectors == selected
        assert evaluation == raw_eval and evaluation != [{'adjusted': 'EVAL'}]
        assert events[-1] == 'EVAL_pairs'
        events.append('evaluated_raw')
        return {'only_raw_evaluation': True}

    monkeypatch.setattr(runner, 'extract_source', lambda: capsule)
    monkeypatch.setattr(runner, 'snapshot_code', snapshot)
    monkeypatch.setattr(runner, 'correct_phase', correct)
    monkeypatch.setattr(runner, 'build_adjusted_pairs', adjusted)
    monkeypatch.setattr(runner, 'freeze_cv_selectors', select)
    monkeypatch.setattr(runner, 'evaluate_control', evaluate)
    monkeypatch.setattr(runner, 'variance_report', lambda pairs: {'both_adjusted': pairs == [{'adjusted': 'TRAIN'}, {'adjusted': 'EVAL'}]})
    runner.run(output)
    result = runner.read(output / 'run.json')
    assert events == ['snapshot', 'TRAIN_complete', 'TRAIN_pairs', 'selected', 'EVAL_complete', 'EVAL_pairs', 'evaluated_raw']
    assert result['status'] == 'complete' and result['phases'] == phases
    assert result['new_environment_samples'] == result['new_training_updates'] == 0
    assert (output / 'frozen_inputs.json').read_bytes() == frozen['inputs']
    assert (output / 'frozen_cv_selectors.json').read_bytes() == frozen['selectors']
    assert runner.read(output / 'evaluation.json') == {'only_raw_evaluation': True}
    assert runner.read(output / 'variance.json') == {'both_adjusted': True}


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

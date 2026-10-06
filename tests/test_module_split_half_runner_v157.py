"""Synthetic trace extraction and freeze-order wiring; no production outcomes."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts import run_controlled_predictive_module_split_half_v157 as runner

TEMP = Path(__file__).resolve().parents[1] / 'reports/v157_runtime_tmp'
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
        scope='Synthetic gzip extraction; frozen input order; existing output refusal.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_', dir=TEMP) as folder:
        yield Path(folder)


def synthetic_capsule(folder):
    roots, traces, expected = [], [], []
    for life in range(4):
        root_id = f'{life}:risk1:H2:0'
        board = [life + 1] + [0] * 15
        roots.append(dict(root_id=root_id, life=life, query='risk1',
                          source_method='H2', slot=0, board=board))
        path = folder / f'life_{life}.jsonl.gz'
        traces.append(dict(life=life, path=str(path)))
        with gzip.open(path, 'wt') as stream:
            for index, mode in enumerate(('H_H2', 'M_H2')):
                fields = dict(branch_id=f'{root_id}:0:{mode}', root_id=root_id,
                    life=life, query='risk1', source_method='H2', slot=0,
                    suffix=0, mode=mode, seed=100 + life, root_board=board)
                result = dict(score=4 * (life + index), steps=life + index + 1,
                    status='win' if index else 'loss',
                    components=[life + index, 0 if index else 1, index])
                raw = dict(fields, result=dict(result, policy_counts={'calls': 7}),
                    choices=[{'unused_trace': list(range(40))}],
                    spawned_cells=[3, 4], spawned_ranks=[1, 2], tapes=['discard'])
                stream.write(json.dumps(raw) + '\n')
                expected.append(dict(fields, **result))
    return dict(roots=roots, source_traces=traces, cost_refs=[{'path': 'synthetic'}]), expected


def test_extract_keeps_only_compact_outcomes_and_counts_retained_work(local_tmp):
    capsule, expected = synthetic_capsule(local_tmp)
    outcomes, work = runner.extract_outcomes(capsule)
    WORK['synthetic_trace_rows_read'] += work['rows']
    WORK['synthetic_retained_transitions'] += work['retained_environment_transitions']
    assert outcomes == expected
    assert work['rows'] == 8 and work['raw_trace_files_read'] == 4
    assert work['retained_environment_transitions'] == 24
    assert work['new_environment_samples'] == work['native_planner_calls'] == work['model_fits'] == 0
    assert work['seconds'] >= 0
    assert set(outcomes[0]) == {
        'branch_id', 'root_id', 'life', 'query', 'source_method', 'slot',
        'suffix', 'mode', 'seed', 'root_board', 'score', 'steps', 'status', 'components'}


def test_run_freezes_capsule_code_and_inputs_before_reading_outcomes(local_tmp, monkeypatch):
    capsule, expected = synthetic_capsule(local_tmp)
    output = local_tmp / 'experiment'
    events, frozen = [], {}
    pairs = [{'root_id': 'synthetic_pair'}]
    selections = [{'direction': 'A_to_B'}, {'direction': 'B_to_A'}]
    summary = [{'descriptive': True}]
    actual_extract = runner.extract_outcomes

    def source():
        events.append('source')
        return deepcopy(capsule)

    def snapshot(directory):
        assert runner.read(directory / 'source_capsule.json') == capsule
        path = directory / 'source/synthetic.py'
        path.parent.mkdir()
        path.write_text('# synthetic code snapshot\n')
        events.append('snapshot')

    def extract(received):
        assert events == ['source', 'snapshot'] and received == capsule
        assert (output / 'source/synthetic.py').exists()
        frozen['bytes'] = (output / 'frozen_inputs.json').read_bytes()
        frozen_data = runner.read(output / 'frozen_inputs.json')
        assert frozen_data['status'] == 'frozen'
        assert frozen_data['root_ids'] == [r['root_id'] for r in capsule['roots']]
        assert frozen_data['halves'] == {'A': list(range(8)), 'B': list(range(8, 16))}
        assert runner.read(output / 'run.json') == frozen_data
        assert not (output / runner.OUTPUT_REFS['outcomes']).exists()
        events.append('extract')
        outcomes, work = actual_extract(received)
        WORK['synthetic_trace_rows_read'] += work['rows']
        WORK['synthetic_retained_transitions'] += work['retained_environment_transitions']
        return outcomes, work

    def pair_builder(roots, outcomes):
        assert events[-1] == 'extract' and roots == capsule['roots'] and outcomes == expected
        assert runner.read(output / runner.OUTPUT_REFS['outcomes']) == expected
        events.append('pairs')
        return pairs

    def selector(roots, received):
        assert events[-1] == 'pairs' and roots == capsule['roots'] and received == pairs
        events.append('selections')
        return selections

    def summarize(received):
        assert events[-1] == 'selections' and received == selections
        events.append('summary')
        return summary

    monkeypatch.setattr(runner, 'extract_source', source)
    monkeypatch.setattr(runner, 'snapshot_code', snapshot)
    monkeypatch.setattr(runner, 'extract_outcomes', extract)
    monkeypatch.setattr(runner, 'build_pairs', pair_builder)
    monkeypatch.setattr(runner, 'build_selection_rows', selector)
    monkeypatch.setattr(runner, 'summarize', summarize)
    runner.run(output)
    result = runner.read(output / 'run.json')
    assert events == ['source', 'snapshot', 'extract', 'pairs', 'selections', 'summary']
    assert result['status'] == 'complete'
    assert (result['pairs'], result['selection_rows'], result['summary_groups']) == (1, 2, 1)
    assert result['extraction']['rows'] == 8
    assert result['extraction']['retained_environment_transitions'] == 24
    assert (output / 'frozen_inputs.json').read_bytes() == frozen['bytes']
    for key, value in [('outcomes', expected), ('pairs', pairs), ('selections', selections), ('summary', summary)]:
        assert runner.read(output / result['output_refs'][key]) == value


def test_existing_output_is_untouched_without_reading_source(local_tmp, monkeypatch):
    output = local_tmp / 'existing'
    output.mkdir()
    original = b'{"status":"retained_result"}\n'
    (output / 'run.json').write_bytes(original)
    monkeypatch.setattr(runner, 'extract_source', lambda: pytest.fail('existing output must fail before source reads'))
    with pytest.raises(FileExistsError):
        runner.run(output)
    assert (output / 'run.json').read_bytes() == original
    assert list(output.iterdir()) == [output / 'run.json']

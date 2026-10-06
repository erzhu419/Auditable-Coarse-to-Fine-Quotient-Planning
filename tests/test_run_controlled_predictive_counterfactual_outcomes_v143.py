"""Finite roster, stream-sharing and accounting checks; no environment rollouts."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_counterfactual_outcomes_v143 as runner


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_counterfactual_outcomes_v143.runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0,
        model_updates=0, source_refits=0,
        scope='Mocked complete retained cohort, quantile roots, shared suffix streams, action deduplication, cost separation and freeze before workers.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


@pytest.fixture
def local_tmp():
    root = ROOT/'reports/v143_runtime_tmp'; root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='runner_test_', dir=root) as path:
        yield Path(path)


def source_fixture():
    capsule = dict(snapshots=[dict(life=life, rule={}, models={}, leaves={},
        factored_ref=f'/retained/factors_{life}.json', program_ref=f'/retained/program_{life}.json',
        baseline_control_trace=f'/retained/v140_{life}.jsonl.gz',
        shallow_control_trace=f'/retained/v141_control_{life}.jsonl.gz',
        diagnostic_source_trace=f'/retained/v141_diagnostics_{life}.jsonl.gz')
        for life in runner.LIVES], inherited_costs={'prior': 1})
    run = dict(status='complete', eval_lifecycles=[dict(life=life,
        diagnostics_trace=f'eval_{life}/diagnostics.jsonl.gz') for life in runner.LIVES])
    analysis = dict(complete=True, primary_complete=True, costs={'v142': 2})
    return capsule, run, analysis


def retained_fixture():
    sources = runner.extract_source(*source_fixture())['snapshots']
    # All 64 old games, including short and odd-sized cohorts, total exactly 1,973.
    sizes = [4, 5, 8, 13]+[32]*59+[55]
    files, games = {}, {}
    for snapshot in sources:
        life = snapshot['life']; old, new = [], []
        for query in runner.QUERIES:
            for replica in range(runner.REPLICAS):
                game_index = len(games); records = []
                for ordinal in range(sizes[game_index]):
                    step = ordinal*32
                    row = dict(life=life, query=query, replica=replica,
                        seed=14090000000+life*100000+replica, step=step,
                        board=[1+(ordinal%8), 1+(game_index%8)]+[0]*14,
                        previous_action='RIGHT', simulation_seed=14080000000+life*1000000+replica*10000+step,
                        reference={'action': 'LEFT'}, probes={
                            'SHALLOW': {'action': 'UP' if ordinal%2 else 'LEFT'},
                            'LEARNED64': {'action': 'DOWN' if ordinal%3 else 'LEFT'}})
                    records.append(row)
                    h1 = {key:deepcopy(value) for key,value in row.items() if key not in ('reference','probes')}
                    h1['probes'] = {'H1_CONT': {'action': 'UP'}}; new.append(h1)
                games[(life,query,replica)] = records
                old.extend(reversed(records))
        files[snapshot['diagnostic_source_trace']] = old
        files[snapshot['h1_diagnostic_trace']] = list(reversed(new))
    return sources, files, games


def read(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def test_source_retains_all_old_absolute_references_without_copying_games():
    capsule, run, analysis = source_fixture(); original = deepcopy(capsule)
    result = runner.extract_source(capsule, run, analysis)
    assert result['inherited_costs'] == dict(prior=1, v142_experiment={'v142':2})
    for source, old in zip(result['snapshots'], capsule['snapshots']):
        assert source['h1_diagnostic_trace'] == str((runner.SOURCE/f"eval_{source['life']}/diagnostics.jsonl.gz").resolve())
        assert {key:source[key] for key in old} == old
        assert 'games' not in source and 'diagnostics' not in source
    result['snapshots'][0]['leaves']['changed'] = 1
    assert capsule == original


@pytest.mark.parametrize('failed', ['status','complete','primary_complete'])
def test_incomplete_source_prevents_collection(failed):
    capsule, run, analysis = source_fixture()
    if failed == 'status': run[failed] = 'evaluation'
    else: analysis[failed] = False
    with pytest.raises(ValueError, match='V142 must be complete'):
        runner.extract_source(capsule, run, analysis)


def test_cohort_covers_every_game_quantile_and_freezes_distinct_action_streams(monkeypatch):
    sources, files, games = retained_fixture(); original = deepcopy(files); reads = []
    def retained(path):
        reads.append(path); return iter(files[path])
    monkeypatch.setattr(runner, 'read_rows', retained)
    cohort = runner.build_cohort(sources)
    assert reads == [s[key] for s in sources for key in ('diagnostic_source_trace','h1_diagnostic_trace')]
    assert cohort['source_rows_read'] == dict(v141=1973, v142=1973)
    assert len(cohort['roots']) == 256 and cohort['paired_records'] == 2048
    assert cohort['logical_method_suffixes'] == 8192
    assert Counter((r['life'],r['query'],r['replica']) for r in cohort['roots']) == {game:4 for game in games}
    streams = []
    fields = ('life','query','replica','seed','step','board','previous_action','simulation_seed')
    for root in cohort['roots']:
        records = games[(root['life'],root['query'],root['replica'])]
        ordinal = ((2*root['slot']+1)*len(records))//8; old = records[ordinal]
        assert root['source_ordinal'] == ordinal and root['source_game_roots'] == len(records)
        assert {key:root[key] for key in fields} == {key:old[key] for key in fields}
        assert root['root_id'] == f"{old['life']}:{old['query']}:{old['replica']}:{old['step']}"
        assert root['choices'] == dict(H2='LEFT', SHALLOW=old['probes']['SHALLOW']['action'],
            LEARNED64=old['probes']['LEARNED64']['action'], H1_CONT='UP')
        assert root['actions'] == sorted(set(root['choices'].values()))
        base = (14300000000+root['life']*1000000+list(runner.QUERIES).index(root['query'])*100000
            +root['replica']*10000+root['slot']*100)
        assert root['suffix_seeds'] == list(range(base,base+8))
        streams.extend(root['suffix_seeds'])
    assert len(set(streams)) == 2048
    assert cohort['physical_branches'] == sum(8*len(r['actions']) for r in cohort['roots'])
    assert files == original
    cohort['roots'][0]['board'][0] = 99
    assert files == original


@pytest.mark.parametrize('mismatch', ['missing_identity','selected_board','total_roots'])
def test_retained_mismatches_prevent_freezing_an_incorrect_cohort(monkeypatch, mismatch):
    sources, files, _ = retained_fixture(); source = sources[-1]
    old = files[source['diagnostic_source_trace']]; new = files[source['h1_diagnostic_trace']]
    if mismatch == 'missing_identity': new.pop()
    elif mismatch == 'selected_board':
        first = files[sources[0]['h1_diagnostic_trace']]
        next(r for r in first if r['query'] == next(iter(runner.QUERIES)) and r['replica'] == 0 and r['step'] == 0)['board'][0] = 99
    else:
        removed = old.pop(); new[:] = [r for r in new if runner.root_key(r) != runner.root_key(removed)]
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter(files[path]))
    with pytest.raises(ValueError, match='retained'):
        runner.build_cohort(sources)


def test_evaluation_runs_each_distinct_action_once_per_shared_suffix_and_separates_work(local_tmp, monkeypatch):
    roots = [dict(life=0,query=query,root_id=f'0:{query}:0:32',board=[1,1]+[0]*14,
        choices=dict(H2='LEFT',SHALLOW='LEFT',LEARNED64='UP',H1_CONT='UP'),
        actions=['LEFT','UP'],suffix_seeds=[runner.suffix_seed(0,query,0,0,s) for s in range(8)])
        for query in runner.QUERIES]
    frozen = deepcopy(roots); calls, loads = [], []
    class Teacher:
        def __init__(self, query):
            self.query, self.counts, self.spawn_probabilities = query, Counter(), (.9,.1)
        def choose(self, *args, **kwargs): pytest.fail('mock runner called real continuation')
    def load(source, representation, query, folder):
        assert representation == 'SINGLE' and folder.is_dir()
        loads.append((source,query)); model = SimpleNamespace(query=query)
        return model, model, Teacher(query), dict(copied_leaf=1)
    def branch(board, action, teacher, query, seed, max_steps, p_four):
        assert query == runner.QUERIES[teacher.query] and (max_steps,p_four) == (2000,.1)
        calls.append((teacher.query,list(board),action,seed))
        teacher.counts['native_h2_decisions'] += 2
        return dict(seed=seed,first_action=action,result=dict(status='LOST' if action == 'LEFT' else 'WON',
            environment_counts=dict(sampled_transitions=3,random_draws=6),
            policy_counts=dict(native_h2_decisions=2),learning_counts={}))
    monkeypatch.setattr(runner,'load_teacher',load)
    monkeypatch.setattr(runner,'run_branch',branch)
    monkeypatch.setattr(runner,'leaf_state',lambda model,parent=False:dict(query=model.query,frozen=True))
    monkeypatch.setattr(runner,'read_rows',lambda *args:pytest.fail('re-read old decision traces during evaluation'))
    monkeypatch.setattr(runner.previous.previous.previous,'fit_programs',lambda *args:pytest.fail('refitted old programs'))
    result = runner.evaluate_lifecycle(dict(life=0),roots,local_tmp)
    assert [q for _,q in loads] == list(runner.QUERIES)
    expected = [(r['query'],r['board'],a,s) for r in roots for s in r['suffix_seeds'] for a in r['actions']]
    assert calls == expected and len(calls) == 32
    rows = read(local_tmp/result['consequences_trace']); assert len(rows) == 16
    for root in roots:
        selected = [r for r in rows if r['root_id'] == root['root_id']]
        assert [(r['suffix'],r['seed']) for r in selected] == list(enumerate(root['suffix_seeds']))
        assert all(r['continuation'] == 'H2' and set(r['branches']) == {'LEFT','UP'} for r in selected)
        assert all(branch['seed'] == row['seed'] for row in selected for branch in row['branches'].values())
        data = result['queries'][root['query']]
        assert data['roots'] == 1 and data['physical_branches'] == 16 and data['paired_records'] == 8
        assert data['statuses'] == dict(LOST=8,WON=8)
        assert data['loads'] == dict(copied_leaf=1)
        assert data['environment_counts'] == dict(sampled_transitions=48,random_draws=96)
        assert data['policy_counts'] == dict(native_h2_decisions=32)
        assert data['parent_before'] == data['parent_after'] and data['leaf_before'] == data['leaf_after']
    assert roots == frozen


def test_full_roster_code_and_seed_allocation_are_frozen_before_workers(local_tmp, monkeypatch):
    sources, files, _ = retained_fixture(); capsule, source_run, analysis = source_fixture()
    source_dir = local_tmp/'source'; source_dir.mkdir()
    for name,payload in zip(('source_capsule.json','run.json','analysis.json'),(capsule,source_run,analysis)):
        (source_dir/name).write_text(json.dumps(payload))
    for source in sources:
        life = source['life']
        files[str((source_dir/f'eval_{life}/diagnostics.jsonl.gz').resolve())] = files[source['h1_diagnostic_trace']]
    events = []
    class Pool:
        def __init__(self, **kwargs): assert kwargs == dict(max_workers=4)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args):value)
    def snapshot(directory):
        assert len(json.loads((directory/'cohort.json').read_text())['roots']) == 256
        assert len(json.loads((directory/'source_capsule.json').read_text())['snapshots']) == 4
        events.append('code_snapshot')
    def evaluate(source, roots, directory):
        frozen = json.loads((directory/'frozen_inputs.json').read_text())
        cohort = json.loads((directory/'cohort.json').read_text())
        assert frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
        assert events[0] == 'code_snapshot' and frozen['settings']['new_training_samples'] == 0
        assert roots == [r for r in cohort['roots'] if r['life'] == source['life']]
        assert len(roots) == 64 and all(len(r['suffix_seeds']) == 8 for r in roots)
        events.append(source['life']); return dict(life=source['life'])
    monkeypatch.setattr(runner,'SOURCE',source_dir)
    monkeypatch.setattr(runner,'read_rows',lambda path:iter(files[path]))
    monkeypatch.setattr(runner,'snapshot_code',snapshot)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Pool)
    monkeypatch.setattr(runner,'as_completed',lambda futures:reversed(futures))
    monkeypatch.setattr(runner,'evaluate_lifecycle',evaluate)
    monkeypatch.setattr(runner,'load_teacher',lambda *args:pytest.fail('loaded planner before evaluation'))
    monkeypatch.setattr(runner,'run_branch',lambda *args:pytest.fail('ran branch before frozen workers'))
    directory = local_tmp/'run'; runner.run(directory)
    data = json.loads((directory/'run.json').read_text())
    assert events == ['code_snapshot',*runner.LIVES]
    assert data['status'] == 'complete' and [r['life'] for r in data['eval_lifecycles']] == list(runner.LIVES)
    assert data['settings']['continuation'] == 'H2' and data['settings']['expected_roots'] == 256
    assert data['inherited_costs'] == dict(prior=1,v142_experiment={'v142':2})


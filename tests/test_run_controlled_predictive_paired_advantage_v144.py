"""Finite paired-data and phase-order checks; no real games or native calls."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_paired_advantage_v144 as runner


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_paired_advantage_v144.runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0,
        model_updates=0, source_refits=0,
        scope='Mocked retained paired targets, original-game split, ordered training, model freeze, new-game streams and separate phase costs.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


@pytest.fixture
def local_tmp():
    root = ROOT/'reports/v144_runtime_tmp'; root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='runner_test_', dir=root) as path:
        yield Path(path)


def read(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def source_fixture():
    capsule = dict(snapshots=[dict(life=life, rule={}, models={},
        leaves={q: {'SINGLE': {'model_ref': f'/retained/leaf_{life}_{q}.npz'}} for q in runner.QUERIES},
        factored_ref=f'/retained/factors_{life}.json', program_ref=f'/retained/program_{life}.json',
        baseline_control_trace=f'/retained/v140_{life}.jsonl.gz',
        shallow_control_trace=f'/retained/v141_control_{life}.jsonl.gz',
        diagnostic_source_trace=f'/retained/v141_diagnostics_{life}.jsonl.gz',
        h1_diagnostic_trace=f'/retained/v142_diagnostics_{life}.jsonl.gz')
        for life in runner.LIVES], inherited_costs={'prior': 1})
    run = dict(status='complete', eval_lifecycles=[dict(life=life,
        consequences_trace=f'eval_{life}/paired_consequences.jsonl.gz') for life in runner.LIVES])
    analysis = dict(complete=True, primary_complete=True, costs={'v143': 2})
    return capsule, run, analysis


def retained_fixture(sources):
    """The full fixed roster, with same-action rows and nonzero immediate reward."""
    roots, files = [], {}
    for source in sources:
        life = source['life']; records = []
        for query in runner.QUERIES:
            for replica in range(8):
                for slot in range(4):
                    step = 32*(slot+1)
                    same = slot == 0
                    choices = dict(H2='LEFT', H1_CONT='LEFT' if same else 'RIGHT',
                                   SHALLOW='LEFT', LEARNED64='RIGHT')
                    root = dict(life=life, query=query, replica=replica, step=step,
                        root_id=f'{life}:{query}:{replica}:{step}', slot=slot,
                        board=[1, 1, 2, 3]+[0]*12, previous_action='DOWN',
                        seed=14090000000+life*100000+replica,
                        simulation_seed=14080000000+life*1000000+replica*10000+step,
                        choices=choices, actions=['LEFT', 'RIGHT'],
                        suffix_seeds=[14300000000+life*1000000+list(runner.QUERIES).index(query)*100000
                            +replica*10000+slot*100+s for s in range(8)])
                    roots.append(root)
                    for suffix, seed in enumerate(root['suffix_seeds']):
                        branches = {}
                        for action in ('LEFT', 'RIGHT'):
                            candidate = action == 'RIGHT'
                            first = 12 if candidate else 4
                            total = (22528+4096*suffix) if candidate else (20480+2048*suffix)
                            lost = candidate and suffix < 2
                            branches[action] = dict(seed=seed, first_action=action,
                                first_afterstate=([2, 1, 2, 3] if candidate else [1, 2, 2, 3])+[0]*12,
                                scores=[first, total-first], result=dict(status='LOST' if lost else 'WON',
                                    score=total, components=[total/2048., float(lost), float(not lost)],
                                    environment_counts=dict(sampled_transitions=2), policy_counts={}))
                        records.append(dict(root_id=root['root_id'], suffix=suffix, seed=seed,
                            continuation='H2', branches=branches))
        files[life] = list(reversed(records))
    return dict(roots=roots, paired_records=2048), files


def example_fixture(local_tmp, monkeypatch):
    source = runner.extract_source(*source_fixture())
    cohort, files = retained_fixture(source['snapshots'])
    path = local_tmp/'cohort.json'; path.write_text(json.dumps(cohort))
    source['cohort_ref'] = str(path)
    traces = {s['paired_consequences_trace']:files[s['life']] for s in source['snapshots']}
    monkeypatch.setattr(runner, 'read_rows', lambda path: iter(traces[path]))
    return source, cohort, traces


def test_source_retains_absolute_references_without_copying_or_mutating_prior_data():
    capsule, run, analysis = source_fixture(); original = deepcopy(capsule)
    source = runner.extract_source(capsule, run, analysis)
    assert source['inherited_costs'] == dict(prior=1, v143_experiment={'v143':2})
    assert source['cohort_ref'] == str((runner.SOURCE/'cohort.json').resolve())
    for row, prior in zip(source['snapshots'], capsule['snapshots']):
        assert {key:row[key] for key in prior} == prior
        assert row['paired_consequences_trace'] == str((runner.SOURCE/f"eval_{row['life']}/paired_consequences.jsonl.gz").resolve())
        assert 'branches' not in row and 'games' not in row
    source['snapshots'][0]['leaves']['changed'] = 1
    assert capsule == original


@pytest.mark.parametrize('failed', ['status', 'complete', 'primary_complete'])
def test_incomplete_source_prevents_supervision(failed):
    capsule, run, analysis = source_fixture()
    if failed == 'status': run[failed] = 'evaluation'
    else: analysis[failed] = False
    with pytest.raises(ValueError, match='V143 paired outcomes must be complete'):
        runner.extract_source(capsule, run, analysis)


def test_paired_suffix_means_subtract_first_reward_once_and_keep_whole_games_together(local_tmp, monkeypatch):
    source, cohort, traces = example_fixture(local_tmp, monkeypatch); original = deepcopy(traces)
    result = runner.build_examples(source); examples = result['examples']
    assert len(examples) == 256
    assert result['source_rows_read'] == dict(paired_records=2048, physical_branches=4096)
    assert [e['root_id'] for e in examples] == [r['root_id'] for r in cohort['roots']]
    assert Counter(e['split'] for e in examples) == dict(TRAIN=128, VALIDATION=128)
    for e in examples:
        assert e['split'] == ('TRAIN' if e['replica'] < 4 else 'VALIDATION') and e['suffixes'] == 8
        same = e['slot'] == 0
        assert (e['candidate_action'] == e['baseline_action']) == same
        assert e['immediate_difference'] == (0. if same else 8/2048.)
        assert e['target_total'] == ([0.,0.,0.] if same else [4.5,.25,-.25])
        assert e['target_tail'] == ([0.,0.,0.] if same else [4.5-8/2048.,.25,-.25])
    assert traces == original
    examples[0]['candidate_after'][0] = 9
    assert traces == original


@pytest.mark.parametrize('mismatch', ['duplicate_suffix', 'seed', 'cutoff', 'first_afterstate'])
def test_reachable_incomplete_or_unpaired_supervision_is_rejected(local_tmp, monkeypatch, mismatch):
    source, _, traces = example_fixture(local_tmp, monkeypatch)
    rows = next(iter(traces.values())); row = rows[0]
    if mismatch == 'duplicate_suffix': rows[1] = deepcopy(row)
    elif mismatch == 'seed': row['seed'] += 1
    elif mismatch == 'cutoff': row['branches']['LEFT']['result']['status'] = 'CUTOFF'
    else: row['branches']['LEFT']['first_afterstate'][0] += 1
    with pytest.raises(ValueError, match='paired'):
        runner.build_examples(source)


class MockModel:
    instances = []
    def __init__(self):
        self.frozen = False; self.updates = 0; self.counts = Counter(); self.setup_counts = Counter(mock_allocations=1)
        self.calls = []; self.radix = 11; self.instances.append(self)
    def state(self):
        return dict(frozen=self.frozen, updates=self.updates, weights=[] if not self.updates else [[1,1.,0.,0.]])
    def update(self, candidate, baseline, target, alpha):
        assert not self.frozen
        self.calls.append((deepcopy(candidate),deepcopy(baseline),deepcopy(target),alpha))
        self.counts['update_calls'] += 1
        if candidate != baseline:
            self.updates += 1; self.counts['pair_updates'] += 1
    def freeze(self): self.frozen = True
    def predict(self, candidate, baseline):
        assert self.frozen
        self.counts['pair_predictions'] += 1
        return [1. if self.updates else 0.,0.,0.]
    def to_payload(self):
        self.counts['checkpoint_saves'] += 1
        return dict(schema='mock', **self.state())
    @classmethod
    def from_payload(cls, payload):
        model = cls(); model.frozen = payload['frozen']; model.updates = payload['updates']
        model.setup_counts['mock_loads'] += 1
        return model


def test_training_uses_fixed_root_passes_then_frozen_validation_with_a_separate_zero_model(local_tmp, monkeypatch):
    source, _, _ = example_fixture(local_tmp, monkeypatch)
    examples = [e for e in runner.build_examples(source)['examples'] if e['life'] == 0]
    original = deepcopy(examples); MockModel.instances = []
    monkeypatch.setattr(runner, 'PairedAdvantage', MockModel)
    monkeypatch.setattr(runner, 'load_teacher', lambda *a, **k: pytest.fail('training loaded an environment planner'))
    data = runner.train_lifecycle(source['snapshots'][0], examples, local_tmp)
    assert len(MockModel.instances) == 4
    for index, query in enumerate(runner.QUERIES):
        learned, zero = MockModel.instances[2*index:2*index+2]
        train = [e for e in examples if e['query'] == query and e['replica'] < 4]
        validation = [e for e in examples if e['query'] == query and e['replica'] >= 4]
        expected = [(e['candidate_after'],e['baseline_after'],e['target_tail'],.1) for e in train]
        assert learned.calls == expected*32 and len(learned.calls) == 512
        assert not zero.calls and learned is not zero and learned.frozen and zero.frozen
        cell = data['queries'][query]
        assert cell['train_roots'] == [e['root_id'] for e in train]
        assert cell['validation_roots'] == [e['root_id'] for e in validation]
        assert cell['fit_counts'] == dict(update_calls=512,pair_updates=384)
        assert cell['validation_work'] == dict(ZERO=dict(pair_predictions=12),LEARNED=dict(pair_predictions=12))
        assert cell['frozen_state'] == cell['after_validation'] == learned.state()
        assert cell['before'] == dict(frozen=False,updates=0,weights=[])
        assert (local_tmp/cell['model_ref']).is_file()
        assert cell['binding']['life'] == 0 and cell['binding']['query'] == query
        for name in ('ZERO','LEARNED'):
            assert [row['root_id'] for row in cell['validation'][name]] == [e['root_id'] for e in validation]
    assert examples == original


def test_evaluation_runs_only_new_methods_and_keeps_gate_and_leaf_state_and_costs_separate(local_tmp, monkeypatch):
    source = runner.extract_source(*source_fixture())['snapshots'][0]
    factors = local_tmp/'factors.json'; factors.write_text(json.dumps({'rules':[]})); source['factored_ref'] = str(factors)
    trained = dict(queries={}); MockModel.instances = []; calls = []; teachers = []; candidates = []
    for query in runner.QUERIES:
        path = local_tmp/f'{query}.json'; path.write_text(json.dumps(dict(frozen=True,updates=384,weights=[[1,1.,0.,0.]])))
        trained['queries'][query] = dict(model_ref=path.name)
    def load(source, representation, query, folder):
        assert representation == 'SINGLE' and folder.is_dir()
        teacher = SimpleNamespace(counts=Counter(),query=query); teachers.append(teacher)
        leaf = SimpleNamespace(query=query)
        return leaf,leaf,teacher,dict(checkpoint_loads=1)
    def candidate(leaf, factors, build_dir):
        assert factors == {'rules':[]} and build_dir.parent.is_dir()
        value = SimpleNamespace(counts=Counter(),setup_counts=dict(cpp_library_cache_hits=1),setup_seconds=.2)
        candidates.append(value); return value
    def gate(teacher, candidate, model, query):
        assert model.frozen
        return SimpleNamespace(teacher=teacher,candidate=candidate,model=model,counts=Counter())
    def play(planner,life,query,method,replica):
        calls.append((life,query,method,replica,planner))
        if method == 'H2': planner.counts['native_h2'] += 2
        else:
            assert planner.model.frozen and (planner.model.updates == 0) == (method == 'ZERO')
            planner.counts.update(baseline_native_h2=2,candidate_model_swipes=3,learner_pair_predictions=1)
            planner.teacher.counts['native_h2'] += 2; planner.candidate.counts['model_swipes'] += 3
        return dict(life=life,query=query,method=method,replica=replica,result=dict(utility=1.))
    monkeypatch.setattr(runner,'PairedAdvantage',MockModel); monkeypatch.setattr(runner,'AdvantagePlanner',gate)
    monkeypatch.setattr(runner,'H1ContinuationPlanner',candidate); monkeypatch.setattr(runner,'load_teacher',load)
    monkeypatch.setattr(runner,'leaf_state',lambda leaf,parent=False:dict(query=leaf.query,readonly=True))
    monkeypatch.setattr(runner,'play',play)
    monkeypatch.setattr(runner,'read_rows',lambda *a:pytest.fail('evaluation reread old branch traces'))
    result = runner.evaluate_lifecycle(source,trained,local_tmp)
    assert [(l,q,m,r) for l,q,m,r,_ in calls] == [(0,q,m,r) for q in runner.QUERIES for m in ('H2','ZERO','LEARNED') for r in range(8)]
    assert len(read(local_tmp/result['control_trace'])) == 48
    for query, teacher, candidate in zip(runner.QUERIES,teachers,candidates):
        cell = result['queries'][query]
        assert cell['parent_before'] == cell['parent_after'] == cell['leaf_before'] == cell['leaf_after']
        assert cell['planners']['H2']['counts'] == dict(native_h2=16)
        assert cell['teacher_total_counts'] == dict(native_h2=48)
        assert cell['candidate_total_counts'] == dict(model_swipes=48)
        gates = []
        for method in ('ZERO','LEARNED'):
            selected = [p for _,q,m,_,p in calls if q == query and m == method]
            assert all(p is selected[0] for p in selected); gates.append(selected[0])
            assert cell['planners'][method]['counts'] == dict(baseline_native_h2=16,candidate_model_swipes=24,learner_pair_predictions=8)
            assert cell['planners'][method]['model_before'] == cell['planners'][method]['model_after']
        assert gates[0].model is not gates[1].model
    assert all(not model.calls for model in MockModel.instances)


def test_new_game_streams_match_across_methods_and_queries_and_retain_cutoffs(local_tmp, monkeypatch):
    calls = []; environment_seeds = []
    class Planner:
        def __init__(self,method): self.method=method; self.counts=Counter()
        def choose(self,board,query,**kwargs):
            calls.append((self.method,deepcopy(query),kwargs)); self.counts['mock_choose'] += 1
            action = 'LEFT' if self.counts['mock_choose'] == 1 else 'UP'
            choice = dict(action=action,afterstate=[2]+[0]*15,score=4,value=1.,status='ACTIVE',value_kind='estimated_return',
                action_values={action:dict(afterstate=[2]+[0]*15,score=4,value=1.,tail_value=1.-4/2048.)})
            if self.method != 'H2': choice['selection'] = dict(baseline_choice=deepcopy(choice),candidate_choice=deepcopy(choice))
            return choice
    def episode(seed,act,p_four,max_steps):
        assert (p_four,max_steps) == (.1,2000); environment_seeds.append(seed)
        actions = [act([1,1]+[0]*14,0),act([2,1]+[0]*14,1)]
        return dict(seed=seed,actions=actions)
    monkeypatch.setattr(runner.old,'run_episode',episode)
    monkeypatch.setattr(runner.old,'compact_trace',lambda game:dict(actions=game['actions']))
    status = ['CUTOFF']
    monkeypatch.setattr(runner.old,'game_result',lambda game,query,counts,seconds:dict(status=status[0],utility=7.,policy_counts=counts))
    for query in runner.QUERIES:
        for method in ('H2','ZERO','LEARNED'):
            row = runner.play(Planner(method),2,query,method,7)
            assert row['seed'] == 14490200007 and row['result']['utility'] is None
            assert [r['previous_action'] for r in row['choices']] == ['DOWN','LEFT']
            expected = [None,None] if method == 'H2' else [14482070000,14482070001]
            assert [r['simulation_seed'] for r in row['choices']] == expected
            assert row['result']['policy_counts'] == dict(mock_choose=2)
            for choice in row['choices']:
                assert choice['work'] == dict(mock_choose=1)
                if method != 'H2':
                    assert choice['selection']['candidate_choice']['action_values']
                    assert choice['selection']['baseline_choice']['action_values']
    assert environment_seeds == [14490200007]*6
    assert [c[2] for c in calls if c[0] == 'H2'] == [{}]*4
    for method in ('ZERO','LEARNED'):
        assert [c[2] for c in calls if c[0] == method] == [dict(simulation_seed=14482070000,previous_action='DOWN'),dict(simulation_seed=14482070001,previous_action='LEFT')]*2
    status[0] = 'WON'
    assert runner.play(Planner('H2'),2,'risk1','H2',7)['result']['utility'] == 7.


def test_all_models_and_protocol_are_frozen_before_any_new_control(local_tmp,monkeypatch):
    source, _, _ = example_fixture(local_tmp,monkeypatch)
    examples = runner.build_examples(source)
    source_dir = local_tmp/'retained'; source_dir.mkdir()
    for name,payload in zip(('source_capsule.json','run.json','analysis.json'),source_fixture()):
        (source_dir/name).write_text(json.dumps(payload))
    events = []; evaluated = []
    class Pool:
        def __init__(self,**kwargs): assert kwargs == dict(max_workers=4)
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def submit(self,function,*args): return SimpleNamespace(result=lambda value=function(*args):value)
    def snapshot(directory):
        assert (directory/'source_capsule.json').is_file() and len(json.loads((directory/'examples.json').read_text())['examples']) == 256
        events.append('snapshot')
    def train(source,rows,directory):
        assert events[0] == 'snapshot' and not evaluated
        frozen = json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
        assert frozen['settings']['new_training_environment_samples'] == 0
        assert len(rows) == 64 and {e['life'] for e in rows} == {source['life']}
        assert all(Counter(e['split'] for e in rows if e['query'] == q) == dict(TRAIN=16,VALIDATION=16) for q in runner.QUERIES)
        events.append(('train',source['life'])); return dict(life=source['life'],queries={'frozen':True})
    def evaluate(source,trained,directory):
        frozen = json.loads((directory/'frozen_training.json').read_text())
        assert frozen['status'] == 'trained_frozen'
        assert [r['life'] for r in frozen['lifecycles']] == list(runner.LIVES)
        assert frozen['eval_lifecycles'] == [] and trained['queries'] == {'frozen':True}
        assert len([e for e in events if isinstance(e,tuple) and e[0] == 'train']) == 4
        evaluated.append(source['life']); events.append(('eval',source['life']))
        return dict(life=source['life'])
    monkeypatch.setattr(runner,'SOURCE',source_dir); monkeypatch.setattr(runner,'build_examples',lambda s:deepcopy(examples))
    monkeypatch.setattr(runner,'snapshot_code',snapshot); monkeypatch.setattr(runner,'ProcessPoolExecutor',Pool)
    monkeypatch.setattr(runner,'as_completed',lambda futures:reversed(futures))
    monkeypatch.setattr(runner,'train_lifecycle',train); monkeypatch.setattr(runner,'evaluate_lifecycle',evaluate)
    directory = local_tmp/'run'; runner.run(directory)
    result = json.loads((directory/'run.json').read_text())
    assert events == ['snapshot',*[('train',life) for life in runner.LIVES],*[('eval',life) for life in runner.LIVES]]
    assert result['status'] == 'complete' and [r['life'] for r in result['eval_lifecycles']] == list(runner.LIVES)
    assert result['settings']['physical_games'] == 192 and result['settings']['epochs'] == 32
    assert result['inherited_costs'] == dict(prior=1,v143_experiment={'v143':2})

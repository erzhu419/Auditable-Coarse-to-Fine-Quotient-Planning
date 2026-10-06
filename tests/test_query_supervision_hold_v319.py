"""A missing frozen census is a paid cohort HOLD, not effect inference."""
from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import query_supervision_run_v319 as driver


INSUFFICIENT = 'V319 insufficient eligible complete FIT anchors for the frozen census'


class FrozenHead:
    def __init__(self, updates=10):
        self.updates = updates
        self.reward_weights = np.zeros(8)
        self.risk_weights = np.zeros(8)
        self.freeze()
    def freeze(self):
        self.reward_weights.flags.writeable = self.risk_weights.flags.writeable = False


def evaluation(life, task, version=None):
    return dict(estimated_p_four=.1 if task=='A' else .5, head_version=version,
        game_summaries=[dict(seed=319900000000+life*1000000+(100000 if task=='B' else 0)+i,
            status='LOST',utility=0.,steps=1) for i in range(32)],
        counts=dict(environment=dict(raw_tile_productions=128)),cpu_seconds=1.5)


def extraction():
    return dict(reconstructed_raw_tiles=1234,parsed_records=40,compressed_bytes_read=500,
        selected_training_records=4,cpu_seconds=.25)


def inherited_life(life=0):
    initial = {}
    for task in ('A','B'):
        teacher = dict(file=f'FIRST_{life}_{task}_v0.npz',version=0,updates=10)
        initial[task] = dict(context_id=0 if task=='A' else 1,
            planning_belief=dict(estimated_p_four=.1 if task=='A' else .5),
            head_versions=dict(FIRST_LOCAL=teacher))
    return dict(lifecycle=life,parent=life%4,initial=initial,rounds={})


def dataset(fit_steps):
    return dict(afterstates=np.ones((fit_steps+2,16),np.int32),
        postspawn_boards=np.ones((fit_steps+2,16),np.int32),
        ends=np.array([fit_steps,fit_steps+2],np.int64),fit_game_count=1,fit_step_end=fit_steps)


def query_receipt(roots=None):
    receipt = dict(counts=dict(selector_draws=4),planning_counts=dict(leaf_queries=7),
        representation_counts=dict(reward_table_lookups=224),cpu_seconds=2.5,seconds=3.)
    if roots is not None:
        receipt.update(chosen_afterstates=roots.copy(),validmask=np.array([1,0,0,0],np.int32))
    return receipt


def install_initial_mocks(monkeypatch):
    monkeypatch.setattr(driver,'_restore_first',lambda template,version,runtime:
        (FrozenHead(version['updates']),dict(restored_version=version)))
    monkeypatch.setattr(driver,'_new_head',lambda template,kind,runtime,first:
        (FrozenHead(first.updates),{}))
    monkeypatch.setattr(driver,'_evaluate',lambda leaf,life,task,belief,runtime,engine,version=None:
        evaluation(life,task,version))
    monkeypatch.setattr(driver,'load_leaf',lambda source,runtime:(object(),{}))
    monkeypatch.setattr(driver,'NativeValueStream',lambda *args:object())
    monkeypatch.setattr(driver,'_child_cpu',lambda:0.)


@pytest.mark.parametrize('failure',['prepare','valid'])
def test_census_domain_failure_stops_before_labels_and_retains_partial_evaluation_and_query_costs(tmp_path,monkeypatch,failure):
    install_initial_mocks(monkeypatch)
    monkeypatch.setattr(driver,'GROUPS',2)
    life = inherited_life()
    data = dataset(3 if failure=='prepare' else 6)
    datasets = {'1':dict(A=data,B=data),'2':dict(A=data,B=data)}
    def retained(*args):
        yield life,datasets,extraction()
        raise AssertionError('A held parent must not replace the failed lifecycle')
    monkeypatch.setattr(driver,'iter_query_lifecycles',retained)
    queried = []
    def query(first,preboards,seed,runtime,**kwargs):
        queried.append(1)
        roots = driver.prepare_anchors(data,2)['natural_roots']
        return query_receipt(roots)
    monkeypatch.setattr(driver,'query_roots',query)
    def no_labels(*args,**kwargs):
        raise AssertionError('Unavailable census must precede supervision and fitting')
    monkeypatch.setattr(driver,'supervise',no_labels)
    monkeypatch.setattr(driver,'fit_supervision',no_labels)

    parent = driver._run_parent(dict(parent=0),{},tmp_path)
    assert parent['status'] == 'HOLD_CENSUS' and len(parent['lifecycles']) == 1
    partial = parent['lifecycles'][0]
    saved = json.loads((tmp_path/'lifecycle_receipts/life_0_partial.json').read_text())
    assert saved == partial
    assert partial['rounds'] == {'1':{}}
    assert partial['census_failure']['task'] == 'A' and partial['census_failure']['round'] == 1
    assert sum(len(value['game_summaries']) for task in partial['initial'].values()
        for value in task['evaluations'].values()) == 128
    if failure=='prepare':
        assert queried == [] and partial['census_failure']['query'] is None
    else:
        assert queried == [1]
        assert partial['census_failure']['valid_anchors'] == 1
        assert partial['census_failure']['requested_groups'] == 2
        assert partial['census_failure']['query'] == query_receipt()

    parent.update(cpu_seconds=10.,compiler_cpu_seconds=2.)
    account = driver.accounting(dict(accounting=dict(economic_source_and_target_cpu_seconds=100.)),
        [partial],[parent],cpu=3.,wall=4.)
    assert account['new_training_raw_tiles'] == 0 and account['new_evaluation_games'] == 128
    assert account['new_evaluation_environment_counts'] == dict(raw_tile_productions=512)
    assert account['new_evaluation_cpu_seconds'] == 6.
    assert account['retained_raw_tiles_reconstructed'] == 1234
    assert account['new_experiment_cpu_seconds'] == 15.
    assert account['economic_source_v317_and_experiment_cpu_seconds'] == 115.
    expected_query = {} if failure=='prepare' else dict(selector_draws=4)
    assert account['physical_census_query_counts'] == expected_query
    for arm in driver.UPDATING_ARMS:
        assert account['per_arm'][arm]['rootgroups'] == 0
        assert account['per_arm'][arm]['economic_census_query_counts'] == expected_query
        expected_cpu = 0. if failure=='prepare' else 2.5+partial['census_failure']['anchor_cpu_seconds']
        assert account['per_arm'][arm]['economic_census_cpu_seconds'] == expected_cpu


def test_unexpected_valueerror_is_not_reclassified_as_a_census_hold(tmp_path,monkeypatch):
    install_initial_mocks(monkeypatch)
    life = inherited_life()
    monkeypatch.setattr(driver,'iter_query_lifecycles',lambda *args:iter([(life,{'1':dict(A={})},extraction())]))
    def bad_prepare(*args):
        raise ValueError('Actual dataset structure changed')
    monkeypatch.setattr(driver,'prepare_anchors',bad_prepare)
    with pytest.raises(ValueError,match='Actual dataset structure changed'):
        driver._run_parent(dict(parent=0),{},tmp_path)
    assert not (tmp_path/'lifecycle_receipts/life_0_partial.json').exists()


def completed_row(life):
    inherited = inherited_life(life)
    initial, rounds = {}, {'1':{},'2':{}}
    for task in ('A','B'):
        teacher = inherited['initial'][task]['head_versions']['FIRST_LOCAL']
        initial[task] = dict(head_version=teacher,planning_belief=inherited['initial'][task]['planning_belief'],
            evaluations=dict(SOURCE=evaluation(life,task),FIRST_LOCAL=evaluation(life,task,teacher)))
        previous = {arm:teacher for arm in driver.UPDATING_ARMS}
        for number in ('1','2'):
            arms = {}
            for arm in driver.UPDATING_ARMS:
                version = dict(file=f'{life}_{task}_{arm}_v{number}.npz',saved_bytes=7,
                    base_file=previous[arm]['file'])
                arms[arm] = dict(supervision=dict(counts=dict(supervision_start_spawns=4),
                    environment_counts=dict(raw_tile_productions=4),planning_counts={},representation_counts={},
                    cpu_seconds=.5,group_artifact=dict(saved_bytes=5,array_bytes=128)),
                    fit=dict(fitted_rootgroups=1,learning_counts=dict(rootgroup_updates=1),
                        normalization_counts={},cpu_seconds=.3),head_version=version,
                    evaluations=evaluation(life,task,version))
                previous[arm] = version
            rounds[number][task] = dict(arms=arms,census=dict(query=query_receipt(),
                anchor_cpu_seconds=.1,saved_bytes=3))
    return dict(lifecycle=life,parent=life%4,initial=initial,rounds=rounds,extraction=extraction())


def test_whole_cohort_hold_skips_inference_keeps_completed_parents_and_counts_only_paid_stages(tmp_path,monkeypatch):
    source_dir = tmp_path/'source'; source_dir.mkdir()
    source = source_dir/'summary.json'
    source.write_text(json.dumps(dict(status='EXPERIMENT_COMPLETE',
        source_provenance=dict(parents=[dict(parent=p) for p in range(4)]),
        accounting=dict(economic_source_and_target_cpu_seconds=100.))))
    (source_dir/'audit.json').write_text(json.dumps(dict(independent_valid=True)))
    partial = completed_row(0)
    partial['rounds'] = {'1':{}}
    partial['census_failure'] = dict(task='A',round=1,reason=INSUFFICIENT,query=None)
    parents = {p:dict(parent=p,status='HOLD_CENSUS' if p==0 else 'PARENT_COMPLETE',
        lifecycles=[partial] if p==0 else [completed_row(life) for life in range(p,16,4)],
        source_setup={},cpu_seconds=10.,compiler_cpu_seconds=2.,wall_seconds=4.) for p in range(4)}
    monkeypatch.setattr(driver,'_run_parent',lambda source,document,out:deepcopy(parents[source['parent']]))
    class InlinePool:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def submit(self,function,*args):return SimpleNamespace(result=lambda:function(*args))
    monkeypatch.setattr(driver,'ProcessPoolExecutor',InlinePool)
    monkeypatch.setattr(driver,'as_completed',lambda jobs:reversed(jobs))
    def no_inference(*args,**kwargs):
        raise AssertionError('Incomplete frozen cohort must not enter summarize or bootstrap')
    monkeypatch.setattr(driver,'summarize',no_inference)
    cpu_ticks,wall_ticks = iter((0.,5.)),iter((100.,109.))
    monkeypatch.setattr(driver,'process_time',lambda:next(cpu_ticks))
    monkeypatch.setattr(driver,'perf_counter',lambda:next(wall_ticks))

    out = tmp_path/'result'
    result = driver.run(source,out)
    assert result['status'] == 'HOLD_CENSUS'
    assert result['settings']['lifecycles'] == list(range(16))
    assert [row['lifecycle'] for row in result['by_lifecycle']] == [0,1,2,3,5,6,7,9,10,11,13,14,15]
    assert result['summary']['primary_self_improvement_status'] == 'HOLD_CENSUS'
    assert result['summary']['coverage_intervention_status'] == 'HOLD_CENSUS'
    assert 'final_ab_contrasts' not in result['summary']
    for flag in ('primary_self_improvement_supported','coverage_intervention_supported',
            'retained_improvement_supported','coverage_mechanism_supported'):
        assert not result['summary'][flag]
    assert result['summary']['census_failures'] == [dict(lifecycle=0,parent=0,**partial['census_failure'])]
    account = result['accounting']
    assert account['new_evaluation_games'] == 128+12*384
    assert account['new_training_raw_tiles'] == 12*32
    assert account['group_files'] == account['new_head_files'] == 12*8
    assert account['new_experiment_cpu_seconds'] == 53.
    assert account['economic_source_v317_and_experiment_cpu_seconds'] == 153.
    persisted = json.loads((out/'summary.json').read_text())
    for key in ('status','summary','accounting','by_lifecycle'):
        assert persisted[key] == result[key]
    assert json.loads((out/'parent_0_receipt.json').read_text())['status'] == 'HOLD_CENSUS'

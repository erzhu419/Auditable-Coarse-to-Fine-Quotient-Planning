"""New stream namespace, preserved censored costs, and pre-reference freezing."""
from collections import Counter
from concurrent.futures import Future
from copy import deepcopy
import gzip
import json
from pathlib import Path
import pytest
from scripts import run_controlled_predictive_heldout_replication_v101 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    p=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_heldout_runner_v101.checks.json'
    r=json.loads(p.read_text()) if p.exists() else dict(attempts=[])
    r['attempts'].append(dict(failed_tests=request.session.testsfailed-before,
        environment_transitions=0, model_transitions=0, neural_fits=0,
        scope='Synthetic reference records and mocked execution ordering only.'))
    p.write_text(json.dumps(r,indent=2)+'\n')


def fixture_rows():
    root=dict(id='life_9_reward_4',life=9,query='reward',episode=4,board=[1]*10+[0]*6)
    raw=[];ground,planning,outcomes=Counter(),Counter(),Counter()
    for replica in range(2):
        seed=8310000000+101009*10000000+400+replica
        for option in m.OPTIONS:
            duration=0 if option=='H2' else int(option.split('_')[1])
            game=dict(seed=seed,initial_board=root['board'],status='CUTOFF',steps_count=3,
                work=dict(sampled_transitions=3,environment_random_draws=6))
            row=dict(option=option,replica=replica,env_seed=seed,model_seed=seed+1000000000000,
                game=game,planning_counts=dict(model_uniform_draws=12),controller=dict(
                    events=[{}],initiation_step=0,selected_option=option,fragment_actions=min(duration,3)))
            raw.append(row);ground.update(game['work']);planning.update(row['planning_counts']);outcomes['CUTOFF']+=1
    log=dict(trajectories=len(raw),ground_work=dict(ground),planning_counts=dict(planning),
        outcomes=dict(outcomes),censored_root=True,pair_deltas={})
    return root,raw,log


def test_reference_audit_detects_seed_reuse_roster_and_initial_board_changes():
    root,raw,log=fixture_rows()
    assert all(m.audit_reference(root,raw,log,2).values())
    changed=deepcopy(raw);changed[0]['env_seed']-=1000*10000000
    assert not m.audit_reference(root,changed,log,2)['paired_fresh_streams']
    changed=deepcopy(raw);changed[0]['game']['initial_board']=[0]*16
    assert not m.audit_reference(root,changed,log,2)['root_boards_match']
    changed=deepcopy(raw);changed[-1]=deepcopy(changed[0])
    assert not m.audit_reference(root,changed,log,2)['trajectory_roster_complete']


def test_reference_job_retains_both_blocks_and_all_censored_cost(tmp_path,monkeypatch):
    root,raw,log=fixture_rows()
    monkeypatch.setattr(m,'REPLICAS',2);monkeypatch.setattr(m,'BLOCK_SIZE',1)
    monkeypatch.setattr(m.LearnedDynamics,'from_payload',lambda _:None)
    def sample(selected,rule,life,replicas,max_steps):
        assert selected==root and rule is None and life==101009 and replicas==2 and max_steps==2000
        return [],raw,log
    monkeypatch.setattr(m,'sample_root',sample)
    result=m.reference_job(root,tmp_path,{})
    assert result['log']['censored_root'] and result['log']['ground_work']['sampled_transitions']==30
    assert all(result['checks'].values())
    with gzip.open(tmp_path/'references'/root['id']/'games.jsonl.gz','rt') as f:
        retained=list(map(json.loads,f))
    assert [r['block'] for r in retained]==['A']*5+['B']*5
    assert len(retained)==10 and all(r['root_id']==root['id'] for r in retained)


def test_all_predictions_saved_before_first_reference_is_submitted(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir();(source/'supplied_dynamics.json').write_text('{}')
    output=tmp_path/'result';root,_,log=fixture_rows();root['predictions_marker']=[2,1,3]
    monkeypatch.setattr(m,'SOURCE',source);monkeypatch.setattr(m,'snapshot',lambda _:None)
    monkeypatch.setattr(m,'load_cohort',lambda *_:([root],dict(unique_roots=1)))
    def reference(selected,directory,payload):
        frozen=json.loads((directory/'cohort.json').read_text())
        assert frozen['roots']==[root]
        assert json.loads((directory/'run.json').read_text())['cohort']==frozen
        return dict(root_id=selected['id'],log=log,checks={},seconds=0)
    class Pool:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def submit(self,fn,*args):
            future=Future();future.set_result(fn(*args));return future
    monkeypatch.setattr(m,'reference_job',reference);monkeypatch.setattr(m,'ProcessPoolExecutor',Pool)
    m.run(output)
    result=json.loads((output/'run.json').read_text())
    assert result['status']=='complete' and len(result['references'])==1
    assert result['cohort']['roots'][0]['predictions_marker']==[2,1,3]

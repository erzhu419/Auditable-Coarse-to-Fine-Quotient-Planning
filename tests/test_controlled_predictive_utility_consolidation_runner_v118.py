"""Independent utility history, source pairing, inherited snapshots and streams."""
import ast
from collections import Counter
from copy import deepcopy
import io
import json
from pathlib import Path
import random
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_utility_consolidation_v118 as runner
from acfqp.science.controlled_predictive_consolidation_v117 import BankKnowledge

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = runner.ROOT / 'reports/controlled_predictive_utility_consolidation_runner_v118.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed-before,
        development_work=dict(WORK), newly_sampled_environment_transitions=0,
        new_synthetic_transitions=0, neural_model_fits=0,
        scope='mock inherited histories, utility games, planning and exact seed arithmetic'))
    path.write_text(json.dumps(log,indent=2)+'\n')


class Bound:
    def __init__(self,payload,module_id):
        self.payload = deepcopy(payload)
        self.module_id = module_id
        self.counts = Counter()
        WORK['mock_payload_reads'] += 1
    def to_payload(self):
        return dict(self.payload,module_id=self.module_id,counts=dict(self.counts))
    def can_route(self,module_id):
        return module_id in self.payload.get('available_modules',[module_id])


def source_life():
    return dict(life=0,phases=[dict(name=name,p4=p4,checkpoint=dict(
        router_payload=dict(module_id=batch,p4=p4),
        models={track:dict(stamp=f'{track}:{batch}',module_id=batch,counts={})
            for track in ('SHARED','SPLIT','MSE_SELECTED')},
        mse_selected_origin=dict(batch=0,mode='SHARED')))
        for batch,(name,p4) in enumerate(runner.PHASES)])


def test_three_phase_utility_history_preserves_mse_and_evaluates_b_end_with_current_router(tmp_path,monkeypatch):
    source = source_life(); original = deepcopy(source)
    template = SimpleNamespace(program='fixed')
    class Router:
        def __init__(self,payload):
            self.payload = deepcopy(payload); self.module_id = payload['module_id']
        def to_payload(self):
            return deepcopy(self.payload)
        def to_rule(self,base):
            assert base is template
            p4 = self.payload['p4']
            return SimpleNamespace(program=base.program,spawn_distribution=((1,1-p4),(2,p4)))
        def observe(self,*args):
            raise AssertionError('new observations must not update inherited router')
    def forbidden_fit(*args,**kwargs):
        raise AssertionError('V118 must not refit any consequence model')
    monkeypatch.setattr(BankKnowledge,'fit',forbidden_fit)
    monkeypatch.setattr(runner,'LearnedDynamics',SimpleNamespace(from_payload=lambda _:template))
    monkeypatch.setattr(runner,'SpawnMemory',SimpleNamespace(from_payload=Router))
    monkeypatch.setattr(runner,'bound_model',Bound)
    def validation(life,batch,models,previous,rule,module_id,stream):
        assert previous['stamp'] == ('SHARED:0' if batch==1 else 'SPLIT:1')
        assert previous['stamp'] != models['MSE_SELECTED']['stamp']
        selected = models['SPLIT'] if batch==1 else previous
        return Bound(selected,module_id).to_payload(),dict(
            selected_candidate='NEW_SPLIT' if batch==1 else 'KEEP',selection_complete=True),[]
    outer,controls = [],[]
    def prediction(life,batch,base,module_id,versions,stream):
        outer.append((batch,module_id,deepcopy(versions)))
        return [],{}
    def control(method,query,replica,seed,p_true,rule,module_id,payload):
        WORK['mock_outer_control_games'] += 1
        controls.append(dict(method=method,module_id=module_id,p4=dict(rule.spawn_distribution)[2],
            payload=deepcopy(payload)))
        return {},{}
    monkeypatch.setattr(runner,'source_validation',validation)
    monkeypatch.setattr(runner,'prediction_games',prediction)
    monkeypatch.setattr(runner,'control_game',control)
    result = runner.lifecycle_run(source,tmp_path,{})
    checkpoints = [phase['checkpoint'] for phase in result['phases']]
    assert [cp['utility_selected_origin'] for cp in checkpoints] == [
        dict(batch=0,mode='SHARED'),dict(batch=1,mode='SPLIT'),dict(batch=1,mode='SPLIT')]
    assert [cp['models']['UTILITY_SELECTED']['stamp'] for cp in checkpoints] == ['SHARED:0','SPLIT:1','SPLIT:1']
    for batch,cp in enumerate(checkpoints):
        assert cp['models']['MSE_SELECTED'] == original['phases'][batch]['checkpoint']['models']['MSE_SELECTED']
        assert all(cp['checks'].values())
    _,module_id,versions = outer[2]
    assert module_id == 2 and versions['B_END']['UTILITY_SELECTED']['stamp'] == 'SPLIT:1'
    assert versions['A_END'] == checkpoints[0]['models'] and versions['B_END'] == checkpoints[1]['models']
    b_end_games = [game for game in controls if game['method']=='UTILITY_B_END_PLAN']
    assert len(b_end_games)==4 and all(game['module_id']==2 and game['p4']==.1
        and game['payload']['stamp']=='SPLIT:1' and game['payload']['module_id']==1 for game in b_end_games)
    assert source==original and all(result['checks'].values())


def test_source_validation_pairs_24_games_and_retains_own_keep_on_censoring(monkeypatch):
    previous = dict(stamp='OWN_UTILITY',module_id=0)
    models = {mode:dict(stamp=mode,module_id=1) for mode in ('SHARED','SPLIT','MSE_SELECTED')}
    before = deepcopy((previous,models)); calls=[]
    def control(candidate,query,replica,seed,p_true,rule,module_id,payload):
        WORK['mock_source_validation_games'] += 1
        calls.append(dict(candidate=candidate,query=query,replica=replica,seed=seed,payload=deepcopy(payload)))
        if candidate=='KEEP':
            assert payload is previous
        status = 'CUTOFF' if candidate=='NEW_SPLIT' and query=='risk_goal' and replica==3 else 'LOST'
        row = dict(method=candidate,query=query,replica=replica,seed=seed,
            result=dict(status=status,utility=0. if candidate=='KEEP' else 10.))
        return row,deepcopy(row)
    monkeypatch.setattr(runner,'bound_model',Bound)
    monkeypatch.setattr(runner,'control_game',control)
    selected,choice,games = runner.source_validation(2,1,models,previous,object(),1,io.StringIO())
    assert len(calls)==len(games)==24
    assert {call['payload']['stamp'] for call in calls} == {'OWN_UTILITY','SHARED','SPLIT'}
    for replica in range(4):
        paired = [call for call in calls if call['replica']==replica]
        assert len(paired)==6 and len({call['seed'] for call in paired})==1
    assert not choice['selection_complete'] and choice['selected_candidate']=='KEEP'
    assert selected['stamp']=='OWN_UTILITY' and selected['module_id']==1
    assert (previous,models)==before


def expression(path,function,kind='environment'):
    method = next(node for node in ast.parse(path.read_text()).body
        if isinstance(node,ast.FunctionDef) and node.name==function)
    if kind=='environment':
        value = next(node.value for node in ast.walk(method) if isinstance(node,ast.Assign)
            and any(isinstance(target,ast.Name) and target.id=='seed' for target in node.targets))
    else:
        value = next(node.args[0] for node in ast.walk(method) if isinstance(node,ast.Call)
            and isinstance(node.func,ast.Attribute) and node.func.attr=='Random')
    return compile(ast.Expression(value),str(path),'eval')


def evaluate(expr,values):
    return eval(expr,{'__builtins__':{},'VERSION_BASE':runner.VERSION_BASE,
        'PLANNING_OFFSET':runner.PLANNING_OFFSET},values)


def test_new_environment_and_planning_namespaces_are_disjoint_from_all_historical_streams():
    current = Path(runner.__file__); scripts=current.parent
    fresh = {}
    for role,function in [('validation','source_validation'),('prediction','prediction_games'),('control','lifecycle_run')]:
        expr = expression(current,function); seeds=[]
        for life in range(4):
            for batch in (range(1,3) if role=='validation' else range(3)):
                cases = ([dict(policy_index=p,replica=r) for p in range(3) for r in range(2)]
                    if role=='prediction' else [dict(replica=r) for r in range(4 if role=='validation' else 2)])
                seeds.extend(evaluate(expr,dict(life=life,batch=batch,**case)) for case in cases)
        assert len(seeds)==len(set(seeds))
        fresh[role]=set(seeds)
    new_environment=set.union(*fresh.values())
    assert len(new_environment)==sum(map(len,fresh.values()))==128
    planning_expr=expression(current,'control_game','planning')
    new_planning={evaluate(planning_expr,dict(seed=seed)) for seed in fresh['validation']|fresh['control']}
    assert new_planning=={seed+50000000 for seed in fresh['validation']|fresh['control']}
    assert len(new_planning)==56 and not new_environment&new_planning
    historical_environment,historical_planning=set(),set()
    for version in (115,116,117):
        basename={115:'regime_memory',116:'context_consequences',117:'consolidation'}[version]
        path=scripts/f'run_controlled_predictive_{basename}_v{version}.py'
        functions=[('source','lifecycle_run'),('control','evaluation_game' if version==115 else 'control_game')]
        if version!=115:
            functions.append(('prediction','prediction_games'))
        for role,function in functions:
            expr=expression(path,function)
            plan_expr=expression(path,function,'planning') if role=='control' else None
            for life in range(4):
                for phase_index in range(3):
                    if role=='source':
                        cases=[dict(episode=i,local_episode=i) for i in range(6 if version==115 else 18)]
                    elif role=='prediction':
                        cases=[dict(policy_index=p,replica=r) for p in range(3) for r in range(2)]
                    elif version==115:
                        cases=[dict(after_game=n,replica=r) for n in ((6,) if phase_index==0 else (1,3,6)) for r in range(2)]
                    else:
                        cases=[dict(replica=r) for r in range(2)]
                    for case in cases:
                        seed=evaluate(expr,dict(life=life,phase_index=phase_index,**case))
                        historical_environment.add(seed)
                        if plan_expr is not None:
                            historical_planning.add(evaluate(plan_expr,dict(seed=seed)))
    assert not (new_environment|new_planning)&(historical_environment|historical_planning)
    WORK.update(new_environment_seeds_checked=len(new_environment),new_planning_seeds_checked=len(new_planning),
        historical_environment_seeds_checked=len(historical_environment),historical_planning_seeds_checked=len(historical_planning))


def test_control_missing_branch_uses_h2_keeps_cost_and_binds_planning_offset(monkeypatch):
    monkeypatch.setattr(runner,'bound_model',Bound)
    seed=runner.VERSION_BASE+3000000; knowledge_used=[]
    def choose(board,query,knowledge,rule,rng,depth,work):
        assert rng.random()==random.Random(seed+50000000).random()
        knowledge_used.append(knowledge); work['model_uniform_draws']+=4
        WORK['mock_planner_calls']+=1
        return dict(action='LEFT',value=0.,metrics={},policy=None,branches=[],action_values={'LEFT':{}})
    def run_episode(env_seed,actor,p_true,max_steps):
        WORK['mock_control_wrapper_games']+=1
        assert env_seed==seed and actor((1,)+(0,)*15,0)=='LEFT'
        return dict(status='LOST',return_score=2048,steps_count=1,seconds=0.,
            work={'sampled_transitions':1,'environment_random_draws':6})
    monkeypatch.setattr(runner.planner,'choose',choose)
    monkeypatch.setattr(runner,'run_episode',run_episode)
    row,raw=runner.control_game('SPLIT_PLAN','risk_goal',0,seed,.1,object(),9,
        dict(stamp='unavailable',available_modules=[0]))
    assert knowledge_used==[None]
    assert row['result']['fallback_h2'] and row['result']['routed_module_id']==9
    assert row['result']['utility']==-3.
    assert row['result']['environment_counts']['sampled_transitions']==1
    assert row['result']['planning_counts']['model_uniform_draws']==4
    assert row['result']['prediction_counts']=={}
    assert raw['decisions'][0]['action_values']=={'LEFT':{}}

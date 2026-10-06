"""V153 replay and source wiring fixtures; no native planner or scientific run."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from scripts import analyze_controlled_predictive_module_diagnosis_v153 as audit
from scripts import run_controlled_predictive_module_diagnosis_v153 as runner
from acfqp.science.controlled_predictive_policy_modules_v151 import RootConsequences
from acfqp.science.controlled_predictive_module_diagnosis_v153 import run_branch

TEMP=Path(__file__).resolve().parents[1]/'reports/v153_runtime_tmp'
WORK=Counter();ENVIRONMENT=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'analyzer_checks.json';payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__==__name__ for i in request.session.items),
        failures=request.session.testsfailed-before,new_environment_samples=ENVIRONMENT['sampled_transitions'],
        environment_counts=dict(ENVIRONMENT),work=dict(WORK),training_updates=0,native_planner_calls=0,
        scope='Synthetic retained roots and short fixed-board branches; native value checks stubbed, phase/commitment/RNG/returns audited.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def test_settings_seeds_and_exact_four_mode_roster_match_runner():
    assert audit.expected_settings()==runner.settings()
    roots=[dict(root_id=f'{l}:{q}:{source}:{slot}',life=l,query=q,source_method=source,slot=slot)
        for l in audit.LIVES for q in audit.QUERIES for source in audit.SOURCES for slot in range(4)]
    roster=runner.branch_roster(roots)
    assert len(roster)==4096 and len({r['branch_id'] for r in roster})==4096
    seeds=[]
    for root in roots:
        for suffix in range(16):
            expected=audit.branch_seed(root,suffix);seeds.append(expected)
            assert expected==runner.branch_seed(root['life'],root['query'],root['source_method'],root['slot'],suffix)
    assert len(set(seeds))==1024 and all(15320000000<=s<15324000000 for s in seeds)


def test_actual_root_preparation_and_frozen_prediction_accounting_match_independent_reader():
    with TemporaryDirectory(prefix='analyzer_source_',dir=TEMP) as name:
        directory=Path(name);capsule=dict(models=[],source_traces=[]);models={}
        for life in audit.LIVES:
            for query in audit.QUERIES:
                model=RootConsequences();model.freeze();payload=model.to_payload();path=directory/f'{life}_{query}.json';path.write_text(json.dumps(payload))
                metadata=dict(life=life,query=query,model_ref=path.name,frozen_state=model.state())
                capsule['models'].append(metadata);models[life,query]=dict(metadata=metadata,weights={})
            trace=directory/f'life_{life}.jsonl.gz';capsule['source_traces'].append(dict(life=life,path=str(trace)))
            with gzip.open(trace,'wt') as output:
                for query in audit.QUERIES:
                    for method in audit.SOURCES:
                        for slot in range(4):
                            choices=[dict(afterstate=[0]+[1+i%7]*15,module_decision=dict(boundary=method=='H2' or i%3==0)) for i in range(20)]
                            row=dict(life=life,query=query,method=method,replica=slot*4,checkpoint=-1 if method=='H2' else 4,
                                physical_id=f'{life}:{query}:{-1 if method=="H2" else 4}:{method}:{slot*4}',seed=15290000000+life*1000000+slot*4,
                                choices=choices,initial_board=[1]+[0]*15,spawned_cells=[0]*20,spawned_ranks=[2]*20)
                            output.write(json.dumps(row)+'\n')
        roots,preparation=runner.prepare_roots(capsule,directory);frozen=dict(roots=roots,preparation=preparation,branch_roster=runner.branch_roster(roots))
        checks,work=audit.preparation_checks(capsule,frozen,models)
        assert all(checks.values()),checks
        assert preparation['source_rows_read']==preparation['source_games_selected']==64
        assert work['root_prediction_counts']['root_predictions']==64
        assert all(r['replica']==4*r['slot'] and r['source_step']==(r['selected_boundary_index']*(1 if r['source_method']=='H2' else 3)) for r in roots)
        changed=deepcopy(frozen);changed['roots'][0]['prediction']['advantage']=1.;changed['branch_roster'][0]['seed']+=1
        damaged,_=audit.preparation_checks(capsule,changed,models)
        assert not damaged['root_predictions'] and not damaged['branch_roster']
        WORK.update(source_fixture_rows_read=192,real_preparation_predictions=64,
            prediction_oracle_records=128,model_payload_saves=8,model_loads=8)


class LegalPlanner:
    def __init__(self):self.counts=Counter();self.calls=0
    def choose(self,board,query):
        actions=('LEFT','DOWN','RIGHT','UP');start=self.calls%4;self.calls+=1
        for action in actions[start:]+actions[:start]:
            after,score,changed=audit.prior.ground.swipe_board_v1(tuple(board),audit.prior.ground.Swipe2048Action(action));WORK['stub_legality_swipes']+=1
            if changed:break
        self.counts['choose_calls']+=1;WORK['stub_planner_calls']+=1
        return dict(action=action,afterstate=list(after),score=score,status='ACTIVE',value=0.,tail_value=0.,action_values={})


@pytest.mark.parametrize('mode,limit',[('H_H2',3),('M_H2',10),('H_GATE',10),('M_GATE',10)])
def test_independent_replay_checks_actual_prefix_gate_and_environment(mode,limit):
    bank={q:LegalPlanner() for q in audit.QUERIES};model=RootConsequences();model._weights={-1:(1.,0.,0.)};model.freeze()
    row=run_branch([1,1]+[0]*14,bank,'risk1',mode,model,123,max_steps=limit)
    ENVIRONMENT.update(row['result']['environment_counts']);WORK.update(real_branch_predictions=model.counts['root_predictions'])
    with patch.object(audit.prior.planning,'planning_counts_valid',return_value=True), \
            patch.object(audit.prior.local,'compact_choice_valid',return_value=True), \
            patch.object(audit.prior.h1,'root_choice_checks',return_value={}):
        checks,swipes=audit.replay_branch(row,model.weights,max_steps=limit);WORK['reported_audit_replay_swipes']+=swipes
        assert all(checks.values()),checks
        assert row['result']['status']=='CUTOFF' and row['result']['utility'] is None
        if mode=='M_GATE':
            changed=deepcopy(row);changed['choices'][0]['policy_key']='risk1'
            damaged,swipes=audit.replay_branch(changed,model.weights,max_steps=limit);WORK['reported_audit_replay_swipes']+=swipes
            assert not damaged['branch_forced_query']
        if mode=='H_GATE':
            changed=deepcopy(row);changed['choices'][1]['module_decision']['remaining_after']=0
            damaged,swipes=audit.replay_branch(changed,model.weights,max_steps=limit);WORK['reported_audit_replay_swipes']+=swipes
            assert not damaged['module_commitment']

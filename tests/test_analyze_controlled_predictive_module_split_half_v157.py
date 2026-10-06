"""Synthetic end-to-end split-half integrity and leakage failures."""
from copy import deepcopy
from collections import Counter
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts import analyze_controlled_predictive_module_split_half_v157 as audit
from scripts import run_controlled_predictive_module_split_half_v157 as runner
from acfqp.science.controlled_predictive_module_split_half_v157 import build_pairs,build_selection_rows,summarize

TEMP=Path(__file__).resolve().parents[1]/'reports/v157_runtime_tmp'
WORK=Counter()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value)+'\n')


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'analyzer_checks.json';payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__==__name__ for i in request.session.items),
        failures=request.session.testsfailed-before,new_environment_samples=0,native_planner_calls=0,model_fits=0,
        production_rows_read=0,work=dict(WORK),scope='Synthetic complete quartet fixture plus wrong evaluation half, damaged pair, and omitted root artifacts.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def experiment():
    with TemporaryDirectory(prefix='analyzer_',dir=TEMP) as name:
        directory=Path(name);latest=directory/'v156';branches=directory/'v153';branches.mkdir();latest.mkdir()
        roots=[];roster=[];traces=[];lifecycles=[];examples=[];transitions=0
        for life in audit.LIVES:
            path=branches/f'life_{life}.jsonl.gz';traces.append(dict(life=life,path=str(path)));lifecycles.append(dict(life=life,branch_trace=path.name))
            with gzip.open(path,'wt') as output:
                for query in audit.QUERIES:
                    for method in audit.SOURCES:
                        for slot in range(4):
                            value=0. if slot==2 else (.25 if slot%2==0 else -.25)
                            root=dict(root_id=f'{life}:{query}:{method}:{slot}',life=life,query=query,source_method=method,slot=slot,
                                board=[1,slot+1]+[0]*14,prediction=dict(components=[value,0.,0.],advantage=value,accept=value>0));roots.append(root)
                            examples.append(dict(root_id=root['root_id'],targets={'REPAIR_H2':[(5+slot)/2048,0.,0.],'REPAIR_GATE':[5/2048,0.,0.]}))
                            for suffix in range(16):
                                for mode in audit.MODES:
                                    score=1000+suffix
                                    if mode=='M_H2':score+=20+slot if suffix<8 else -10+slot
                                    if mode=='M_GATE':score+=-5-slot if suffix<8 else 15+slot
                                    row=dict(branch_id=f'{root["root_id"]}:{suffix}:{mode}',root_id=root['root_id'],life=life,query=query,
                                        source_method=method,slot=slot,suffix=suffix,mode=mode,seed=audit.seed(root,suffix),root_board=root['board'],
                                        result=dict(score=score,steps=4+suffix,status='LOST',components=[score/2048,1,0]))
                                    transitions+=row['result']['steps'];output.write(json.dumps(row)+'\n')
                                    roster.append({k:row[k] for k in ('branch_id','root_id','suffix','mode','seed')})
        cost=dict(retained_environment_transitions=transitions)
        save(latest/'run.json',dict(status='complete'));save(latest/'analysis.json',dict(complete=True,primary_complete=True))
        save(latest/'source_capsule.json',dict(roots=roots,examples=examples,retained_training_cost=cost))
        save(branches/'run.json',dict(status='complete',lifecycles=lifecycles));save(branches/'analysis.json',dict(complete=True,primary_complete=True))
        save(branches/'frozen_inputs.json',dict(roots=roots,branch_roster=roster))
        capsule=dict(roots=roots,examples=examples,branch_roster=roster,source_traces=traces,retained_training_cost=cost,cost_refs=[],
            source_run_ref=str(latest/'run.json'),source_analysis_ref=str(latest/'analysis.json'),source_capsule_ref=str(latest/'source_capsule.json'),
            branch_run_ref=str(branches/'run.json'),branch_analysis_ref=str(branches/'analysis.json'),branch_frozen_ref=str(branches/'frozen_inputs.json'))
        save(directory/'source_capsule.json',capsule)
        frozen=dict(status='frozen',settings=runner.settings(),halves=deepcopy(runner.HALVES),root_ids=[r['root_id'] for r in roots],
            output_refs=deepcopy(runner.OUTPUT_REFS),inherited_cost_refs=[]);save(directory/'frozen_inputs.json',frozen)
        outcomes,work=runner.extract_outcomes(capsule);WORK['synthetic_runner_raw_rows_read']+=work['rows']
        pairs=build_pairs(roots,outcomes);selections=build_selection_rows(roots,pairs);summary=summarize(selections)
        for key,value in (('outcomes',outcomes),('pairs',pairs),('selections',selections),('summary',summary)):save(directory/runner.OUTPUT_REFS[key],value)
        save(directory/'run.json',dict(frozen,status='complete',extraction=work,pairs=len(pairs),selection_rows=len(selections),summary_groups=len(summary),seconds=0.))
        yield directory


def checked(directory):
    result=audit.analyze(directory);WORK['synthetic_analyzer_raw_rows_read']+=result['costs']['raw_rows_read']
    WORK['independent_selection_rows']+=result['costs']['selection_rows_recomputed']
    return result,{c['name']:c['passed'] for c in result['checks']}


def test_independent_reconstruction_and_equal_weight_summaries_match_actual_core(experiment):
    assert audit.expected_settings()==runner.settings()
    result,checks=checked(experiment)
    assert result['complete'] and result['primary_complete'] and all(checks.values()),checks
    assert result['costs']['raw_rows_read']==4096 and result['costs']['raw_trace_files_read']==4
    assert result['costs']['model_files_read']==result['costs']['new_environment_samples']==0
    assert len(result['summary'])==72
    gate=next(g for g in result['summary'] if all(g[k]==v for k,v in dict(query='risk1',target='GATE',eval_target='GATE',source_method='ALL',direction='ALL').items()))
    assert gate['roots']==32 and gate['row_count']==64 and len(gate['per_history'])==4
    assert gate['gain_vs_old']<0 and gate['selection_optimism']>0


@pytest.mark.parametrize('damage,failed',[('half','opposite_half_selection'),('pair','paired_outcomes'),('root','compact_extraction')])
def test_damaged_eval_half_pair_or_missing_root_prevents_completion(experiment,damage,failed):
    key={'half':'selections','pair':'pairs','root':'outcomes'}[damage];path=experiment/runner.OUTPUT_REFS[key];rows=audit.read(path)
    if damage=='half':rows[0]['eval_half']=rows[0]['train_half']
    elif damage=='pair':rows[0]['components']['GATE'][0]+=.5
    else:
        root=rows[0]['root_id'];rows=[r for r in rows if r['root_id']!=root]
    save(path,rows);result,checks=checked(experiment)
    assert not result['complete'] and not result['primary_complete'] and not checks[failed]
    assert result['costs']['raw_rows_read']==4096

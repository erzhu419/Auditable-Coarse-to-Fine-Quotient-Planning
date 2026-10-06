"""Independent prefix binding and terminal-utility control-variate arithmetic."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_module_control_variate_v159 as audit
from scripts import run_controlled_predictive_module_control_variate_v159 as runner
from acfqp.science import controlled_predictive_module_control_variate_v159 as core
from acfqp.science import controlled_predictive_module_precision_v158 as precision

TEMP=Path(__file__).resolve().parents[1]/'reports/v159_runtime_tmp'
WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'analyzer_checks.json';payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__==__name__ for i in request.session.items),
        failures=request.session.testsfailed-before,new_environment_samples=0,new_training_updates=0,native_planner_calls=0,
        production_rows_read=0,work=dict(WORK),scope='Synthetic prefix corruption and independent corrected-label/RAW-evaluation/variance arithmetic.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def test_first_eight_prefix_binding_centering_and_candidate_corruption():
    assert audit.expected_settings()==runner.settings()
    after=[2,1,2,1,1,2,1,2,2,1,2,1,1,2,0,0]
    original=dict(branch_id='0:risk1:H2:0:TRAIN:0:H_GATE',root_id='0:risk1:H2:0',life=0,query='risk1',source_method='H2',slot=0,
        split='TRAIN',suffix=0,mode='H_GATE',actions=['LEFT']*10,choices=[dict(afterstate=list(after)) for _ in range(10)],
        spawned_cells=[14,15]*5,spawned_ranks=[1,2]*5)
    def critic(board):
        WORK['synthetic_scalar_critic_calls']+=1
        return sum((i+1)*rank for i,rank in enumerate(board))*.25
    correction=core.branch_correction(original,critic)
    checks,counts=audit.prefix_checks(original,correction,critic)
    assert all(checks.values()),checks
    assert len(correction['steps'])==8 and counts['critic_calls']==counts['spawn_outcomes_enumerated']==32
    damaged=deepcopy(correction);damaged['steps'][0]['candidates'][0]['value']+=.5
    checks,_=audit.prefix_checks(original,damaged,critic)
    assert not checks['critic_values']
    damaged=deepcopy(correction);damaged['steps'][0]['afterstate'][0]=0
    checks,_=audit.prefix_checks(original,damaged,critic)
    assert not checks['prefix_steps']
    assert all(sum(c['probability'] for c in s['candidates'])==1 for s in correction['steps'])


def test_independent_cv_selectors_use_train_and_score_raw_eval_with_cutoffs():
    roots=[];pairs=[];corrections=[]
    for life in range(4):
        for query in ('risk1','risk8'):
            for source in ('H2','LEARN8'):
                for slot in range(4):
                    root=dict(root_id=f'{life}:{query}:{source}:{slot}',life=life,query=query,source_method=source,slot=slot,
                        prediction=dict(advantage=1 if slot%2==0 else -1,accept=slot%2==0));roots.append(root)
                    for split in ('TRAIN','EVAL'):
                        for suffix in range(32):
                            advantage=(suffix-15.5)*.1+(.2 if split=='TRAIN' else -.3)+slot*.1
                            pairs.append(dict(**{k:root[k] for k in core.METADATA},split=split,suffix=suffix,complete=True,
                                components=[advantage,0.,0.],advantage=advantage))
                            for mode,c in (('H_GATE',.1),('M_GATE',.4+(suffix-15.5)*.08)):
                                corrections.append(dict(**{k:root[k] for k in core.METADATA},split=split,suffix=suffix,mode=mode,
                                    branch_id=f'{root["root_id"]}:{split}:{suffix}:{mode}',correction=c))
    corrected=audit.adjusted_pairs(pairs,corrections);expected=core.build_adjusted_pairs(pairs,corrections)
    assert audit.equivalent(corrected,expected)
    train=[p for p in pairs if p['split']=='TRAIN'];evaluation=[p for p in pairs if p['split']=='EVAL']
    adjusted_train=[p for p in corrected if p['split']=='TRAIN'];raw=precision.freeze_selectors(roots,train)
    controlled=audit.cv_selectors(roots,adjusted_train);assert audit.equivalent(controlled,core.freeze_cv_selectors(roots,adjusted_train))
    results=audit.evaluate_control(raw,controlled,evaluation);actual=core.evaluate_control(raw,controlled,evaluation)
    assert audit.equivalent(results,actual)
    assert audit.equivalent(audit.variance_report(corrected),core.variance_report(corrected))
    WORK.update(synthetic_pairs=4096,synthetic_corrections=8192,independent_selector_rows=192,independent_scoring_rows=384)
    indexed={(p['root_id'],p['suffix']):p for p in evaluation}
    for row in results['cv']['rows']:
        expected=(int(row['accept'])-int(row['old_accept']))*indexed[row['root_id'],0]['advantage']
        assert row['gains']['vs_old']['samples'][0]==expected
        assert row['eval_components'][0]==pytest.approx(sum(indexed[row['root_id'],s]['advantage'] for s in range(32))/32)
    damaged=deepcopy(evaluation);damaged[0].update(complete=False,components=None,advantage=None)
    results=audit.evaluate_control(raw,controlled,damaged);actual=core.evaluate_control(raw,controlled,damaged)
    assert audit.equivalent(results,actual)
    affected=next(row for row in results['contrasts'] if row['query']=='risk1' and row['budget']==32 and row['source_method']=='ALL')
    assert not affected['complete'] and affected['gain']['mean'] is None and affected['gain']['conditional_suffix_ci95'] is None
    WORK['independent_scoring_rows']+=384

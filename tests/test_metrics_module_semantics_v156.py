"""Only the new representation contrast needs additional statistical checks."""
from collections import Counter
import json
from pathlib import Path
import pytest
from scripts import analyze_controlled_predictive_module_semantics_v156 as audit

TEMP=Path(__file__).resolve().parents[1]/'reports/v156_runtime_tmp'
WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'metrics_checks.json';data=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(tests=sum(i.module.__name__==__name__ for i in request.session.items),
        failures=request.session.testsfailed-before,work=dict(WORK),environment_samples=0,native_calls=0,training_updates=0))
    path.write_text(json.dumps(data,indent=2)+'\n')


def rows():
    result=[]
    for life in range(4):
        value=life+1.
        for query in ('risk1','risk8'):
            for replica in (0,4,8,12):
                for kind in ('LOCAL','SEMANTIC'):
                    for arm in ('REPAIR_H2','REPAIR_GATE'):
                        for source in ('H2','LEARN8'):
                            for slot in range(4):
                                new=value if kind=='SEMANTIC' else 0.
                                result.append(dict(life=life,query=query,replica=replica,fold_id=f'{life}:{query}:{replica}',
                                    representation=kind,arm=arm,source_method=source,root_id=f'{life}:{query}:{source}:{slot}',
                                    split='heldout' if 4*slot==replica else 'train',
                                    old_prediction=dict(components=[0.,0.,0.],advantage=0.,accept=False),
                                    prediction=dict(components=[new,0.,0.],advantage=new,accept=new>0),
                                    targets={'REPAIR_H2':[value,0.,0.],'REPAIR_GATE':[value/2,0.,0.]}))
    WORK['synthetic_rows']+=len(result)
    return result


def test_semantic_minus_local_pairs_same_history_and_target():
    outcome=audit.aggregate(rows());WORK['aggregate_calls']+=1
    assert outcome['primary_complete']
    for split in ('heldout','train'):
        for query in ('risk1','risk8'):
            for source in ('ALL','H2','LEARN8'):
                arms=outcome['semantic_minus_local'][split][query][source]
                assert arms['REPAIR_H2']['means']['new_mse_own']==pytest.approx(-7.5)
                assert arms['REPAIR_GATE']['means']['new_mse_own']==pytest.approx(0.)
                for arm in arms.values():
                    assert arm['means']['new_mse_gate']==pytest.approx(0.)
                    assert arm['means']['policy_gain_change_gate']==pytest.approx(1.25)
                    assert arm['means']['policy_gain_change_h2']==pytest.approx(2.5)
                    assert [c['differences']['policy_gain_change_gate'] for c in arm['lifecycles']]==[.5,1.,1.5,2.]
    assert not any(token in json.dumps(outcome).lower() for token in ('ci95','standard_error','confidence_interval'))


def test_source_specific_no_change_stays_in_paired_gain_denominator():
    data=rows()
    for row in data:
        if row['representation']=='SEMANTIC' and row['source_method']=='LEARN8':
            row['prediction']=dict(components=[0.,0.,0.],advantage=0.,accept=False)
    outcome=audit.aggregate(list(reversed(data)));WORK['aggregate_calls']+=1
    assert outcome['primary_complete']
    for query in ('risk1','risk8'):
        groups=outcome['semantic_minus_local']['heldout'][query]
        for arm in ('REPAIR_H2','REPAIR_GATE'):
            assert groups['ALL'][arm]['means']['policy_gain_change_gate']==pytest.approx(.625)
            assert groups['H2'][arm]['means']['policy_gain_change_gate']==pytest.approx(1.25)
            assert groups['LEARN8'][arm]['means']['policy_gain_change_gate']==0.
    reduced=[r for i,r in enumerate(data) if i!=next(j for j,s in enumerate(data)
        if s['representation']=='SEMANTIC' and s['split']=='heldout')]
    missing=audit.aggregate(reduced);WORK['aggregate_calls']+=1
    assert not missing['primary_complete']


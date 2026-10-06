"""Fresh-pool selector algebra and conditional variance on synthetic outcomes."""
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
from statistics import mean, variance

import pytest

from acfqp.science.controlled_predictive_module_precision_v158 import (
    build_pairs, freeze_selectors, evaluate)

TEMP = Path(__file__).resolve().parents[1]/'reports/v158_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'; data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, synthetic_work=dict(WORK), production_data_reads=0,
        environment_samples=0, model_samples=0, native_calls=0, training_updates=0))
    path.write_text(json.dumps(data, indent=2)+'\n')


def root(life=0, query='risk1', source='H2', slot=0):
    return dict(root_id=f'{life}:{query}:{source}:{slot}', life=life, query=query,
        source_method=source, slot=slot, prediction=dict(accept=slot % 3 == 0))


def all_roots():
    return [root(life, query, source, slot) for life in range(4) for query in ('risk1', 'risk8')
        for source in ('H2', 'LEARN8') for slot in range(4)]


def train_value(item, suffix):
    return 2. if item['slot'] % 2 else (2. if suffix < 8 else -4. if suffix < 16 else 1.)


def eval_value(item, suffix):
    return item['life']+item['slot']+1.+2*(item['source_method']=='LEARN8')+(item['slot']+1)*(suffix-15.5)/4


def outcomes(roots, train_fn=train_value):
    records = []
    for split in ('TRAIN', 'EVAL'):
        for index, item in enumerate(roots):
            for suffix in range(32):
                delta = train_fn(item, suffix) if split == 'TRAIN' else eval_value(item, suffix)
                base = 1000.+100.*suffix
                for mode, score in (('H_GATE', base), ('M_GATE', base+delta)):
                    records.append(dict(**{k:item[k] for k in ('root_id','life','query','source_method','slot')},
                        branch_id=f'{split}:{item["root_id"]}:{suffix}:{mode}', split=split, suffix=suffix, mode=mode,
                        seed=(10000 if split=='TRAIN' else 1000000)+index*100+suffix,
                        status='WON', components=[score, 0., 1.], steps=20+suffix))
    WORK['synthetic_outcomes_generated'] += len(records)
    return list(reversed(records))


def pairs(roots, records, split):
    WORK['build_pairs_calls'] += 1
    return build_pairs(roots, records, split)


def selectors(roots, rows):
    WORK['freeze_selectors_calls'] += 1
    return freeze_selectors(roots, rows)


def evaluation(selected, rows):
    WORK['evaluate_calls'] += 1
    return evaluate(selected, rows)


def test_pair_components_apply_query_weights_and_keep_all_32_suffixes():
    roots = [root(query=q) for q in ('risk1','risk8')]; records = outcomes(roots)
    for record in records:
        if record['mode']=='H_GATE': record.update(components=[10.,0.,1.],status='WON')
        else: record.update(components=[12.,1.,0.],status='LOST')
    for split in ('TRAIN','EVAL'):
        result = pairs(roots, records, split)
        assert len(result)==64
        for row in result:
            assert row['split']==split and row['complete'] and row['components']==[2.,1.,-1.]
            assert row['advantage']==(0. if row['query']=='risk1' else -14.)


def test_nested_training_is_strict_and_independent_evaluation_never_changes_frozen_choices():
    roots = [root(slot=slot) for slot in (0,1)]; records = outcomes(roots)
    selected = selectors(roots, pairs(roots,records,'TRAIN')); frozen = deepcopy(selected)
    by_key = {(s['slot'],s['budget']):s for s in selected}
    assert [by_key[0,n]['train_advantage'] for n in (8,16,32)]==[2.,-1.,0.]
    assert [by_key[0,n]['accept'] for n in (8,16,32)]==[True,False,False]
    assert all(by_key[1,n]['accept'] for n in (8,16,32))
    initial, _, _ = evaluation(selected,pairs(roots,records,'EVAL'))
    for record in records:
        if record['split']=='EVAL' and record['mode']=='M_GATE': record['components'][0]+=100.
    assert selectors(roots,pairs(roots,records,'TRAIN'))==frozen
    altered, _, _ = evaluation(selected,pairs(roots,records,'EVAL'))
    assert selected==frozen
    for old,new in zip(initial,altered):
        assert old['accept']==new['accept'] and old['train_components']==new['train_components']
        assert new['eval_advantage']==old['eval_advantage']+100.
        assert len(new['gains']['vs_old']['samples'])==32


def test_paired_precision_contrast_and_gain_intervals_use_all_roots_then_equal_histories():
    roots=all_roots(); records=outcomes(roots)
    chosen=selectors(roots,pairs(roots,records,'TRAIN'))
    rows,summaries,comparisons=evaluation(chosen,pairs(roots,records,'EVAL'))
    assert len(chosen)==len(rows)==192 and len(summaries)==18 and len(comparisons)==6
    for comparison in comparisons:
        query,source=comparison['query'],comparison['source_method']
        selected=[r for r in roots if r['query']==query and (source=='ALL' or r['source_method']==source)]
        expected_means=[]; history_variances=[]
        for life in range(4):
            local=[r for r in selected if r['life']==life]
            samples=[[-eval_value(r,s) if r['slot']%2==0 else 0. for s in range(32)] for r in local]
            expected_means.append(mean(mean(v) for v in samples))
            history_variances.append(sum(variance(v)/32 for v in samples)/len(local)**2)
            h=comparison['per_history'][life]
            assert h['roots']==len(local) and h['gain']['complete']
            assert h['gain']['conditional_suffix_se']==pytest.approx(math.sqrt(history_variances[-1]))
        expected_mean=mean(expected_means);se=math.sqrt(sum(history_variances)/16)
        assert comparison['roots']==len(selected) and comparison['complete'] and comparison['contrast']=='32-8'
        assert comparison['gain']['mean']==pytest.approx(expected_mean)
        assert comparison['gain']['conditional_suffix_se']==pytest.approx(se)
        assert comparison['gain']['conditional_suffix_ci95']==pytest.approx([expected_mean-1.96*se,expected_mean+1.96*se])
    for cell in summaries:
        selected=[r for r in roots if r['query']==cell['query'] and (cell['source_method']=='ALL' or r['source_method']==cell['source_method'])]
        assert cell['roots']==len(selected) and cell['complete']
        if cell['budget']==32: assert cell['means']['decision_change_rate']==.5
        for gain_name in ('vs_old','vs_reject','vs_accept'):
            history_means=[];history_variances=[]
            for life in range(4):
                local=[r for r in selected if r['life']==life]; samples=[]
                for item in local:
                    accepted=True if cell['budget']==8 else bool(item['slot']%2)
                    coefficient={'vs_old':int(accepted)-int(item['prediction']['accept']),
                        'vs_reject':int(accepted),'vs_accept':int(accepted)-1}[gain_name]
                    samples.append([coefficient*eval_value(item,s) for s in range(32)])
                history_means.append(mean(mean(v) for v in samples))
                history_variances.append(sum(variance(v)/32 for v in samples)/len(local)**2)
            assert cell['gains'][gain_name]['mean']==pytest.approx(mean(history_means))
            assert cell['gains'][gain_name]['conditional_suffix_se']==pytest.approx(math.sqrt(sum(history_variances)/16))
    # Shared EVAL noise cancels when n32 and n8 choose the same action; it is not two independent arm variances.
    for row in rows:
        if row['budget']==32 and row['slot'] in (2,3):
            assert row['gains']['vs_old']['samples']==[0.]*32
            assert row['gains']['vs_old']['mean_variance']==0.


@pytest.mark.parametrize('split,suffix', [('TRAIN',31),('EVAL',3)])
def test_cutoff_is_retained_and_only_affected_budgets_groups_lose_completeness(split,suffix):
    roots=all_roots();records=outcomes(roots);bad=root(0,'risk1','H2',0)['root_id']
    next(r for r in records if (r['root_id'],r['split'],r['suffix'],r['mode'])==(bad,split,suffix,'M_GATE'))['status']='CUTOFF'
    train=pairs(roots,records,'TRAIN');test=pairs(roots,records,'EVAL')
    incomplete=next(r for r in (train if split=='TRAIN' else test) if r['root_id']==bad and r['suffix']==suffix)
    assert not incomplete['complete'] and incomplete['components'] is None and incomplete['advantage'] is None
    chosen=selectors(roots,train);rows,summaries,comparisons=evaluation(chosen,test)
    for row in rows:
        affected=row['root_id']==bad and (split=='EVAL' or row['budget']==32)
        assert row['complete']==(not affected)
        if affected:
            assert row['gains']['vs_old']['mean'] is None and not row['gains']['vs_old']['complete']
            assert len(row['gains']['vs_old']['samples'])==32
            if split=='TRAIN': assert row['accept'] is None and row['gains']['vs_old']['samples']==[None]*32
            else: assert row['gains']['vs_old']['samples'][suffix] is None
    for cell in summaries:
        affected=cell['query']=='risk1' and cell['source_method'] in ('ALL','H2') and (split=='EVAL' or cell['budget']==32)
        assert cell['complete']==(not affected)
        if affected: assert cell['gains']['vs_old']['conditional_suffix_ci95'] is None
    for cell in comparisons:
        affected=cell['query']=='risk1' and cell['source_method'] in ('ALL','H2')
        assert cell['complete']==(not affected)
        if affected: assert cell['gain']['mean'] is None and cell['gain']['conditional_suffix_se'] is None


def test_unchanged_selectors_keep_zero_gain_and_full_cohort_denominator():
    roots=all_roots();records=outcomes(roots,lambda r,s:1. if r['prediction']['accept'] else 0.)
    chosen=selectors(roots,pairs(roots,records,'TRAIN'))
    rows,summaries,comparisons=evaluation(chosen,pairs(roots,records,'EVAL'))
    assert all(r['accept']==r['old_accept'] for r in rows)
    for cell in summaries:
        assert cell['complete'] and cell['roots'] in (16,32)
        assert cell['means']['decision_change_rate']==0.
        assert cell['gains']['vs_old']['mean']==cell['gains']['vs_old']['conditional_suffix_se']==0.
    for cell in comparisons:
        assert cell['complete'] and cell['gain']['mean']==0. and cell['gain']['conditional_suffix_ci95']==[0.,0.]


@pytest.mark.parametrize('corruption',['missing','duplicate'])
def test_incomplete_record_roster_is_not_confused_with_a_retained_cutoff(corruption):
    roots=[root()];records=outcomes(roots)
    train=[r for r in records if r['split']=='TRAIN']
    if corruption=='missing':train.pop()
    else:train.append(deepcopy(train[0]))
    with pytest.raises(ValueError):pairs(roots,train,'TRAIN')

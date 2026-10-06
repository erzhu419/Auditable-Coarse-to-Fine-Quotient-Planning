"""Synthetic spawn centering and unchanged-terminal decision comparisons."""
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
from statistics import mean, variance

import pytest

from acfqp.science import controlled_predictive_module_control_variate_v159 as core
from acfqp.science import controlled_predictive_module_precision_v158 as precision

TEMP = Path(__file__).resolve().parents[1]/'reports/v159_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'
    data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, synthetic_work=dict(WORK), production_data_reads=0,
        environment_samples=0, model_samples=0, native_calls=0, training_updates=0))
    path.write_text(json.dumps(data, indent=2)+'\n')


def critic(board):
    WORK['synthetic_critic_calls'] += 1
    return sum((i+1)*rank**2 for i, rank in enumerate(board))


def root(life=0, query='risk1', source='H2', slot=0):
    return dict(root_id=f'{life}:{query}:{source}:{slot}', life=life, query=query,
                source_method=source, slot=slot, prediction=dict(accept=life%2==0))


def synthetic_pairs(roots):
    pairs, corrections = [], []
    for split in ('TRAIN', 'EVAL'):
        for item in roots:
            meta = {k:item[k] for k in core.METADATA}
            for suffix in range(32):
                raw = (1. if split=='TRAIN' else 3.+item['life']+(suffix-15.5)/4)
                control = ((2. if suffix<8 else 0.) if split=='TRAIN' else .5*raw)
                if item['source_method']=='LEARN8': control = 0.
                pairs.append(dict(**meta, split=split, suffix=suffix, complete=True,
                                  components=[raw,0.,0.], advantage=raw))
                for mode, correction in (('H_GATE', .25), ('M_GATE', .25+control)):
                    corrections.append(dict(**meta, split=split, suffix=suffix, mode=mode,
                        branch_id=f'{item["root_id"]}:{split}:{suffix}:{mode}', correction=correction))
    WORK['synthetic_pairs_created'] += len(pairs)
    WORK['synthetic_corrections_created'] += len(corrections)
    return pairs, corrections


def test_exact_spawn_law_centers_any_fixed_critic_and_evaluates_each_candidate_once():
    after = [3]*16; after[1]=after[7]=0
    call_before = WORK['synthetic_critic_calls']
    term = core.spawn_term(after, 7, 2, critic)
    assert term['counts']==dict(spawn_outcomes_enumerated=4, critic_calls=4)
    assert WORK['synthetic_critic_calls']-call_before==4
    assert [(c['cell'],c['rank'],c['probability']) for c in term['candidates']]==[
        (1,1,.45),(1,2,.05),(7,1,.45),(7,2,.05)]
    assert sum(c['probability']*(c['value']-term['expected_value'])
               for c in term['candidates'])==pytest.approx(0.,abs=1e-12)
    assert term['observed_value']==term['candidates'][-1]['value']
    assert term['correction']==term['observed_value']-term['expected_value']
    assert after[1]==after[7]==0


@pytest.mark.parametrize('steps', [1, 10])
def test_retained_prefix_is_bounded_by_actual_steps_and_includes_last_spawn(steps):
    item = root()
    after = [2]*16; after[4]=0
    row = dict(**{k:item[k] for k in core.METADATA}, branch_id='branch', split='TRAIN',
        suffix=0, mode='M_GATE', actions=['LEFT']*steps,
        choices=[dict(afterstate=after) for _ in range(steps)],
        spawned_cells=[4]*steps, spawned_ranks=[2]*steps)
    before = deepcopy(row); count_before = WORK['synthetic_critic_calls']
    result = core.branch_correction(row, critic)
    n = min(8,steps)
    assert row==before and len(result['steps'])==n
    assert [s['step'] for s in result['steps']]==list(range(n))
    assert result['correction']==pytest.approx(n*(20.-(.9*5.+.1*20.)))
    assert result['counts']==dict(branch_records_processed=1, corrected_spawn_steps=n,
                                  spawn_outcomes_enumerated=2*n, critic_calls=2*n)
    assert WORK['synthetic_critic_calls']-count_before==2*n


def test_scalar_pair_sign_nested_strict_zero_and_cutoff_do_not_fabricate_components():
    roots = [root()]; raw, corrections = synthetic_pairs(roots)
    adjusted = core.build_adjusted_pairs(raw, corrections)
    assert adjusted[0]['control_difference']==2.
    assert adjusted[0]['raw_advantage']==1. and adjusted[0]['advantage']==-1.
    assert adjusted[0]['raw_components']==[1.,0.,0.] and adjusted[0]['components'] is None
    train = [p for p in adjusted if p['split']=='TRAIN']
    chosen = core.freeze_cv_selectors(roots,train)
    assert [s['train_advantage'] for s in chosen]==[-1.,0.,.5]
    assert [s['accept'] for s in chosen]==[False,False,True]
    assert all(s['complete'] and s['scalar_control'] and s['train_components'] is None for s in chosen)
    raw[31].update(complete=False,components=None,advantage=None)
    adjusted = core.build_adjusted_pairs(raw,corrections)
    assert adjusted[31]['advantage'] is None and adjusted[31]['control_difference']==0.
    chosen = core.freeze_cv_selectors(roots,[p for p in adjusted if p['split']=='TRAIN'])
    assert [s['complete'] for s in chosen]==[True,True,False]
    assert chosen[-1]['accept'] is None


def test_eval_uses_original_terminal_labels_with_paired_variance_and_unchanged_roots():
    roots = [root(life,query,source) for life in range(4) for query in precision.QUERIES
             for source in precision.SOURCES]
    raw, corrections = synthetic_pairs(roots)
    adjusted = core.build_adjusted_pairs(raw,corrections)
    raw_choices = precision.freeze_selectors(roots,[p for p in raw if p['split']=='TRAIN'])
    cv_choices = core.freeze_cv_selectors(roots,[p for p in adjusted if p['split']=='TRAIN'])
    before = deepcopy(cv_choices)
    evaluated = core.evaluate_control(raw_choices,cv_choices,[p for p in raw if p['split']=='EVAL'])
    assert cv_choices==before
    assert len(evaluated['contrasts'])==18
    for row in evaluated['cv']['rows']:
        assert row['eval_advantage']==3.+row['life']
        assert row['complete'] and row['train_components'] is None
    for group in evaluated['contrasts']:
        changed = group['budget'] in (8,16)
        factor = 1. if group['source_method']=='H2' else 0. if group['source_method']=='LEARN8' else .5
        expected_mean = -4.5*factor if changed else 0.
        expected_se = math.sqrt(variance([(s-15.5)/4 for s in range(32)])/32/4)*factor if changed else 0.
        assert group['gain']['mean']==pytest.approx(expected_mean)
        assert group['gain']['conditional_suffix_se']==pytest.approx(expected_se)
        assert group['gain']['conditional_suffix_ci95']==pytest.approx([
            expected_mean-1.96*expected_se,expected_mean+1.96*expected_se])
        assert group['roots']==(8 if group['source_method']=='ALL' else 4)
    # A zero coefficient cannot turn an unobserved terminal result into a known zero.
    damaged = deepcopy([p for p in raw if p['split']=='EVAL'])
    damaged[0].update(complete=False,components=None,advantage=None)
    incomplete = core.evaluate_control(raw_choices,cv_choices,damaged)
    primary = next(g for g in incomplete['contrasts'] if g['query']=='risk1'
                   and g['budget']==32 and g['source_method']=='ALL')
    assert not primary['complete'] and primary['gain']['mean'] is None
    unaffected = next(g for g in incomplete['contrasts'] if g['query']=='risk8'
                      and g['budget']==32 and g['source_method']=='ALL')
    assert unaffected['complete'] and unaffected['gain']['mean']==0.


def test_variance_report_equal_roots_then_histories_and_no_cutoff_dropping():
    roots = [root(life,source=source) for life in range(4) for source in precision.SOURCES]
    roots.append(root(0,slot=1))
    raw, corrections = synthetic_pairs(roots)
    adjusted = core.build_adjusted_pairs(raw,corrections)
    groups = core.variance_report(adjusted)
    assert len(groups)==12
    group = next(g for g in groups if g['split']=='EVAL' and g['query']=='risk1' and g['source_method']=='ALL')
    basevar = variance([3.+(s-15.5)/4 for s in range(32)])
    # History 0 has two corrected and one unchanged root; others have one of each.
    cv_ratio = mean([(.25+.25+1)/3, (.25+1)/2, (.25+1)/2, (.25+1)/2])
    covariance_ratio = mean([(.5+.5)/3,.5/2,.5/2,.5/2])
    assert group['roots']==9 and group['complete']
    assert group['means']['raw_mean']==4.5
    assert group['means']['raw_variance']==pytest.approx(basevar)
    assert group['means']['cv_variance']==pytest.approx(cv_ratio*basevar)
    assert group['means']['covariance_raw_control']==pytest.approx(covariance_ratio*basevar)
    assert group['variance_ratio']==pytest.approx(cv_ratio)
    assert group['means']['cv_mean']==pytest.approx(group['means']['raw_mean']-group['means']['control_mean'])
    damaged = next(p for p in adjusted if p['split']=='EVAL')
    damaged.update(complete=False,advantage=None,raw_advantage=None)
    groups = core.variance_report(adjusted)
    invalid = next(g for g in groups if g['split']=='EVAL' and g['query']=='risk1' and g['source_method']=='ALL')
    assert invalid['roots']==9 and not invalid['complete']
    assert invalid['means']['raw_variance'] is None and invalid['variance_ratio'] is None


def test_missing_or_duplicate_corrections_are_not_silently_dropped():
    raw, corrections = synthetic_pairs([root()])
    with pytest.raises(ValueError,match='paired roster'):
        core.build_adjusted_pairs(raw,corrections[:-1])
    with pytest.raises(ValueError,match='duplicate branch'):
        core.build_adjusted_pairs(raw,corrections+[corrections[0]])

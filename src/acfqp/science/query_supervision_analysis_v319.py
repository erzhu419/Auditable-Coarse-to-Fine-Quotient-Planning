"""Separate own-FIRST growth, coverage intervention and both-bank retention."""
from math import floor
import random
from statistics import mean

TASKS=('A','B')
UPDATING_ARMS=('FACTUAL_LOCAL','QUERY_LOCAL')
ARMS=('SOURCE','FIRST_LOCAL')+UPDATING_ARMS
PAIRS=(('QUERY_LOCAL','FIRST_LOCAL'),('QUERY_LOCAL','FACTUAL_LOCAL'),('QUERY_LOCAL','SOURCE'),
    ('FACTUAL_LOCAL','FIRST_LOCAL'),('FACTUAL_LOCAL','SOURCE'),('FIRST_LOCAL','SOURCE'))


def _bootstrap(rows,values,draws):
    groups=[[v for row,v in zip(rows,values) if row['parent']==p] for p in range(4)]
    rng=random.Random(31900001)
    distribution=sorted(mean(mean(rng.choices(group,k=4)) for group in groups) for _ in range(draws))
    def q(level):
        position=(draws-1)*level;lo=floor(position);hi=min(lo+1,draws-1)
        return distribution[lo]+(distribution[hi]-distribution[lo])*(position-lo)
    return dict(mean=mean(values),ci95=[q(.025),q(.975)],
        lifecycle_deltas={str(row['lifecycle']):v for row,v in zip(rows,values)},
        improved_equal_worse=[sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)],
        parent_mean_deltas={str(p):mean(group) for p,group in enumerate(groups)},
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REUSED_FIRST_COHORT')


def _status(contrast,hold,retention=False):
    if hold:return 'HOLD_CUTOFF'
    lo,hi=contrast['ci95']
    return ('SUPPORTED_NONDECREASE' if retention else 'SUPPORTED_GAIN') if (lo>=0 if retention else lo>0) else 'SUPPORTED_LOSS' if hi<0 else 'UNRESOLVED'


def summarize(lives,draws=20000):
    rows=sorted(lives,key=lambda r:r['lifecycle'])
    if len(rows)!=16 or [r['lifecycle'] for r in rows]!=list(range(16)) or any(r['parent']!=r['lifecycle']%4 for r in rows):
        raise ValueError('V319 retains all sixteen FIRST lifecycles and four fixed SOURCE parents')
    records=[];cutoffs=[];physical_games=0
    for row in rows:
        cells={}
        for task in TASKS:
            initial=row['initial'][task];teacher=initial['head_version'];p=initial['planning_belief']['estimated_p_four']
            previous={arm:teacher for arm in UPDATING_ARMS}
            stages=[('FIRST',initial['evaluations'])]
            for r in ('1','2'):
                stage=row['rounds'][r][task]
                if not stage['teacher_unchanged'] or stage['teacher_version']!=teacher:
                    raise ValueError('V319 selector and both labels keep the immutable actual FIRST teacher')
                counts=[]
                for arm in UPDATING_ARMS:
                    item=stage['arms'][arm];fit=item['fit']
                    if fit['alpha']!=.0025 or fit['learning_counts']['rootgroup_updates']!=stage['groups']:
                        raise ValueError('V319 arms share root-group count and current prediction/commit rule')
                    if item['head_version']['base_file']!=previous[arm]['file']:
                        raise ValueError('V319 private learner advances its own actual version')
                    counts.append(fit['learning_counts']['rootgroup_updates']);previous[arm]=item['head_version']
                if counts[0]!=counts[1]:raise ValueError('V319 root-group quotas match')
                stages.append(('ROUND'+r,{**initial['evaluations'],**{a:stage['arms'][a]['evaluations'] for a in UPDATING_ARMS}}))
            for checkpoint,evaluations in stages:
                values={}
                for arm,evaluation in evaluations.items():
                    games=evaluation['game_summaries']
                    expected=[319900000000+row['lifecycle']*1000000+(100000 if task=='B' else 0)+i for i in range(32)]
                    if len(games)!=32 or [g['seed'] for g in games]!=expected or evaluation['estimated_p_four']!=p:
                        raise ValueError('V319 every checkpoint keeps paired new seeds and immutable bank belief')
                    if any(g['status'] not in ('WON','LOST','CUTOFF') for g in games):raise ValueError('V319 explicit natural endpoint status')
                    cutoffs.extend(dict(lifecycle=row['lifecycle'],task=task,arm=arm,checkpoint=checkpoint,seed=g['seed'])
                        for g in games if g['status']=='CUTOFF')
                    if checkpoint=='FIRST' or arm in UPDATING_ARMS:physical_games+=len(games)
                    values[arm]=mean(g['utility'] for g in games)
                cells[checkpoint+'_'+task]=values
        records.append(dict(lifecycle=row['lifecycle'],parent=row['parent'],cells=cells))
    round_ab={};task_contrasts={};checkpoints={};hold=bool(cutoffs)
    for r in ('1','2'):
        round_ab[r]={left+'_minus_'+right:_bootstrap(records,[mean(row['cells']['ROUND'+r+'_'+t][left]-
            row['cells']['ROUND'+r+'_'+t][right] for t in TASKS) for row in records],draws) for left,right in PAIRS}
        for task in TASKS:
            key='ROUND'+r+'_'+task
            task_contrasts[key]={left+'_minus_'+right:_bootstrap(records,[row['cells'][key][left]-row['cells'][key][right]
                for row in records],draws) for left,right in PAIRS}
            checkpoints[key]={arm:task_contrasts[key][arm+'_minus_FIRST_LOCAL'] for arm in UPDATING_ARMS}
    final=round_ab['2'];primary=_status(final['QUERY_LOCAL_minus_FIRST_LOCAL'],hold)
    coverage=_status(final['QUERY_LOCAL_minus_FACTUAL_LOCAL'],hold)
    retention={task:_status(checkpoints['ROUND2_'+task]['QUERY_LOCAL'],hold,True) for task in TASKS}
    preserved=all(s=='SUPPORTED_NONDECREASE' for s in retention.values())
    return dict(final_ab_contrasts=final,round_ab_contrasts=round_ab,task_contrasts=task_contrasts,
        checkpoint_contrasts=checkpoints,by_lifecycle=records,complete_game_endpoints=not hold,cutoffs=cutoffs,
        physical_evaluation_games=physical_games,primary_contrast='QUERY_LOCAL_minus_FIRST_LOCAL_FINAL_AB',
        primary_self_improvement_status=primary,primary_self_improvement_supported=primary=='SUPPORTED_GAIN',
        coverage_intervention_status=coverage,coverage_intervention_supported=coverage=='SUPPORTED_GAIN',
        factual_self_improvement_status=_status(final['FACTUAL_LOCAL_minus_FIRST_LOCAL'],hold),
        final_net_gain_status=_status(final['QUERY_LOCAL_minus_SOURCE'],hold),task_retention_status=retention,
        retained_improvement_supported=primary=='SUPPORTED_GAIN' and preserved,
        coverage_mechanism_supported=primary=='SUPPORTED_GAIN' and preserved and coverage=='SUPPORTED_GAIN',
        bootstrap_seed=31900001,bootstrap_draws=draws,
        evidence_scope='New exactly matched one-step generative supervision on an existing sixteen-life FIRST cohort '
            'under four frozen SOURCE parents. Both arms share fixed teacher/anchors and paired fresh ground RNG; '
            'only supervised afterstate distribution changes. Group quotas match; actual address writes and compute can differ. '
            'The teacher is bootstrapped, not terminal truth. No fresh initial adaptation, unconditional source replication, '
            'ordinary online sampling-efficiency or general strategic-learning claim.')

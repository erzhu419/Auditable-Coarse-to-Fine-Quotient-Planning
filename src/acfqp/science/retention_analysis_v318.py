"""Four frozen mechanism effects on sixteen retained A lifecycles."""
from math import floor
import random
from statistics import mean

NEW_VIEWS = ('R1_OWN_LOCAL','R2_OWN_LOCAL','R2_FIRST_FULL','R2_FIRST_LOCAL')
VIEWS = ('FIRST','R1_OWN_FULL','R1_OWN_LOCAL','R2_OWN_FULL','R2_OWN_LOCAL','R2_FIRST_FULL','R2_FIRST_LOCAL')
EFFECTS = ('TARGET_FIRST_FULL_MINUS_OWN_FULL','LOCAL_OWN_MINUS_FULL_OWN',
    'TARGET_BY_LOCAL_INTERACTION','R1_LOCAL_MINUS_FULL')


def effects(values):
    local_own=values['R2_OWN_LOCAL']-values['R2_OWN_FULL']
    return dict(TARGET_FIRST_FULL_MINUS_OWN_FULL=values['R2_FIRST_FULL']-values['R2_OWN_FULL'],
        LOCAL_OWN_MINUS_FULL_OWN=local_own,
        TARGET_BY_LOCAL_INTERACTION=values['R2_FIRST_LOCAL']-values['R2_FIRST_FULL']-local_own,
        R1_LOCAL_MINUS_FULL=values['R1_OWN_LOCAL']-values['R1_OWN_FULL'])


def interval(rows, values, draws):
    groups=[[v for r,v in zip(rows,values) if r['parent']==p] for p in range(4)]
    rng=random.Random(31800001)
    distribution=sorted(mean(mean(rng.choices(group,k=4)) for group in groups) for _ in range(draws))
    def quantile(q):
        position=(draws-1)*q;lo=floor(position);hi=min(lo+1,draws-1)
        return distribution[lo]+(distribution[hi]-distribution[lo])*(position-lo)
    return dict(mean=mean(values),ci95=[quantile(.025),quantile(.975)],
        ci98_75=[quantile(.00625),quantile(.99375)],
        lifecycle_deltas={str(r['lifecycle']):v for r,v in zip(rows,values)},
        parent_mean_deltas={str(p):mean(group) for p,group in enumerate(groups)},
        improved_equal_worse=[sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)])


def status(ci, hold):
    return 'HOLD_CUTOFF' if hold else 'SUPPORTED_GAIN' if ci[0]>0 else 'SUPPORTED_LOSS' if ci[1]<0 else 'UNRESOLVED'


def summarize(lives, draws=20000):
    rows=sorted(lives,key=lambda r:r['lifecycle'])
    if len(rows)!=16 or [r['lifecycle'] for r in rows]!=list(range(16)) or any(r['parent']!=r['lifecycle']%4 for r in rows):
        raise ValueError('V318 retains all sixteen A lives and their original four parents')
    values=[];cutoffs=[];physical_games=0
    for row in rows:
        cell={}
        for view in VIEWS:
            evaluation=row['evaluations'][view];games=evaluation['game_summaries']
            seeds=[317900000000+row['lifecycle']*1000000+episode for episode in range(32)]
            if len(games)!=32 or [g['seed'] for g in games]!=seeds:
                raise ValueError('Every view keeps its original 32 paired A seeds')
            if any(g['status'] not in ('WON','LOST','CUTOFF') for g in games):
                raise ValueError('Every endpoint retains its actual natural or cutoff status')
            cutoffs.extend(dict(lifecycle=row['lifecycle'],view=view,seed=g['seed']) for g in games if g['status']=='CUTOFF')
            if view in NEW_VIEWS:physical_games+=len(games)
            cell[view]=mean(g['utility'] for g in games)
        values.append(cell)
    hold=bool(cutoffs)
    contrasts={name:interval(rows,[effects(cell)[name] for cell in values],draws) for name in EFFECTS}
    for contrast in contrasts.values():contrast['status98_75']=status(contrast['ci98_75'],hold)
    secondary={view:interval(rows,[cell[view]-cell['FIRST'] for cell in values],draws) for view in VIEWS if view!='FIRST'}
    for contrast in secondary.values():contrast['status95']=status(contrast['ci95'],hold)
    return dict(effects=contrasts,secondary_own_first=secondary,complete_game_endpoints=not hold,cutoffs=cutoffs,
        new_physical_evaluation_games=physical_games,bootstrap_seed=31800001,bootstrap_draws=draws,
        mechanism_family=dict(size=4,family_alpha=.05,interval_coverage=.9875,method='BONFERRONI'),
        evidence_scope='Frozen interventions on all sixteen V317 A lives under four reused SOURCE parents. '
            'Paired evaluation seeds are reused. No new training facts or independent confirmation. '
            'Exact FIT localization blocks all support-external generalization, including symmetry transfer. '
            'FIRST bootstrap changes both branch selection and continuation values. '
            'The interventions do not establish deployment value, cross-bank forgetting or overall retained growth.')

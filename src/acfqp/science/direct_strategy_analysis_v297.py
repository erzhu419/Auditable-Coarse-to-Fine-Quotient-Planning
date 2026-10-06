"""Independent stable-A whole-game performance of direct policy search."""
from math import floor
import random
from statistics import mean

ARMS = ('SOURCE', 'CEM', 'RANDOM_SEARCH')
PAIRS = (('CEM', 'SOURCE'), ('CEM', 'RANDOM_SEARCH'), ('RANDOM_SEARCH', 'SOURCE'))
PRIMARY = 'CEM_minus_SOURCE'
BOOTSTRAP_SEED = 29700001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def evaluation_seed(life, replica):
    return 297900010000+life*1000000+replica


def _bootstrap(rows, values, draws):
    groups={p:[v for row,v in zip(rows,values) if row['parent']==p] for p in range(4)}
    rng=random.Random(BOOTSTRAP_SEED)
    samples=sorted(mean(mean(rng.choices(group,k=4)) for group in groups.values()) for _ in range(draws))
    def quantile(q):
        index=(draws-1)*q; low=floor(index); high=min(low+1,draws-1)
        return samples[low]+(samples[high]-samples[low])*(index-low)
    return dict(mean=mean(values),ci95=[quantile(.025),quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']):v for row,v in zip(rows,values)},
        improved_equal_worse=[sum(v>0. for v in values),sum(v==0. for v in values),sum(v<0. for v in values)],
        adverse_lifecycles=[row['lifecycle'] for row,v in zip(rows,values) if v<0.],
        parent_mean_deltas={str(p):mean(group) for p,group in groups.items()},interval_scope=INTERVAL_SCOPE)


def _science(games, life):
    if len(games)!=32 or [g['seed'] for g in games]!=[evaluation_seed(life,i) for i in range(32)]:
        raise ValueError('V297 requires all 32 fresh independent paired science games')
    if any(g['status'] not in ('WON','LOST','CUTOFF') for g in games):
        raise ValueError('Natural terminal and cutoff outcomes must remain in science')
    return dict(games=32,mean_game_utility=mean(g['utility'] for g in games),
        wins=sum(g['status']=='WON' for g in games),losses=sum(g['status']=='LOST' for g in games),
        cutoffs=sum(g['status']=='CUTOFF' for g in games),steps=sum(g['steps'] for g in games))


def _training_choice(row, arm):
    rounds=row['search_rounds']; life=row['lifecycle']; cutoff_references=0
    if len(rounds)!=4 or [r['round_index'] for r in rounds]!=list(range(4)):
        raise ValueError('Each search requires its four complete chronological rounds')
    for round_index,round_row in enumerate(rounds):
        value=round_row['arms'][arm]; candidates=value['candidates']
        if len(candidates)!=8 or len({tuple(theta) for theta in candidates})!=8 or len(value['reference_ids'])!=8:
            raise ValueError('Each round requires eight unique executable candidate programs')
        fitnesses=[]
        for theta,reference_id in zip(candidates,value['reference_ids']):
            receipt=row['training_references'][reference_id]; games=receipt['game_summaries']
            seeds=[297200010000+life*1000000+round_index*1000+i for i in range(4)]
            if receipt['theta']!=theta or len(games)!=4 or [g['seed'] for g in games]!=seeds:
                raise ValueError('Search fitness must come from the candidate four training-game receipts')
            if (receipt['model_p_four']!=row['arms']['SOURCE']['model_p_four']
                    or receipt['environment_p_four']!=.1):
                raise ValueError('Training and science use the same source belief and stable-A law')
            if any(g['status'] not in ('WON','LOST','CUTOFF') for g in games):
                raise ValueError('Actual training terminal and cutoff outcomes must remain present')
            cutoff_references+=sum(g['status']=='CUTOFF' for g in games)
            fitnesses.append(mean(g['utility'] for g in games))
        winner=min(range(8),key=lambda i:(-fitnesses[i],i))
        if (fitnesses!=value['fitnesses'] or value['winner_index']!=winner
                or value['winner_theta']!=candidates[winner]):
            raise ValueError('Candidate selection must use training fitness with the frozen tie order')
    if row['arms'][arm]['theta']!=rounds[-1]['arms'][arm]['winner_theta']:
        raise ValueError('Science must execute the final training winner without reselection')
    return cutoff_references


def analyze(lifecycles, draws=20000):
    rows=sorted(lifecycles,key=lambda r:r['lifecycle'])
    if (len(rows)!=16 or [r['lifecycle'] for r in rows]!=list(range(16))
            or any(r['parent']!=r['lifecycle']%4 for r in rows)):
        raise ValueError('V297 requires all sixteen whole lives under four fixed source parents')
    records=[]; physical_games=physical_cutoffs=training_cutoffs=0
    for row in rows:
        life=row['lifecycle']; source=row['arms']['SOURCE']; arms={}; unique={}
        if source['theta']!=[0.,0.,0.,0.]:
            raise ValueError('SOURCE must execute the exact zero-parameter original policy')
        for arm in ARMS:
            value=row['arms'][arm]; theta=tuple(value['theta']); training=value['training']
            if (len(theta)!=4 or value['model_p_four']!=source['model_p_four']
                    or value['environment_p_four']!=.1):
                raise ValueError('All direct-policy arms use the same observed source belief in stable A')
            if training['game_references']!=(0 if arm=='SOURCE' else 128):
                raise ValueError('CEM and random search each require 128 complete training game references')
            if arm!='SOURCE' and _training_choice(row,arm)!=training['cutoff_games']:
                raise ValueError('Training cutoff references must match all candidate games')
            training_cutoffs+=training['cutoff_games']
            scored=_science(value['game_summaries'],life)
            if theta in unique:
                if unique[theta]['game_summaries']!=value['game_summaries']:
                    raise ValueError('Identical actors must share their exact science receipts')
            else:
                unique[theta]=value; physical_games+=scored['games']; physical_cutoffs+=scored['cutoffs']
            arms[arm]=dict(scored,theta=list(theta),model_p_four=value['model_p_four'],
                training_game_references=training['game_references'],training_cutoff_references=training['cutoff_games'])
        records.append(dict(lifecycle=life,parent=row['parent'],arms=arms,
            unique_science_actors=len(unique),physical_science_games=len(unique)*32,
            logical_science_game_references=3*32))
    arms={arm:dict(mean_game_utility=mean(r['arms'][arm]['mean_game_utility'] for r in records),
        **{key:sum(r['arms'][arm][key] for r in records) for key in ('games','wins','losses','cutoffs','steps',
                                                                 'training_game_references','training_cutoff_references')}) for arm in ARMS}
    contrasts={left+'_minus_'+right:_bootstrap(records,
        [r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records],draws)
        for left,right in PAIRS}
    complete=training_cutoffs+physical_cutoffs==0
    return dict(arms=arms,primary_contrast=PRIMARY,paired_contrasts=contrasts,
        stable_task_policy_gain_supported=complete and contrasts[PRIMARY]['ci95'][0]>0.,
        optimizer_contribution_supported=complete and contrasts['CEM_minus_RANDOM_SEARCH']['ci95'][0]>0.,
        complete_natural_games=complete,training_cutoff_references=training_cutoffs,
        physical_science_cutoffs=physical_cutoffs,physical_science_games=physical_games,
        logical_science_game_references=16*3*32,training_game_references_per_search_arm=16*128,
        by_lifecycle=records,bootstrap_seed=BOOTSTRAP_SEED,bootstrap_draws=draws,
        interval_scope=INTERVAL_SCOPE,estimator='EQUAL_SCIENCE_GAMES_THEN_LIFECYCLES',
        objective='DIRECT_STATEFUL_POLICY_PARAMETERS_SELECTED_BY_COMPLETE_TRAINING_GAME_UTILITY',
        control_interpretation='Random search matches candidate evaluations and complete training-game references. '
            'Strategy-dependent raw tile, computation and inherited source costs remain in the actual ledger.',
        evidence_scope='New independent stable-A complete-game policy utility, conditional on four fixed old source parents. '
            'Training winner scores do not define science outcomes. No continuous strategic learning, B adaptation '
            'or persistent strategy-library transfer is established.')

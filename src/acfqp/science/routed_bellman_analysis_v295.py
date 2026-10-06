"""Independent net control, routed sharing, correction and signed retention."""
from math import floor
import random
from statistics import mean

from .natural_episode_analysis_v292 import _aggregate
from .shadow_deployment_analysis_v293 import _direction

ARMS = ('FROZEN', 'SMOOTH_BELLMAN', 'ROUTED_BELLMAN')
PHASES = ('A', 'B', 'A_prime')
PAIRS = (('ROUTED_BELLMAN', 'FROZEN'), ('ROUTED_BELLMAN', 'SMOOTH_BELLMAN'),
         ('SMOOTH_BELLMAN', 'FROZEN'))
PRIMARY = 'ROUTED_BELLMAN_minus_FROZEN'
BOOTSTRAP_SEED = 29500001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def evaluation_seed(life, phase, game):
    return 295900010000+life*1000000+phase*100000+game


def _bootstrap(rows, values, draws):
    groups = {p:[v for r,v in zip(rows, values) if r['parent']==p] for p in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(g, k=4)) for g in groups.values()) for _ in range(draws))
    def quantile(q):
        index = (draws-1)*q; low = floor(index); high = min(low+1, draws-1)
        return samples[low]+(samples[high]-samples[low])*(index-low)
    return dict(mean=mean(values), ci95=[quantile(.025),quantile(.975)],
        lifecycle_deltas={str(r['lifecycle']):v for r,v in zip(rows, values)},
        improved_equal_worse=[sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)],
        adverse_lifecycles=[r['lifecycle'] for r,v in zip(rows,values) if v<0],
        parent_mean_deltas={str(p):mean(g) for p,g in groups.items()}, interval_scope=INTERVAL_SCOPE)


def _games(games, life, phase):
    if len(games)!=32 or [g['seed'] for g in games]!=[evaluation_seed(life,phase,i) for i in range(32)]:
        raise ValueError('V295 requires all 32 fresh paired complete-game references')
    if any(g['status'] not in ('WON','LOST','CUTOFF') for g in games):
        raise ValueError('Scientific terminal/cutoff outcomes must all remain present')
    return dict(games=32,mean_game_utility=mean(g['utility'] for g in games),
        wins=sum(g['status']=='WON' for g in games),losses=sum(g['status']=='LOST' for g in games),
        cutoffs=sum(g['status']=='CUTOFF' for g in games),steps=sum(g['steps'] for g in games))


def analyze(lifecycles, draws=20000):
    rows = sorted(lifecycles,key=lambda r:r['lifecycle'])
    if len(rows)!=16 or [r['lifecycle'] for r in rows]!=list(range(16)) or any(r['parent']!=r['lifecycle']%4 for r in rows):
        raise ValueError('V295 requires sixteen whole lives under four fixed parents')
    records = []
    for row in rows:
        life = row['lifecycle']; arms = {}; snapshots = row['dataset']['snapshots']
        module_a = snapshots['A']['memory']['active_module_id']; p_a = snapshots['A']['estimated_p_four']
        for arm in ARMS:
            phases = {}
            for phase_index,phase in enumerate(PHASES):
                value = row['arms'][arm]['phases'][phase]; snapshot = value['snapshot']; probe = value['retention_probe']
                module = snapshots[phase]['memory']['active_module_id']; p = snapshots[phase]['estimated_p_four']
                selected = module if arm=='ROUTED_BELLMAN' else None
                if snapshot['estimated_p_four']!=p or snapshot['active_module_id']!=module or snapshot['selected_value_module_id']!=selected:
                    raise ValueError('Current science must use the original observed active module and p')
                if (probe['model_p_four']!=p_a or probe['environment_p_four']!=.1 or probe['depth']!=2
                        or probe['selected_value_module_id']!=(module_a if arm=='ROUTED_BELLMAN' else None)
                        or probe['shared_with_current']!=(phase_index==0)):
                    raise ValueError('Known-A probes must use the saved observed A context')
                if phase_index==0 and probe['game_summaries']!=value['game_summaries']:
                    raise ValueError('A endpoint/probe must share the same physical games')
                scored = value['heldout']['game_metrics']
                if [r['metadata'] for r in scored]!=row['dataset']['phases'][phase]['heldout_games']:
                    raise ValueError('Value-label holdout must retain every original complete game')
                phases[phase] = dict(_games(value['game_summaries'],life,phase_index),
                    heldout={k:mean(r[k] for r in scored) for k in ('mse','mae','bias')},
                    retention_probe=_games(probe['game_summaries'],life,0))
            ahead = row['arms'][arm]['phases']['B']['a_head_on_B']; module_b = snapshots['B']['memory']['active_module_id']
            if (ahead['model_p_four']!=snapshots['B']['estimated_p_four'] or ahead['environment_p_four']!=.5
                    or ahead['selected_value_module_id']!=(module_b if arm=='ROUTED_BELLMAN' else None)
                    or ahead['depth']!=2 or ahead['shared_with_current']!=(arm=='FROZEN')):
                raise ValueError('B no-update counterpart requires the identical observed route and belief')
            if arm=='FROZEN' and ahead['game_summaries']!=row['arms'][arm]['phases']['B']['game_summaries']:
                raise ValueError('Unchanged source B reference must be shared')
            phases['B']['a_head_on_B'] = _games(ahead['game_summaries'],life,1)
            arms[arm] = dict(mean_game_utility=mean(v['mean_game_utility'] for v in phases.values()),
                heldout={k:mean(v['heldout'][k] for v in phases.values()) for k in ('mse','mae','bias')}, phases=phases)
        records.append(dict(lifecycle=life,parent=row['parent'],arms=arms,
            actual_A_prime_module=snapshots['A_prime']['memory']['active_module_id'], saved_A_module=module_a,
            A_prime_same_observed_module=snapshots['A_prime']['memory']['active_module_id']==module_a))
    arms = {}
    for arm in ARMS:
        phases = {p:dict(_aggregate([r['arms'][arm]['phases'][p] for r in records]),
            heldout={k:mean(r['arms'][arm]['phases'][p]['heldout'][k] for r in records) for k in ('mse','mae','bias')},
            retention_probe=_aggregate([r['arms'][arm]['phases'][p]['retention_probe'] for r in records])) for p in PHASES}
        arms[arm] = dict(mean_game_utility=mean(r['arms'][arm]['mean_game_utility'] for r in records),phases=phases,
            heldout={k:mean(r['arms'][arm]['heldout'][k] for r in records) for k in ('mse','mae','bias')},
            **{k:sum(v[k] for v in phases.values()) for k in ('games','wins','losses','cutoffs','steps')})
    paired = {}; phase_contrasts = {p:{} for p in PHASES}; corrections = {}; retention = {}
    for left,right in PAIRS:
        name = left+'_minus_'+right
        paired[name] = _bootstrap(records,[r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records],draws)
        for p in PHASES:
            phase_contrasts[p][name] = _bootstrap(records,[r['arms'][left]['phases'][p]['mean_game_utility']-r['arms'][right]['phases'][p]['mean_game_utility'] for r in records],draws)
    for arm in ARMS:
        corrections[arm] = _bootstrap(records,[r['arms'][arm]['phases']['B']['mean_game_utility']-
            r['arms'][arm]['phases']['B']['a_head_on_B']['mean_game_utility'] for r in records],draws)
        retention[arm] = {}
        for name,p,q in (('after_B','B','A'),('restoration','A_prime','B'),('final_vs_A','A_prime','A')):
            c = _bootstrap(records,[r['arms'][arm]['phases'][p]['retention_probe']['mean_game_utility']-
                r['arms'][arm]['phases'][q]['retention_probe']['mean_game_utility'] for r in records],draws)
            retention[arm][name] = dict(c,direction=_direction(c))
    cutoffs = sum(v['cutoffs'] for v in arms.values())
    cutoffs += sum(r['arms'][a]['phases'][p]['retention_probe']['cutoffs'] for r in records for a in ARMS for p in ('B','A_prime'))
    cutoffs += sum(r['arms'][a]['phases']['B']['a_head_on_B']['cutoffs'] for r in records for a in ARMS[1:])
    complete = cutoffs==0
    return dict(arms=arms,primary_contrast=PRIMARY,paired_contrasts=paired,phase_contrasts=phase_contrasts,
        correction_contrasts=corrections,retention_contrasts=retention,by_lifecycle=records,science_cutoffs=cutoffs,
        net_gain_supported=complete and paired[PRIMARY]['ci95'][0]>0.,
        correction_supported=complete and corrections['ROUTED_BELLMAN']['ci95'][0]>0.,complete_game_endpoints=complete,
        physical_science_games=8704,logical_science_game_references=10752,
        actual_A_prime_same_observed_module=sum(r['A_prime_same_observed_module'] for r in records),
        bootstrap_seed=BOOTSTRAP_SEED,bootstrap_draws=draws,interval_scope=INTERVAL_SCOPE,
        estimator='EQUAL_GAMES_THEN_PHASES_THEN_LIFECYCLES',
        correction_interpretation='A library follows the same B observed expert births but receives no B value updates; '
            'current and counterpart use identical observed B module, p, environment and seeds.',
        retention_interpretation='Known observed A context probes are separate from actual A-prime observed reactivation. '
            'Saved expert storage and a confidence interval crossing zero do not establish behavioral preservation.',
        evidence_scope='Exploratory same-retained-training-history sharing comparison, new independent science seeds; '
            'conditional on four old source parents. No new training acquisition or ranking references.')

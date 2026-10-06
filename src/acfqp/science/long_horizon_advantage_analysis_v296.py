"""Independent returns for old fixed one-action choices at retained anchors."""
from math import floor
import random
from statistics import mean

from .conditional_bellman_analysis_v294 import ranking_seed as discovery_seed

PHASES = ('A', 'B', 'A_prime')
METHODS = ('SOURCE', 'BELLMAN', 'DISCOVERY')
PAIRS = (('DISCOVERY', 'SOURCE'), ('DISCOVERY', 'BELLMAN'), ('BELLMAN', 'SOURCE'))
PRIMARY = 'DISCOVERY_minus_SOURCE'
BOOTSTRAP_SEED = 29600001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def validation_seed(life, phase, anchor, replica):
    return 296600010000+life*1000000+phase*100000+anchor*1000+replica


def _bootstrap(rows, values, draws):
    groups = {parent:[v for row,v in zip(rows,values) if row['parent']==parent] for parent in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group,k=4)) for group in groups.values()) for _ in range(draws))
    def quantile(q):
        index=(draws-1)*q; low=floor(index); high=min(low+1,draws-1)
        return samples[low]+(samples[high]-samples[low])*(index-low)
    return dict(mean=mean(values),ci95=[quantile(.025),quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']):v for row,v in zip(rows,values)},
        improved_equal_worse=[sum(v>0. for v in values),sum(v==0. for v in values),sum(v<0. for v in values)],
        adverse_lifecycles=[row['lifecycle'] for row,v in zip(rows,values) if v<0.],
        parent_mean_deltas={str(p):mean(group) for p,group in groups.items()},interval_scope=INTERVAL_SCOPE)


def _means(reference, actions, life, phase, anchor, seed_function, p):
    if reference['model_p_four']!=p or reference['environment_p_four']!=(.5 if phase==1 else .1):
        raise ValueError('Continuation policy uses recorded observed p; only the environment uses phase law')
    samples=reference['rollouts']
    if sorted({r['action'] for r in samples})!=actions:
        raise ValueError('Receipts must cover exactly the frozen action inventory')
    values={}
    for action in actions:
        selected=[row for row in samples if row['action']==action]
        if len(selected)!=32 or [r['seed'] for r in selected]!=[seed_function(life,phase,anchor,i) for i in range(32)]:
            raise ValueError('Every physical action needs its 32 complete paired replica receipts')
        if any(r['status'] not in ('WON','LOST','CUTOFF') for r in selected):
            raise ValueError('Actual terminal and cutoff continuation outcomes must remain present')
        values[action]=mean(r['total_utility'] for r in selected)
    return values,sum(r['status']=='CUTOFF' for r in samples),len(samples)


def _contrasts(values):
    return {left+'_minus_'+right:values[left]-values[right] for left,right in PAIRS}


def analyze(lifecycles, draws=20000):
    rows=sorted(lifecycles,key=lambda r:r['lifecycle'])
    if (len(rows)!=16 or [r['lifecycle'] for r in rows]!=list(range(16))
            or any(r['parent']!=r['lifecycle']%4 for r in rows)):
        raise ValueError('V296 requires all sixteen paired whole lives under four fixed parents')
    records=[]; old_cutoffs=new_cutoffs=old_rollouts=new_rollouts=0
    action_inventory={1:0,2:0,3:0}; same_actions={name:0 for name in (left+'_minus_'+right for left,right in PAIRS)}
    for row in rows:
        life=row['lifecycle']; phases={}
        for phase_index,phase in enumerate(PHASES):
            anchors=row['phases'][phase]['anchors']
            if len(anchors)!=3 or [a['anchor_id'] for a in anchors]!=[f'L{life:02d}-{phase}-Q{i}' for i in range(3)]:
                raise ValueError('All three original fixed anchors must remain in their original order')
            values=[]
            for anchor_index,anchor in enumerate(anchors):
                legal=sorted(anchor['choices']['FROZEN']['action_values'])
                old,c_old,n_old=_means(anchor['discovery_reference'],legal,life,phase_index,anchor_index,
                                       discovery_seed,anchor['model_p_four'])
                # Tuple order makes ties lexical, including when every action return is negative.
                selected=min(legal,key=lambda a:(-old[a],a))
                actions=dict(SOURCE=anchor['choices']['FROZEN']['action'],
                    BELLMAN=anchor['choices']['BELLMAN_CONDITIONED']['action'],DISCOVERY=selected)
                for key,method in (('source_action','SOURCE'),('bellman_action','BELLMAN'),('discovery_action','DISCOVERY')):
                    if anchor[key]!=actions[method]:
                        raise ValueError('Frozen choices must come only from old discovery receipts and old policy actions')
                candidates=sorted(set(actions.values()))
                if anchor['legal_actions']!=legal or anchor['validation_actions']!=candidates:
                    raise ValueError('New validation must use only the sorted unique frozen candidate union')
                new,c_new,n_new=_means(anchor['validation_reference'],candidates,life,phase_index,anchor_index,
                                       validation_seed,anchor['model_p_four'])
                old_cutoffs+=c_old; new_cutoffs+=c_new; old_rollouts+=n_old; new_rollouts+=n_new
                action_inventory[len(candidates)]+=1
                old_values={method:old[action] for method,action in actions.items()}
                new_values={method:new[action] for method,action in actions.items()}
                old_deltas,new_deltas=_contrasts(old_values),_contrasts(new_values)
                for name,(left,right) in zip(same_actions,PAIRS):
                    same_actions[name]+=actions[left]==actions[right]
                values.append(dict(anchor_id=anchor['anchor_id'],actions=actions,
                    discovery_action_means=old,validation_action_means=new,
                    discovery_values=old_values,validation_values=new_values,
                    discovery_contrasts=old_deltas,validation_contrasts=new_deltas,
                    discovery_validation_drop={name:old_deltas[name]-new_deltas[name] for name in old_deltas}))
            phases[phase]=dict(anchors=values,
                **{field:{key:mean(a[field][key] for a in values) for key in values[0][field]}
                   for field in ('discovery_values','validation_values','discovery_contrasts','validation_contrasts','discovery_validation_drop')})
        records.append(dict(lifecycle=life,parent=row['parent'],phases=phases,
            **{field:{key:mean(v[field][key] for v in phases.values()) for key in phases['A'][field]}
               for field in ('discovery_values','validation_values','discovery_contrasts','validation_contrasts','discovery_validation_drop')}))
    paired={}; discovery={}; drops={}; phase_contrasts={p:{} for p in PHASES}; phase_drops={p:{} for p in PHASES}
    for left,right in PAIRS:
        name=left+'_minus_'+right
        paired[name]=_bootstrap(records,[r['validation_contrasts'][name] for r in records],draws)
        discovery[name]=_bootstrap(records,[r['discovery_contrasts'][name] for r in records],draws)
        c=_bootstrap(records,[r['discovery_validation_drop'][name] for r in records],draws)
        c['positive_zero_negative']=c.pop('improved_equal_worse'); c['negative_lifecycles']=c.pop('adverse_lifecycles')
        drops[name]=c
        for phase in PHASES:
            phase_contrasts[phase][name]=_bootstrap(records,[r['phases'][phase]['validation_contrasts'][name] for r in records],draws)
            c=_bootstrap(records,[r['phases'][phase]['discovery_validation_drop'][name] for r in records],draws)
            c['positive_zero_negative']=c.pop('improved_equal_worse'); c['negative_lifecycles']=c.pop('adverse_lifecycles')
            phase_drops[phase][name]=c
    complete=old_cutoffs+new_cutoffs==0
    return dict(primary_contrast=PRIMARY,paired_contrasts=paired,discovery_contrasts=discovery,
        discovery_validation_drop=drops,phase_contrasts=phase_contrasts,phase_discovery_validation_drop=phase_drops,
        method_values={method:dict(discovery=mean(r['discovery_values'][method] for r in records),
            validation=mean(r['validation_values'][method] for r in records)) for method in METHODS},
        phase_method_values={phase:{method:dict(discovery=mean(r['phases'][phase]['discovery_values'][method] for r in records),
            validation=mean(r['phases'][phase]['validation_values'][method] for r in records)) for method in METHODS} for phase in PHASES},
        complete_continuations=complete,discovery_cutoffs=old_cutoffs,validation_cutoffs=new_cutoffs,
        observed_anchor_signal_supported=complete and paired[PRIMARY]['ci95'][0]>0.,
        anchors=144,discovery_physical_rollouts=old_rollouts,validation_physical_rollouts=new_rollouts,
        validation_logical_candidate_references=144*3*32,paired_replica_seed_streams=144*32,
        validation_unique_action_inventory={str(k):v for k,v in action_inventory.items()},same_action_anchors=same_actions,
        bootstrap_seed=BOOTSTRAP_SEED,bootstrap_draws=draws,interval_scope=INTERVAL_SCOPE,
        estimator='EQUAL_REPLICAS_THEN_ANCHORS_THEN_PHASES_THEN_LIFECYCLES',by_lifecycle=records,
        discovery_interpretation='Old action selection maximizes finite noisy total-return means and fixes the candidates only. '
            'New validation never selects or replaces a candidate.',
        discovery_validation_drop_interpretation='Old discovery advantage minus independent validation advantage at identical fixed candidate actions; this observed difference alone does not establish true selection bias.',
        evidence_scope='Once-forced first action then fixed observed-p SOURCE-H2 continuation at 144 retained natural anchors. '
            'No full-policy net gain, learnability or unsampled-state bias cause is established. Conditional on four old source parents.')

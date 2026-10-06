#!/usr/bin/env python3
"""Independent retained-label V120 interference arithmetic and compact audit."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from math import isclose
from pathlib import Path
from statistics import mean, pvariance

GROUPS = ('uniform','competition')
CATEGORIES = ('SELF','SAME_BOARD_OTHER_ACTION','OTHER_BOARD')
ENDPOINTS = ('mean_label_delta_mse','single_label_mean_delta_mse','empirical_noise_penalty')


def require(condition,message):
    if not condition:
        raise ValueError(message)


def close(a,b):
    return isclose(a,b,rel_tol=1e-10,abs_tol=1e-10)


def feature_addresses(board,radix=11):
    patterns=((0,1,2,4,5,6),(4,5,6,8,9,10),(0,1,2,3,4,5),(4,5,6,7,8,9))
    addresses=[]
    for table,pattern in enumerate(patterns):
        for reflected in (False,True):
            for rotations in range(4):
                index=0
                for cell in pattern:
                    r,c=divmod(cell,4)
                    if reflected:c=3-c
                    for _ in range(rotations):r,c=c,3-r
                    index=index*radix+board[4*r+c]
                addresses.append(table*radix**6+index)
    return addresses


def kernel(left,right):
    a,b=Counter(left),Counter(right)
    return sum(count*b[address] for address,count in a.items())


def expected_metrics(vi,vj,discovery,validation,k):
    require(len(discovery)==len(validation)==32,'two frozen 32-replica batches')
    a,b=mean(discovery),mean(validation)
    va,vb=pvariance(discovery),pvariance(validation)
    beta=.0025*k
    delta=beta*(a-vi)
    baseline=mean((vj-y)**2 for y in validation)
    mean_delta=2*delta*(vj-b)+delta**2
    penalty=beta**2*va
    return dict(vi=vi,vj=vj,k=k,alpha=.0025,beta=beta,
        batch1_count=32,batch2_count=32,batch1_mean=a,batch2_mean=b,
        batch1_popvar=va,batch2_popvar=vb,
        batch1_second_moment=mean(y*y for y in discovery),batch2_second_moment=mean(y*y for y in validation),
        baseline_bias=vj-b,baseline_validation_mse=baseline,mean_label_prediction_delta=delta,
        mean_label_delta_mse=mean_delta,single_label_mean_delta_mse=mean_delta+penalty,
        empirical_noise_penalty=penalty,mean_label_validation_mse=baseline+mean_delta,
        single_label_mean_validation_mse=baseline+mean_delta+penalty)


def category(pair):
    if pair['donor_state_id'] != pair['target_state_id']:return 'OTHER_BOARD'
    return 'SELF' if pair['donor_action'] == pair['target_action'] else 'SAME_BOARD_OTHER_ACTION'


def average(rows):
    return {key:mean(row[key] for row in rows) for key in rows[0]}


def aggregate(pairs,kind):
    selected=[p for p in pairs if category(p)==kind]
    tree=defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    for p in selected:
        values=dict(baseline_validation_mse=p['baseline_validation_mse'],
            **{key:p[key] for key in ENDPOINTS},
            mean_label_validation_mse=p['baseline_validation_mse']+p['mean_label_delta_mse'],
            single_label_mean_validation_mse=p['baseline_validation_mse']+p['single_label_mean_delta_mse'],
            zero_kernel_fraction=float(p['kernel']==0),
            positive_mean_label_delta_fraction=float(p['mean_label_delta_mse']>0))
        tree[p['donor_state_id']][p['donor_action']][p['target_state_id']].append(values)
    metrics=average([average([average([average(actions) for actions in targets.values()])
        for targets in donors.values()]) for donors in tree.values()])
    return dict(metrics=metrics,pairs=len(selected),donor_boards=len(tree),
        recipient_boards=len({p['target_state_id'] for p in selected}),
        zero_kernel_pairs=sum(p['kernel']==0 for p in selected),
        positive_mean_label_pairs=sum(p['mean_label_delta_mse']>0 for p in selected),
        negative_mean_label_pairs=sum(p['mean_label_delta_mse']<0 for p in selected))


def compare_nested(saved,expected,message):
    require(set(saved)==set(expected),message+' fields')
    for key,value in expected.items():
        if isinstance(value,dict):compare_nested(saved[key],value,message+'.'+key)
        elif isinstance(value,float):require(close(saved[key],value),message+'.'+key)
        else:require(saved[key]==value,message+'.'+key)


def check_diagnostic(saved,values):
    require(close(saved['mean'],mean(values)),'signed life mean')
    require(set(saved['lifecycle_deltas'])=={str(i) for i in range(16)}
        and all(close(saved['lifecycle_deltas'][str(i)],v) for i,v in enumerate(values)), 'signed life deltas')
    require(saved['improved_equal_worse']==[sum(v<0 for v in values),sum(v==0 for v in values),sum(v>0 for v in values)]
        and saved['adverse_lifecycles']==[i for i,v in enumerate(values) if v>0], 'adverse harms filtered')
    groups=[values[p::4] for p in range(4)]
    require(saved['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
        and all(close(saved['parent_mean_deltas'][str(p)],mean(g)) for p,g in enumerate(groups)), 'fixed-parent interval inputs')
    low,high=saved['ci95']
    require(mean(min(g) for g in groups)-1e-10<=low<=high<=mean(max(g) for g in groups)+1e-10, 'CI possible range')


def swipe(board,action):
    """Pure standard-2048 afterstate/score; no spawn or random draw."""
    after=list(board);score=0
    for line in range(4):
        cells=([4*line+c for c in range(4)] if action in ('LEFT','RIGHT')
               else [4*r+line for r in range(4)])
        if action in ('RIGHT','DOWN'):cells.reverse()
        ranks=[board[c] for c in cells if board[c]]
        packed=[];i=0
        while i<len(ranks):
            if i+1<len(ranks) and ranks[i]==ranks[i+1]:
                packed.append(ranks[i]+1);score+=2**(ranks[i]+1);i+=2
            else:packed.append(ranks[i]);i+=1
        for cell,value in zip(cells,packed+[0]*(4-len(packed))):after[cell]=value
    return after,score


def json_file(path):
    return json.loads(Path(path).read_text())


def audit(directory):
    d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    require(d['schema']=='acfqp.ntuple_interference.v288'
        and d['status']=='DIAGNOSTIC_COMPLETE' and d['scientific_gate']=='NOT_A_FORMAL_GATE','diagnostic status')
    expected_settings=dict(lifecycles=list(range(16)),parents=4,phase='A',groups=list(GROUPS),
        alpha=.0025,feature_occurrences=32,replicas_per_batch=32,batches=['discovery','validation'],
        bootstrap_draws=20000,bootstrap_seed=28800001,
        primary=dict(group='uniform',category='OTHER_BOARD',metric='mean_label_delta_mse'),
        fit='ISOLATED_ANALYTIC_UPDATES_WITHOUT_WEIGHT_MUTATION',
        continuation='RETAINED_FIXED_TRUE_P_ORACLE_H2')
    for key,value in expected_settings.items():require(settings[key]==value,'frozen '+key)
    original=json_file(settings['source_summary'])
    require(json_file(Path(settings['source_summary']).with_name('audit.json'))['independent_valid'],
        'retained V285 has no completed independent audit')
    require(d['source_provenance']==original['source_provenance'],'source provenance changed')
    states={state['state_id']:state for parent in original['parent_receipts']
        for state in parent['states'] if state['phase']=='A'}
    require(len(states)==128,'all selected A roots not retained')
    original_parents={p['parent']:p for p in original['parent_receipts']}
    retained={};consumed=Counter();parent_consumed={}
    for parent_id,parent in original_parents.items():
        counts=Counter()
        with gzip.open(parent['trace_file'],'rt') as stream:
            for line in stream:
                row=json.loads(line);counts['retained_records_read']+=1
                if row['state_id'] not in states:continue
                key=(row['state_id'],row['action'],row['batch'],row['replica_index'])
                require(key not in retained,'duplicate retained labels')
                retained[key]=row['suffix_utility']
                counts.update(retained_A_rollouts=1,retained_A_environment_transitions=row['steps'],
                    retained_A_post_action_spawns=row['steps'],retained_A_random_draws=2*row['steps'])
        parent_consumed[parent_id]=dict(counts);consumed.update(counts)
    expected_queries={};processing=Counter()
    for state_id,state in states.items():
        require(state['parent']==state['lifecycle']%4,'root parent/lifecycle assignment')
        for action in state['legal_actions']:
            after,score=swipe(state['board'],action)
            require(after!=state['board'] and score==state['immediate_scores'][action],'retained legal swipe/first reward')
            processing['deterministic_swipe_reconstructions']+=1
            for batch in ('discovery','validation'):
                require(all((state_id,action,batch,i) in retained for i in range(32)),'missing retained batch')
            if max(after)>=11:
                processing['analytic_winning_queries_excluded']+=1
            else:expected_queries[state_id,action]=(after,score)
    require(len(retained)==64*sum(len(s['legal_actions']) for s in states.values()),'retained label inventory')
    queries={};by_group=defaultdict(list);parent_query_counts=Counter()
    trace=Path(d['query_trace'])
    with gzip.open(trace,'rt') as stream:
        for line in stream:
            q=json.loads(line);key=(q['state_id'],q['action'])
            require(key in expected_queries and key not in queries,'query selection/duplication')
            state=states[q['state_id']];after,score=expected_queries[key]
            require(q['board']==state['board'] and q['afterstate']==after and q['first_score']==score,
                'deterministic query afterstate/reward changed')
            require(all(q[field]==state[field] for field in ('lifecycle','parent','group')),'query cohort assignment')
            require(q['features']==feature_addresses(after) and len(q['features'])==32,'V120 feature addresses/multiplicities')
            require(close(q['prediction'],q['raw_prediction']+q['failure_shift']+q['success_shift']),
                'query prediction conversion')
            require(q['failure_shift']==q['success_shift']==0.,'risk_goal source-query identity')
            for batch in ('discovery','validation'):
                require(q[batch]==[retained[q['state_id'],q['action'],batch,i] for i in range(32)],
                    'query independent retained batch ordering')
            queries[key]=q;by_group[q['lifecycle'],q['group']].append(q)
            parent_query_counts[q['parent']]+=1
            processing.update(direct_leaf_predictions=1,feature_occurrences_encoded=32)
    require(set(queries)==set(expected_queries),'nonwinning legal actions omitted')
    require([l['lifecycle'] for l in d['by_lifecycle']]==list(range(16)),'complete ordered lifecycle inventory')
    life_analysis=[]
    for life in d['by_lifecycle']:
        lifecycle=life['lifecycle'];require(life['parent']==lifecycle%4,'analysis parent assignment')
        result=dict(lifecycle=lifecycle,parent=lifecycle%4,groups={})
        for group in GROUPS:
            query_rows=by_group[lifecycle,group];saved=life['groups'][group]
            require(len({q['state_id'] for q in query_rows})==4 and saved['query_count']==len(query_rows),
                'four equal-weight boards/group')
            identities={(a['state_id'],a['action'],b['state_id'],b['action']) for a in query_rows for b in query_rows}
            seen=set()
            for pair in saved['pairs']:
                identity=tuple(pair[k] for k in ('donor_state_id','donor_action','target_state_id','target_action'))
                require(identity in identities and identity not in seen,'directed pair omitted or duplicated')
                seen.add(identity)
                donor,target=queries[identity[:2]],queries[identity[2:]]
                k=kernel(donor['features'],target['features'])
                require(pair['kernel']==pair['k']==k,'feature overlap multiplicity')
                expected=expected_metrics(donor['prediction'],target['prediction'],donor['discovery'],target['validation'],k)
                compare_nested({key:pair[key] for key in expected},expected,'isolated update arithmetic')
            require(seen==identities,'all directed pairs including protected zeros')
            processing.update(kernel_matrices=1,feature_pair_inner_products=len(identities),
                isolated_update_pair_diagnostics=len(identities))
            result['groups'][group]=dict(categories={kind:aggregate(saved['pairs'],kind) for kind in CATEGORIES})
        life_analysis.append(result)
    analysis=d['summary']
    require(analysis['primary_endpoint']==settings['primary'] and analysis['bootstrap_draws']==20000
        and analysis['bootstrap_seed']==28800001
        and analysis['estimator']=='RECIPIENT_ACTION_BOARD_THEN_DONOR_ACTION_BOARD_THEN_LIFECYCLE',
        'primary/bootstrap/weighting declaration')
    require(len(analysis['by_lifecycle'])==16,'lifecycle analysis inventory')
    for saved,expected in zip(analysis['by_lifecycle'],life_analysis):compare_nested(saved,expected,'life weighting')
    results={}
    for group in GROUPS:
        results[group]={}
        for kind in CATEGORIES:
            records=[life['groups'][group]['categories'][kind] for life in life_analysis]
            saved=analysis['groups'][group]['categories'][kind]
            compare_nested(saved['metrics'],average([record['metrics'] for record in records]),'global life weighting')
            for name in ('pairs','zero_kernel_pairs','positive_mean_label_pairs','negative_mean_label_pairs'):
                require(saved[name]==sum(record[name] for record in records),'global '+name)
            for endpoint in ENDPOINTS:
                check_diagnostic(saved['paired_diagnostics'][endpoint],[record['metrics'][endpoint] for record in records])
            results[group][kind]={key:saved['paired_diagnostics'][key] for key in ENDPOINTS}
    receipts=d['parent_receipts']
    require([p['parent'] for p in receipts]==list(range(4)),'one physical source load per parent')
    parameter_count=4*11**6
    for receipt in receipts:
        parent=receipt['parent'];source=d['source_provenance']['parents'][parent]
        require(receipt['retained_counts']==parent_consumed[parent],'parent reused observation costs')
        require(receipt['new_value_updates']==0 and receipt['source_query']==receipt['target_query']==source['source_query'],
            'source conversion/actual updates')
        require(receipt['model_prediction_counts']==dict(value_predictions=parent_query_counts[parent],
            table_lookups=32*parent_query_counts[parent]),'prediction/lookup work')
        setup=receipt['source_setup'];counts=setup['setup_counts']
        require(setup['checkpoint_loads']==1 and setup['new_leaf_updates']==0
            and setup['inherited_updates']==source['updates'],'source loading/update scope')
        require(setup['leaf_weight_bytes']==8*parameter_count
            and setup['resident_source_and_leaf_weight_bytes']==16*parameter_count
            and counts['source_parameters_copied']==parameter_count
            and counts['source_weight_bytes_copied']==8*parameter_count,'source allocation/copy costs')
    account=d['accounting'];inherited=account['inherited_costs']
    require(account['new_environment_observations']==account['new_actual_value_updates']==0,'new environment/value update')
    require(account['processing_counts']==dict(processing),'deterministic processing ledger')
    env=dict(sum((Counter(p['inherited_training_costs']['environment_counts'])
        for p in original['source_provenance']['parents']),Counter()))
    require(inherited['source_value_environment_counts']==env
        and inherited['source_value_training_raw_tiles']==env['sampled_transitions']+env['initial_spawns'],
        'historical source counts including initial spawns')
    require(close(inherited['source_value_training_seconds'],sum(p['inherited_training_costs']['training_seconds']
        for p in original['source_provenance']['parents'])),'historical source CPU')
    require(inherited['inherited_dynamics_costs']==original['source_provenance']['inherited_dynamics_costs']
        and inherited['inherited_v281_acquisition_costs']==original['accounting']['inherited_v281_costs']
        and inherited['inherited_v285_full_diagnostic_costs']==original['accounting']
        and inherited['inherited_v285_selected_A_rollout_counts']==dict(consumed),'inherited scopes omitted/changed')
    require('alternative scopes' in inherited['scope'] and 'must not be added' in inherited['scope'],
        'subset acquisition double-counting scope')
    require(account['query_trace_bytes']==trace.stat().st_size,'retained trace storage')
    require(all(account[k]>=0 for k in ('coordinator_cpu_seconds','compiler_cpu_seconds','wall_seconds')),
        'actual diagnostic compute costs')
    primary=analysis['groups']['uniform']['categories']['OTHER_BOARD']['paired_diagnostics']
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,
        root_boards=len(states),query_afterstates=len(queries),directed_pairs=processing['feature_pair_inner_products'],
        new_environment_observations=0,new_actual_value_updates=0,
        retained_A_rollouts=consumed['retained_A_rollouts'],
        retained_A_environment_transitions=consumed['retained_A_environment_transitions'],
        primary={endpoint:{key:primary[endpoint][key] for key in ('mean','ci95','improved_equal_worse','adverse_lifecycles')}
            for endpoint in ENDPOINTS},
        groups={group:{kind:{endpoint:{key:values[endpoint][key]
            for key in ('mean','ci95','improved_equal_worse','adverse_lifecycles')}
            for endpoint in ENDPOINTS} for kind,values in categories.items()}
            for group,categories in results.items()},
        actual_diagnostic_costs={key:account[key] for key in ('processing_counts','coordinator_cpu_seconds',
            'compiler_cpu_seconds','wall_seconds','query_trace_bytes')},
        method='Literal standard swipe/features; retained batches; multiplicity kernels; all isolated-update moments; '
            'board/action/life weights; signed diagnostics; historical and actual cost ledgers.',
        limitations='Frozen checkpoint predictions not reexecuted. Existing 20000-draw bootstrap not regenerated; '
            'signed inputs, fixed-parent grouping and interval bounds checked. No new environment, old world/terminal '
            'replay or actual weight updates. One isolated update on this cohort does not identify accumulated '
            'learning or policy-shift effects in V287.',errors=[])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))
    raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()

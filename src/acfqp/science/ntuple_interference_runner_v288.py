"""Retained-label diagnosis of isolated n-tuple updates; no new rollouts."""
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

import numpy as np

from acfqp.domains import standard_2048 as ground
from .natural_model_revision_v281 import load_leaf
from .ntuple_interference_v288 import feature_kernel, pair_metrics

ALPHA = .0025
GROUPS = ('uniform', 'competition')


def configuration(source_summary):
    return dict(schema='acfqp.ntuple_interference_freeze.v288',
        source_summary=str(Path(source_summary).resolve()),
        protocol=str(Path(__file__).resolve().parents[3]/'specs/NTUPLE_INTERFERENCE_V288.md'),
        lifecycles=list(range(16)), parents=4, phase='A', groups=GROUPS,
        alpha=ALPHA, feature_occurrences=32, replicas_per_batch=32,
        batches=['discovery','validation'], bootstrap_draws=20000, bootstrap_seed=28800001,
        primary=dict(group='uniform',category='OTHER_BOARD',metric='mean_label_delta_mse'),
        fit='ISOLATED_ANALYTIC_UPDATES_WITHOUT_WEIGHT_MUTATION',
        continuation='RETAINED_FIXED_TRUE_P_ORACLE_H2',
        finite_test_passes=dict(kernel=5,analysis=5,driver=3))


def read_labels(parent):
    """Reuse the audited suffix utility, retaining all A acquisition costs."""
    states = {s['state_id']: s for s in parent['states'] if s['phase']=='A'}
    labels = defaultdict(lambda: {'discovery':{},'validation':{}})
    counts = Counter()
    with gzip.open(parent['trace_file'],'rt') as stream:
        for line in stream:
            row = json.loads(line)
            counts['retained_records_read'] += 1
            if row['state_id'] not in states:
                continue
            state = states[row['state_id']]
            action, batch, replica = row['action'],row['batch'],row['replica_index']
            score = state['immediate_scores'][action]
            terminal_bonus = 4. if row['status']=='WON' else -4.
            if (row['first_score']!=score or row['status'] not in ('WON','LOST')
                    or row['suffix_utility']!=(row['total_score']-score)/2048.+terminal_bonus):
                raise ValueError('Retained suffix includes the current action or lacks a terminal return')
            target = labels[state['state_id'],action][batch]
            if replica in target:
                raise ValueError('Retained action/batch replica duplicated')
            target[replica] = row['suffix_utility']
            counts.update(retained_A_rollouts=1,retained_A_environment_transitions=row['steps'],
                retained_A_post_action_spawns=row['steps'],
                retained_A_random_draws=2*row['steps'])
    for state in states.values():
        for action in state['legal_actions']:
            for batch in ('discovery','validation'):
                values=labels[state['state_id'],action][batch]
                if set(values)!=set(range(32)):
                    raise ValueError('V288 requires both complete independent batches per legal action')
    return dict(states=states, labels={key:{batch:[values[i] for i in range(32)]
        for batch,values in batches.items()} for key,batches in labels.items()}, counts=dict(counts))


def build_queries(leaf, state, labels, counts):
    rows=[]
    for action in state['legal_actions']:
        after,score,changed=ground.swipe_board_v1(tuple(state['board']),ground.Swipe2048Action(action))
        counts.update(deterministic_swipe_reconstructions=1)
        if not changed or score!=state['immediate_scores'][action]:
            raise ValueError('Retained legal action or first score differs from standard ground swipe')
        if max(after)>=leaf.radix:
            counts['analytic_winning_queries_excluded']+=1
            continue
        raw=leaf.model.value(after)
        prediction=raw+leaf.failure_shift+leaf.success_shift
        indices=leaf.model.feature_indices(after)
        counts.update(direct_leaf_predictions=1,feature_occurrences_encoded=32)
        rows.append(dict(state_id=state['state_id'],action=action,
            lifecycle=state['lifecycle'],parent=state['parent'],group=state['group'],
            board=state['board'],afterstate=list(after),first_score=score,
            prediction=prediction,raw_prediction=raw,
            failure_shift=leaf.failure_shift,success_shift=leaf.success_shift,
            features=indices.tolist(),**labels[state['state_id'],action]))
    return rows


def build_pairs(queries, counts):
    kernel=feature_kernel(np.asarray([q['features'] for q in queries],dtype=np.int64))
    counts['kernel_matrices']+=1
    counts['feature_pair_inner_products']+=kernel.size
    rows=[]
    for i,donor in enumerate(queries):
        for j,target in enumerate(queries):
            metrics=pair_metrics(donor['prediction'],target['prediction'],
                donor['discovery'],target['validation'],int(kernel[i,j]),ALPHA)
            counts['isolated_update_pair_diagnostics']+=1
            rows.append(dict(donor_state_id=donor['state_id'],donor_action=donor['action'],
                target_state_id=target['state_id'],target_action=target['action'],
                kernel=int(kernel[i,j]),**metrics))
    return rows


def inherited_costs(original, consumed):
    source=original['source_provenance']
    env=dict(sum((Counter(p['inherited_training_costs']['environment_counts'])
        for p in source['parents']),Counter()))
    dynamics=source['inherited_dynamics_costs']
    carriers=original['accounting']['inherited_v281_costs']
    return dict(source_value_training_raw_tiles=env['sampled_transitions']+env['initial_spawns'],
        source_value_environment_counts=env,
        source_value_training_seconds=sum(p['inherited_training_costs']['training_seconds']
            for p in source['parents']), inherited_dynamics_costs=dynamics,
        inherited_v281_acquisition_costs=carriers,
        inherited_v285_selected_A_rollout_counts=consumed,
        inherited_v285_full_diagnostic_costs=original['accounting'],
        scope='Historical source/dynamics/carrier acquisition is retained once. Selected A suffix '
            'observations are a reused subset of the original V285 diagnostic; subset and full totals '
            'are alternative scopes and must not be added together. Both label treatments use the '
            'same already-paid 32 discovery and 32 validation replicas.')


def run(source_summary, output):
    from .interference_analysis_v288 import summarize
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V288 frozen configuration or results already exist')
    original=json.loads(Path(source_summary).read_text())
    audit=json.loads(Path(source_summary).with_name('audit.json').read_text())
    if not audit['independent_valid']:
        raise ValueError('V285 suffix data requires its existing independent PASS audit')
    settings=configuration(source_summary)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu_started=perf_counter(),process_time()
    children_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    lives={life:dict(lifecycle=life,parent=life%4,groups={}) for life in range(16)}
    receipts=[]
    processing=Counter(); consumed=Counter()
    query_trace=output/'queries.jsonl.gz'
    with gzip.open(query_trace,'xt',encoding='utf-8') as stream:
        for parent in original['parent_receipts']:
            loaded=read_labels(parent)
            consumed.update(loaded['counts'])
            source=original['source_provenance']['parents'][parent['parent']]
            leaf,setup=load_leaf(source,output/'runtime'/f"parent_{parent['parent']}")
            counts_before=leaf.model.counts.copy()
            states=list(loaded['states'].values())
            for life in range(parent['parent'],16,4):
                for group in GROUPS:
                    selected=[state for state in states if state['lifecycle']==life and state['group']==group]
                    if len(selected)!=4:
                        raise ValueError('V288 retains four preselected roots per group/lifecycle')
                    queries=[]
                    for state in selected:
                        queries.extend(build_queries(leaf,state,loaded['labels'],processing))
                    for row in queries:
                        stream.write(json.dumps(row,separators=(',', ':'),allow_nan=False)+'\n')
                    lives[life]['groups'][group]=dict(query_count=len(queries),
                        pairs=build_pairs(queries,processing))
            receipts.append(dict(parent=parent['parent'],source_setup=setup,
                source_query=leaf.source_query,target_query=leaf.target_query,
                new_value_updates=leaf.updates,model_prediction_counts={key:value-counts_before.get(key,0)
                    for key,value in leaf.model.counts.items() if value!=counts_before.get(key,0)},
                retained_counts=loaded['counts']))
            if leaf.updates!=0:
                raise ValueError('An analytic diagnostic must not mutate the frozen source learner')
            del leaf
            print(json.dumps(dict(event='interference_parent_complete',parent=parent['parent'],
                retained_A_rollouts=loaded['counts']['retained_A_rollouts'])),flush=True)
    rows=[lives[life] for life in range(16)]
    analysis=summarize(rows)
    children_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    result=dict(schema='acfqp.ntuple_interference.v288',status='DIAGNOSTIC_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE',settings=settings,source_provenance=original['source_provenance'],
        parent_receipts=receipts,by_lifecycle=rows,summary=analysis,
        query_trace=str(query_trace.resolve()),
        accounting=dict(new_environment_observations=0,new_actual_value_updates=0,
            processing_counts=dict(processing), inherited_costs=inherited_costs(original,dict(consumed)),
            coordinator_cpu_seconds=process_time()-cpu_started,
            compiler_cpu_seconds=children_after.ru_utime+children_after.ru_stime
                -children_before.ru_utime-children_before.ru_stime,
            wall_seconds=perf_counter()-started,query_trace_bytes=query_trace.stat().st_size))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='interference_complete',status=result['status'],
        primary=analysis['primary_endpoint'],new_environment_observations=0)),flush=True)
    return result

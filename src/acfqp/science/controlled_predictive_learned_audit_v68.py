"""Frozen source dynamics audited on unseen concrete finite 2048 closures."""
from __future__ import annotations

from collections import Counter,defaultdict
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
import math
from time import perf_counter

from .controlled_predictive_causal_audit_v66 import compute_reference

TOLERANCE=1e-12


@dataclass(frozen=True)
class SourceSupport:
    registry: dict
    signatures: frozenset
    state_signatures: dict
    counts: dict
    elapsed_seconds: float


def _semantic_ids(model,registry,work):
    """Canonical standard-2048 kernels, independent of source cell identifiers."""
    actions=defaultdict(list)
    for state,action in model.rows:actions[state].append(action)
    signatures={}
    for state in sorted(model.layers,key=lambda s:(model.layers[s],s)):
        work['semantic_states']+=1
        rows=[]
        for action in sorted(actions[state]):
            mass=defaultdict(Fraction)
            for outcome in model.rows[state,action]:
                work['semantic_outcome_terms']+=1
                # Standard 2048 uses 9/10 or 1/10 divided by at most 16 vacancies.
                probability=Fraction(outcome.probability).limit_denominator(160)
                if probability:
                    mass[signatures[outcome.next_state],Fraction(outcome.reward)]+=probability
            rows.append((action,tuple((target,reward,p) for (target,reward),p in sorted(mass.items()))))
        signature=(model.layers[state],model.terminal[state],tuple(rows))
        if signature not in registry:registry[signature]=len(registry)
        signatures[state]=registry[signature]
    return signatures


def recursive_support(model):
    """Audit-only source semantic inventory; it is never updated by target data."""
    started,work,registry=perf_counter(),Counter(),{}
    ids=_semantic_ids(model,registry,work)
    return SourceSupport(registry,frozenset(ids.values()),ids,dict(work),perf_counter()-started)


def support_coverage(model,source_support):
    work,registry=Counter(),dict(source_support.registry)
    signatures=_semantic_ids(model,registry,work)
    layers=defaultdict(Counter)
    for state,signature in signatures.items():
        if model.terminal[state]=='ACTIVE':
            layer=layers[model.layers[state]]
            layer['active_states']+=1
            layer['source_supported_states']+=int(signature in source_support.signatures)
    return dict(active_states=sum(c['active_states'] for c in layers.values()),
        source_supported_states=sum(c['source_supported_states'] for c in layers.values()),
        by_horizon={str(h):dict(counts) for h,counts in sorted(layers.items())},
        roots=[dict(root=root,source_supported=signatures[root] in source_support.signatures) for root in model.roots],
        counts=dict(work),scope='Exact recursive reward/terminal/transition support under standard-2048 rational probabilities. This bounds exact model expressibility, not policy accuracy; target signatures are audit-only.')


def _policy_metrics(model,policy,query,work):
    metrics={}
    for state in sorted(model.layers,key=lambda s:(model.layers[s],s)):
        work['policy_evaluation_states']+=1
        status=model.terminal[state]
        if status!='ACTIVE':
            row=dict(reward=0.,natural_failure=float(status=='LOST'),unsupported=0.,success=float(status=='WON'))
        elif (state,policy.get(state)) not in model.rows:
            # Protocol stop, not a fabricated legal game transition or a fallback.
            row=dict(reward=0.,natural_failure=0.,unsupported=1.,success=0.)
            work['unsupported_policy_states']+=1
        else:
            outcomes=model.rows[state,policy[state]]
            work['policy_evaluation_action_rows']+=1;work['policy_evaluation_outcome_terms']+=len(outcomes)
            row={name:math.fsum(o.probability*((o.reward if name=='reward' else 0.)+metrics[o.next_state][name])
                for o in outcomes if o.probability) for name in ('reward','natural_failure','unsupported','success')}
        row['failure']=row['natural_failure']+row['unsupported']
        row['value']=query.reward_weight*row['reward']-query.failure_penalty*row['failure']+query.goal_bonus*row['success']
        metrics[state]=row
    return metrics


def audit_frozen(closure,queries,compiled,solutions,encoded,reference,source_support,*,encoding_counts=None,encoding_seconds=0.,target_support=None):
    """Use one frozen batch encoding; no target row is added to source dynamics."""
    started,work=perf_counter(),Counter()
    model=closure.model
    active=[s for s in model.layers if model.terminal[s]=='ACTIVE']
    mapping,route_errors={},Counter()
    terminals={(cell.layer,cell.terminal):code for code,cell in compiled.cells.items() if cell.terminal!='ACTIVE'}
    for state in model.layers:
        if model.terminal[state]!='ACTIVE':
            mapping[state]=terminals.get((model.layers[state],model.terminal[state]));continue
        code=encoded.get(state)
        cell=compiled.cells.get(code)
        if cell is None or cell.terminal!='ACTIVE' or cell.layer!=model.layers[state]:
            mapping[state]=None;route_errors['missing_or_wrong_layer_source_code']+=1
        else:mapping[state]=code
    source_actions=defaultdict(set)
    for code,action in compiled.rows:source_actions[code].add(action)
    model_errors,maximum_tv,compared_rows=Counter(),0.,0
    for state in active:
        code=mapping[state]
        if code is not None and set(reference.actions[state])!=source_actions[code]:model_errors['legal_action_set_difference']+=1
    for (state,action),row in model.rows.items():
        work['target_model_row_checks']+=1;work['target_model_outcome_terms']+=len(row)
        code=mapping[state]
        if code is None or (code,action) not in compiled.rows:
            model_errors['missing_source_action_row']+=1;continue
        if any(mapping[o.next_state] is None for o in row if o.probability):
            model_errors['unmapped_successor_code']+=1;continue
        ground,source=defaultdict(list),defaultdict(list)
        for o in row:
            if o.probability:ground[mapping[o.next_state],o.reward].append(o.probability)
        for o in compiled.rows[code,action]:
            if o.probability:source[o.next_state,o.reward].append(o.probability)
        work['source_model_outcome_terms']+=len(compiled.rows[code,action])
        p={k:math.fsum(v) for k,v in ground.items()};q={k:math.fsum(v) for k,v in source.items()}
        tv=.5*math.fsum(abs(p.get(k,0.)-q.get(k,0.)) for k in p.keys()|q.keys())
        maximum_tv=max(maximum_tv,tv);compared_rows+=1
        if tv>TOLERANCE:model_errors['joint_distribution_difference']+=1
    results,policies={},{}
    for name,query in queries.items():
        solution=solutions[name]
        policy={state:solution.policy.get(mapping[state]) for state in active};policies[name]=policy
        metrics=_policy_metrics(model,policy,query,work)
        by_horizon=defaultdict(lambda:dict(states=0,action_errors=0,illegal_or_missing_actions=0,value_loss_sum=0.,maximum_value_loss=0.,unsupported_probability_sum=0.))
        maximum_prediction_error,missing_predictions=0.,0
        for state in active:
            h=by_horizon[str(model.layers[state])];h['states']+=1
            loss=reference.queries[name]['values'][state]-metrics[state]['value']
            qvalues=reference.queries[name]['qvalues'][state]
            legal=policy[state] in qvalues
            h['illegal_or_missing_actions']+=int(not legal)
            h['action_errors']+=int(not legal or qvalues[policy[state]]<reference.queries[name]['values'][state]-TOLERANCE)
            h['value_loss_sum']+=loss;h['maximum_value_loss']=max(h['maximum_value_loss'],loss)
            h['unsupported_probability_sum']+=metrics[state]['unsupported']
            predicted=solution.values.get(mapping[state])
            if predicted is None:missing_predictions+=1
            else:maximum_prediction_error=max(maximum_prediction_error,abs(predicted-metrics[state]['value']))
        roots=[]
        for index,state in enumerate(model.roots):
            predicted=solution.values.get(mapping[state])
            optimal=reference.queries[name]['values'][state]
            roots.append(dict(name=closure.root_names[index],root=state,source_code=mapping[state],selected=policy.get(state),
                actual=metrics[state],predicted_value=predicted,prediction_error=None if predicted is None else predicted-metrics[state]['value'],
                ground_optimal_value=optimal,value_loss=optimal-metrics[state]['value']))
        for stats in by_horizon.values():
            stats['mean_value_loss']=stats['value_loss_sum']/stats['states']
            stats['mean_unsupported_probability']=stats['unsupported_probability_sum']/stats['states']
        results[name]=dict(root_metrics=roots,by_horizon=dict(by_horizon),
            maximum_value_loss=max((v['maximum_value_loss'] for v in by_horizon.values()),default=0.),
            action_errors=sum(v['action_errors'] for v in by_horizon.values()),
            illegal_or_missing_actions=sum(v['illegal_or_missing_actions'] for v in by_horizon.values()),
            maximum_value_prediction_error=maximum_prediction_error,missing_value_predictions=missing_predictions)
    required,violations=0,0
    for left,right in combinations(queries,2):
        a,b=reference.queries[left],reference.queries[right]
        for state in active:
            if a['policy'][state]!=b['policy'][state] and min(a['margins'][state],b['margins'][state])>TOLERANCE:
                required+=1;violations+=int(policies[left][state]!=a['policy'][state] or policies[right][state]!=b['policy'][state])
    support=support_coverage(model,source_support) if target_support is None else target_support
    if target_support is None:work.update({'support_'+name:value for name,value in support['counts'].items()})
    return dict(valid_evidence=True,ground_states=len(model.layers),active_states=len(active),
        encoder_coverage=dict(covered_active_states=sum(mapping[s] is not None for s in active),errors=dict(route_errors)),
        exact_controlled_equivalence=not route_errors and not model_errors,
        controlled_model_errors=dict(model_errors),joint_rows_compared=compared_rows,maximum_joint_total_variation=maximum_tv,
        queries=results,strict_query_switches=dict(required=required,violations=violations,preserved=violations==0),
        source_support=support,encoding_counts=dict(encoding_counts or {}),encoding_seconds=encoding_seconds,
        counts=dict(work),elapsed_seconds=perf_counter()-started,
        scope='The encoder and source kernel are frozen. Each target state is encoded once; all query policies use source cells. Unsupported/illegal actions stop operationally, with separate unsupported reach probability and natural LOST probability. No target transition, label, or query outcome updates either learned artifact.')

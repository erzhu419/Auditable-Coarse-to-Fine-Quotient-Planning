"""Independent finite-model pushforward and lifted-policy audit for V67."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
import math
from time import perf_counter

from .controlled_predictive_action_contract_v67 import encode_key

TOLERANCE=1e-12
METRICS=('reward','failure','success','value')


@dataclass(frozen=True)
class Reference:
    queries: dict
    actions: dict
    counts: dict
    elapsed_seconds: float


def _actions(model):
    actions=defaultdict(list)
    for state,action in model.rows: actions[state].append(action)
    return {state:tuple(sorted(names)) for state,names in actions.items()}


def _terminal(status,query):
    return query.goal_bonus if status=='WON' else -query.failure_penalty if status=='LOST' else 0.


def _metrics(model,policy,query,work,prefix):
    result={}
    for state in sorted(model.layers,key=lambda s:(model.layers[s],s)):
        work[prefix+'_states']+=1
        status=model.terminal[state]
        if status!='ACTIVE':
            metrics=dict(reward=0.,failure=float(status=='LOST'),success=float(status=='WON'))
        else:
            action=policy.get(state)
            row=model.rows.get((state,action))
            if row is None:
                result[state]=None;work[prefix+'_missing_actions']+=1;continue
            work[prefix+'_action_rows']+=1
            work[prefix+'_outcome_terms']+=len(row)
            if any(result.get(o.next_state) is None for o in row if o.probability):
                result[state]=None;continue
            metrics={name:math.fsum(o.probability*((o.reward if name=='reward' else 0.)+result[o.next_state][name])
                for o in row if o.probability) for name in ('reward','failure','success')}
        metrics['value']=query.reward_weight*metrics['reward']-query.failure_penalty*metrics['failure']+query.goal_bonus*metrics['success']
        result[state]=metrics
    return result


def compute_reference(closure,queries):
    """Once per concrete closure: independently optimize all queries and states."""
    started,work=perf_counter(),Counter()
    model,actions=closure.model,_actions(closure.model)
    reference={}
    for name,query in queries.items():
        values,policy,qvalues,margins={},{},{},{}
        for state in sorted(model.layers,key=lambda s:(model.layers[s],s)):
            work['reference_dp_states']+=1
            if model.terminal[state]!='ACTIVE':
                values[state]=_terminal(model.terminal[state],query);continue
            candidates={}
            for action in actions[state]:
                row=model.rows[state,action];work['reference_dp_action_rows']+=1
                work['reference_dp_outcome_terms']+=len(row)
                candidates[action]=math.fsum(o.probability*(query.reward_weight*o.reward+values[o.next_state]) for o in row)
            selected=max(candidates,key=candidates.get)
            values[state],policy[state],qvalues[state]=candidates[selected],selected,candidates
            alternatives=[v for a,v in candidates.items() if a!=selected]
            margins[state]=candidates[selected]-max(alternatives) if alternatives else math.inf
        metrics=_metrics(model,policy,query,work,'reference_policy')
        reference[name]=dict(values=values,policy=policy,qvalues=qvalues,margins=margins,metrics=metrics)
    return Reference(reference,actions,dict(work),perf_counter()-started)


def audit_build(build,closure,queries,solutions,reference,compiled):
    """Check every concrete row without generating or fitting another model."""
    started,work,errors=perf_counter(),Counter(),Counter()
    model,candidate=closure.model,build.model
    mapping,first,worst,worst_tv={},None,None,0.
    legal=_actions(candidate)
    for state in model.layers:
        work['encoded_concrete_states']+=1;work['encoded_board_tiles']+=len(closure.boards[state])
        encoded=encode_key(closure.boards[state],model.layers[state],build.rule)
        target=build.state_index.get(encoded)
        if target not in candidate.layers:
            errors['missing_encoded_state']+=1
            if first is None: first=dict(reason='missing_encoded_state',state=state,horizon=model.layers[state],board=list(closure.boards[state]))
            continue
        mapping[state]=target
        if model.layers[state]!=candidate.layers[target] or model.terminal[state]!=candidate.terminal[target]:
            errors['layer_or_terminal_mismatch']+=1
            if first is None: first=dict(reason='layer_or_terminal_mismatch',state=state,ground=model.terminal[state],encoded=candidate.terminal[target])
        if reference.actions.get(state,())!=legal.get(target,()):
            errors['legal_action_mismatch']+=1
            if first is None: first=dict(reason='legal_action_mismatch',state=state,ground=reference.actions.get(state,()),encoded=legal.get(target,()))
    for (state,action),row in model.rows.items():
        work['joint_distribution_rows']+=1;work['ground_pushforward_outcome_terms']+=len(row)
        target=mapping.get(state)
        if target is None or (target,action) not in candidate.rows: continue
        missing=[o.next_state for o in row if o.probability and o.next_state not in mapping]
        if missing:
            errors['missing_pushforward_target']+=1
            if first is None: first=dict(reason='missing_pushforward_target',state=state,action=action,target=missing[0])
            continue
        ground,abstract=defaultdict(list),defaultdict(list)
        for outcome in row:
            if outcome.probability: ground[mapping[outcome.next_state],outcome.reward].append(outcome.probability)
        candidate_row=candidate.rows[target,action]
        work['candidate_pushforward_outcome_terms']+=len(candidate_row)
        for outcome in candidate_row:
            if outcome.probability: abstract[outcome.next_state,outcome.reward].append(outcome.probability)
        p={key:math.fsum(parts) for key,parts in ground.items()};q={key:math.fsum(parts) for key,parts in abstract.items()}
        tv=.5*math.fsum(abs(p.get(key,0.)-q.get(key,0.)) for key in p.keys()|q.keys())
        if tv>TOLERANCE: errors['reward_successor_joint_distribution']+=1
        if tv>worst_tv:
            worst_tv=tv;worst=dict(reason='reward_successor_joint_distribution',state=state,action=action,total_variation=tv,
                ground_atoms=len(p),candidate_atoms=len(q))
    if tuple(mapping.get(root) for root in model.roots)!=candidate.roots:
        errors['root_mapping']+=1
    structural=not errors
    query_results,lifted_policies={},{}
    for name,query in queries.items():
        solution=solutions[name]
        candidate_policy={state:solution.policy.get(compiled.state_to_cell[state]) for state in candidate.layers if candidate.terminal[state]=='ACTIVE'}
        lifted={state:candidate_policy.get(mapping.get(state)) for state in model.layers if model.terminal[state]=='ACTIVE'}
        lifted_policies[name]=lifted
        true_metrics=_metrics(model,lifted,query,work,'lifted_policy')
        predicted=_metrics(candidate,candidate_policy,query,work,'candidate_policy')
        loss,gap,valuegap,mismatches,missing=0.,0.,0.,0,0
        worst_state=None
        for state in model.layers:
            work['policy_state_comparisons']+=1
            actual=true_metrics[state];encoded=mapping.get(state)
            estimate=predicted.get(encoded)
            if actual is None or estimate is None:
                missing+=1;continue
            state_loss=reference.queries[name]['values'][state]-actual['value']
            if state_loss>loss: loss,worst_state=state_loss,state
            gap=max(gap,*(abs(actual[n]-estimate[n]) for n in METRICS))
            cell=compiled.state_to_cell.get(encoded)
            planned=solution.values.get(cell)
            if planned is None: missing+=1
            else: valuegap=max(valuegap,abs(planned-estimate['value']))
            if model.terminal[state]=='ACTIVE' and lifted[state]!=reference.queries[name]['policy'][state]: mismatches+=1
        valid=missing==0 and loss<=TOLERANCE and gap<=TOLERANCE and valuegap<=TOLERANCE
        query_results[name]=dict(valid=valid,root_metrics=[dict(root=state,name=closure.root_names[index],
            actual=true_metrics[state],predicted=predicted.get(mapping.get(state)),ground_optimal=reference.queries[name]['metrics'][state])
            for index,state in enumerate(model.roots)],maximum_value_loss=loss if not missing else None,maximum_metric_prediction_error=gap if not missing else None,
            maximum_plan_value_residual=valuegap if not missing else None,strict_max_lex_action_mismatches=mismatches,
            unavailable_state_metrics=missing,worst_value_state=worst_state)
    switches,violations=0,0
    for left,right in combinations(queries,2):
        a,b=reference.queries[left],reference.queries[right]
        for state in reference.actions:
            if a['policy'][state]!=b['policy'][state] and min(a['margins'][state],b['margins'][state])>TOLERANCE:
                switches+=1
                violations+=int(lifted_policies[left][state]!=a['policy'][state] or lifted_policies[right][state]!=b['policy'][state])
    work['strict_query_switch_checks']=switches
    return dict(valid=structural and all(q['valid'] for q in query_results.values()) and violations==0,
        structural_valid=structural,errors=dict(errors),mapped_states=len(mapping),ground_states=len(model.layers),
        maximum_joint_total_variation=worst_tv,worst_counterexample=worst if worst_tv>TOLERANCE else first,
        queries=query_results,strict_query_switches=dict(required=switches,violations=violations,preserved=violations==0),
        counts=dict(work),elapsed_seconds=perf_counter()-started,
        scope='All concrete states and reward-successor joint rows are audited. Missing encoded targets remain failures with unavailable policy metrics; no ground reference DP is repeated per arm.')

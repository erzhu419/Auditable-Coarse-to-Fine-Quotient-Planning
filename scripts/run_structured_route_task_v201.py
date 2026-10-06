"""One exact qualification of the declared twelve-context H4 route task."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import structured_route_task_v201 as core

OUTPUT = ROOT/'reports/structured_route_task_v201'
RUNTIME = ROOT/'reports/v201_runtime_tmp'
DELTA = Fraction(1, 20)
SOURCE_FILES = ('src/acfqp/science/structured_route_task_v201.py', 'scripts/run_structured_route_task_v201.py',
    'scripts/analyze_structured_route_task_v201.py', 'tests/test_structured_route_task_v201.py',
    'tests/test_structured_route_analysis_v201.py', 'specs/STRUCTURED_ROUTE_TASK_V201.md',
    'reports/v201_runtime_tmp/run_checks.py', 'reports/v201_runtime_tmp/run_stage.py')


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':'))+'\n')


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    return value


def scalar(value):
    return dict(exact=str(value), value=float(value))


def table_values(values):
    return [[state, h, exact_json(vector)] for (state, h), vector in sorted(values.items(), key=lambda item: (item[0][1], item[0][0]))]


def table_policy(policy):
    return [[state, h, action] for (state, h), action in sorted(policy.items(), key=lambda item: (item[0][1], item[0][0]))]


def margin(vectors, action, query, counts):
    selected = core.utility(vectors[action], query, counts)
    alternatives = [core.utility(vector, query, counts) for other, vector in vectors.items() if other != action]
    counts['margin_subtractions'] += 1
    return selected-max(alternatives)


def structural_evidence(graph, counts):
    distance, frontier = {'START': 0}, ['START']
    while frontier:
        following = []
        for state in frontier:
            for outcomes in graph[state].values():
                counts['reachability_row_reads'] += 1
                for probability, successor, _ in outcomes:
                    counts['reachability_outcome_reads'] += 1
                    if probability > 0 and successor not in distance:
                        distance[successor] = distance[state]+1; following.append(successor)
        frontier = following
    recovery = sum((p for p, nxt, _ in graph['DETOUR_ENTRY']['PASS'] if nxt == 'RECOVERY'), Fraction(0))
    safe_return = graph['RECOVERY']['RETURN'] == [(Fraction(1), 'ABORT', Fraction(0))]
    return dict(reachable_states=sorted(distance), earliest_success_step=distance.get('WON'),
        earliest_failure_step=distance.get('LOST'), recovery_mass=str(recovery), recovery_mass_float=float(recovery),
        safe_abort_from_recovery=safe_return)


def evaluate_case(case):
    work = defaultdict(Counter); graph = core.rows(case, work['model_rows'])
    structure = structural_evidence(graph, work['qualification'])
    recovery_mass = Fraction(structure['recovery_mass']); queries, plans, replayed = {}, {}, {}
    for query in core.QUERIES:
        plan = core.plan(graph, 4, query, work['joint_dp'])
        actual = core.evaluate_plan(graph, 4, plan['policy'], work['oracle_replay'])
        h2 = core.evaluate_controller(graph, 4, query, lookahead=2, counts=work['native_h2'])
        plans[query], replayed[query] = plan, actual
        action = actual['policy']['START', 4]; probability = recovery_mass if action == 'DETOUR' else Fraction(0)
        oracle = dict(vector=exact_json(actual['root']), components=[float(value) for value in actual['root']],
            utility=str(core.utility(actual['root'], query, work['qualification'])),
            utility_float=float(core.utility(actual['root'], query, work['qualification'])),
            root_action=action, recovery_action=plan['policy']['RECOVERY', 2],
            actual_recovery_action=actual['policy'].get(('RECOVERY', 2)),
            recovery_probability=str(probability), recovery_probability_float=float(probability),
            values=table_values(plan['values']), own_values=table_values(actual['values']),
            action_vectors=[[state, h, exact_json(vectors)] for (state, h), vectors in sorted(plan['action_vectors'].items(),
                key=lambda item: (item[0][1], item[0][0]))], policy=table_policy(plan['policy']), own_policy=table_policy(actual['policy']),
            root_action_vectors=exact_json(plan['action_vectors']['START', 4]))
        h2_action = h2['policy']['START', 4]
        control = dict(vector=exact_json(h2['root']), components=[float(value) for value in h2['root']],
            utility=str(core.utility(h2['root'], query, work['qualification'])),
            utility_float=float(core.utility(h2['root'], query, work['qualification'])),
            root_action=h2_action, recovery_action=h2['policy'].get(('RECOVERY', 2)),
            recovery_probability=str(recovery_mass if h2_action == 'DETOUR' else Fraction(0)),
            values=table_values(h2['values']), policy=table_policy(h2['policy']))
        queries[query] = dict(oracle=oracle, native_h2=control)
        work['serialization'].update(dp_value_records=len(plan['values']), dp_action_vector_records=len(plan['action_vectors']),
            full_policy_records=len(plan['policy']), own_policy_records=len(actual['policy']), h2_policy_records=len(h2['policy']))
    h1 = core.plan(graph, 1, 'reward', work['h1'])
    pure = core.pure_values(graph, h=4, counts=work['pure_policies'])
    hard = core.hard_constraint(pure, DELTA, work['hard_constraint'])
    mixture = tuple(sum((weight*pure[name][component] for name, weight in hard['mix']), Fraction(0)) for component in range(3))
    work['hard_constraint'].update(mixture_replay_products=3*len(hard['mix']), mixture_replay_additions=3*len(hard['mix']))
    packed_hard = dict(delta=str(DELTA), vector=exact_json(hard['vector']), components=[float(value) for value in hard['vector']],
        utility=str(hard['utility']), utility_float=float(hard['utility']),
        mix=[dict(policy=name, weight=str(weight)) for name, weight in hard['mix']],
        constituent_vectors={name: exact_json(vector) for name, vector in pure.items()},
        replayed_mixture_vector=exact_json(mixture), candidates=exact_json(hard['candidates']))
    root_margins = {query: margin(plan['action_vectors']['START', 4], plan['policy']['START', 4], query, work['qualification'])
        for query, plan in plans.items()}
    recovery_margins = {query: margin(plans[query]['action_vectors']['RECOVERY', 2], plans[query]['policy']['RECOVERY', 2],
        query, work['qualification']) for query in ('goal', 'risk')}
    risk_advantage = core.utility(replayed['risk']['root'], 'risk', work['qualification'])-core.utility(replayed['goal']['root'], 'risk', work['qualification'])
    planning_gains = {query: Fraction(queries[query]['oracle']['utility'])-Fraction(queries[query]['native_h2']['utility'])
        for query in ('goal', 'risk')}
    feasible_pure = max(core.utility(vector, 'goal', work['qualification']) for vector in pure.values() if vector[1] <= DELTA)
    hard_gain = hard['utility']-feasible_pure
    goal_action, risk_action = queries['goal']['oracle']['root_action'], queries['risk']['oracle']['root_action']
    delayed = (all(vector == (Fraction(0),)*3 for vector in h1['action_vectors']['START', 1].values())
        and structure['earliest_success_step'] == 3 and structure['earliest_failure_step'] == 2
        and recovery_mass > 0 and structure['safe_abort_from_recovery']
        and {'WON', 'LOST', 'ABORT'} <= set(structure['reachable_states']))
    objective = (all(value > 0 for value in root_margins.values()) and queries['reward']['oracle']['root_action'] == 'WAIT'
        and risk_action == 'DETOUR' and risk_advantage > Fraction(1, 100))
    followup = (queries['goal']['oracle']['recovery_action'] == 'RETRY' and queries['risk']['oracle']['recovery_action'] == 'RETURN'
        and all(value > Fraction(1, 100) for value in recovery_margins.values()))
    planning = all(queries[q]['native_h2']['root_action'] == 'WAIT' and planning_gains[q] > Fraction(1, 10) for q in ('goal', 'risk'))
    constrained = (replayed['goal']['root'][1] > DELTA and hard['vector'][1] == DELTA
        and len(hard['mix']) == 2 and all(weight > 0 for _, weight in hard['mix'])
        and sum((weight for _, weight in hard['mix']), Fraction(0)) == 1 and mixture == hard['vector']
        and hard_gain > Fraction(1, 100))
    metrics = dict(root_margins={q: scalar(value) for q, value in root_margins.items()},
        recovery_margins={q: scalar(value) for q, value in recovery_margins.items()},
        risk_advantage_over_goal=scalar(risk_advantage), planning_gains={q: scalar(value) for q, value in planning_gains.items()},
        best_feasible_pure_goal_utility=scalar(feasible_pure), hard_gain_over_best_feasible_pure=scalar(hard_gain),
        goal_to_risk_root_change=goal_action != risk_action,
        both_goal_risk_reach_recovery=Fraction(queries['goal']['oracle']['recovery_probability']) > 0
            and Fraction(queries['risk']['oracle']['recovery_probability']) > 0,
        conditions=dict(DELAYED_STRUCTURE=delayed, OBJECTIVE_CONFLICT=objective, FOLLOWUP_CONTROL=followup,
                        PLANNING_NEEDED=planning, HARD_CONSTRAINT=constrained))
    result = dict(**case, pure_policies={name: dict(vector=exact_json(vector), components=[float(value) for value in vector],
        utilities={q: str(core.utility(vector, q, work['qualification'])) for q in core.QUERIES}) for name, vector in pure.items()},
        queries=queries, h1_first_step_action_vectors=exact_json(h1['action_vectors']['START', 1]),
        structural_evidence=structure, hard_constraint=packed_hard, metrics=metrics)
    result['costs'] = {name: dict(counts) for name, counts in work.items()}
    return exact_json(graph), result


def summarize(results):
    changed = [row['id'] for row in results if row['metrics']['goal_to_risk_root_change']]
    recovery = [row['id'] for row in results if row['metrics']['both_goal_risk_reach_recovery']]
    conditions = {name: all(row['metrics']['conditions'][name] for row in results)
        for name in ('DELAYED_STRUCTURE', 'OBJECTIVE_CONFLICT', 'FOLLOWUP_CONTROL', 'PLANNING_NEEDED', 'HARD_CONSTRAINT')}
    conditions['OBJECTIVE_CONFLICT'] = conditions['OBJECTIVE_CONFLICT'] and len(changed) >= 4
    conditions['FOLLOWUP_CONTROL'] = conditions['FOLLOWUP_CONTROL'] and len(recovery) >= 4
    complete = len(results) == 12; qualified = complete and all(conditions.values())
    return dict(schema='acfqp.structured_route_task.v201.summary', complete=complete, contexts=len(results),
        conditions=conditions, qualification_pass=qualified, decision='TASK_QUALIFIED' if qualified else 'TASK_NOT_QUALIFIED',
        goal_to_risk_changed_contexts=changed, both_goal_risk_recovery_contexts=recovery,
        per_case=[dict(id=row['id'], root_actions={q: value['oracle']['root_action'] for q, value in row['queries'].items()},
            recovery_actions={q: value['oracle']['recovery_action'] for q, value in row['queries'].items()},
            recovery_probabilities={q: value['oracle']['recovery_probability'] for q, value in row['queries'].items()},
            hard_failure=row['hard_constraint']['vector'][1], hard_mix=row['hard_constraint']['mix'], **row['metrics']) for row in results])


def capture_code(output):
    manifests = []
    for relative in SOURCE_FILES:
        path = ROOT/relative; target = output/'source_code'/relative
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
        manifests.append(dict(path=relative))
    save(output/'source_manifest.json', manifests)


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.structured_route_task.v201.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), sampled_interactions=0,
        new_fits=0, teacher_loads=0, learned_updates=0, constructed_contexts=0, support_rows=0, support_outcomes=0,
        test_refs=[str(RUNTIME/'test_checks.json')])
    results, model_rows = [], []; current = None
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            constructed_contexts=record['constructed_contexts']))
        save(output/'run.json', record)
    try:
        capture_code(output); phase('protocol_frozen')
        roster_counts = Counter(); cases = core.roster(roster_counts)
        record['costs']['roster'] = dict(roster_counts); save(output/'cases.json', cases); phase('roster_frozen')
        record['costs']['contexts'] = []
        for case in cases:
            current = case['id']; tick = perf_counter(); graph, result = evaluate_case(case)
            result['seconds'] = perf_counter()-tick
            model_rows.append(dict(id=current, rows=graph)); results.append(result)
            record['constructed_contexts'] += 1
            record['support_rows'] += sum(len(actions) for actions in graph.values())
            record['support_outcomes'] += sum(len(outcomes) for actions in graph.values() for outcomes in actions.values())
            record['costs']['contexts'].append(dict(id=current, seconds=result['seconds'], counts=result['costs']))
            save(output/'model_rows.json', dict(records=model_rows)); save(output/'results.json', dict(records=results))
            save(output/'run.json', record); current = None
        phase('task_evaluated'); summary = summarize(results); save(output/'summary.json', summary)
        record['seconds'] = perf_counter()-begun; phase('complete')
        print(json.dumps({name: summary[name] for name in ('contexts', 'conditions', 'qualification_pass', 'decision')}, separators=(',', ':')), flush=True)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error), context=current))
        if hasattr(error, 'counts'):
            record['failure']['counts'] = error.counts
        save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()

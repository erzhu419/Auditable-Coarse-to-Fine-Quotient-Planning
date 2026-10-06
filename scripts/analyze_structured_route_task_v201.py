"""Independent closed-policy and convex-frontier audit of the delayed route task.

The V201 producer is not imported.  Four achievable full-policy vectors check
the recursive planner; local finite-horizon formulas check its continuation.
The constrained proof uses the upper convex frontier in (failure,utility),
then certifies the saved complete-policy mixture against that bound.
"""
import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'reports/structured_route_task_v201'
WEATHERS = ('normal', 'wet', 'blocked')
OPERATING = ('low', 'high')
RETRY_COSTS = (Fraction(17, 20), Fraction(19, 20))
DELTA = Fraction(1, 20)
QUERIES = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
PURE_NAMES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')
STATES = ('START', 'SHORT_ENTRY', 'DETOUR_ENTRY', 'WAIT_ENTRY', 'RECOVERY', 'DELIVERY', 'WON', 'LOST', 'ABORT')
ZERO = (Fraction(0), Fraction(0), Fraction(0))


def context(weather, operating, retry_cost):
    parameters = {
        'normal': (Fraction(9, 10), Fraction(17, 20), Fraction(1, 100), Fraction(7, 50), Fraction(1, 4)),
        'wet': (Fraction(17, 20), Fraction(39, 50), Fraction(1, 50), Fraction(1, 5), Fraction(3, 10)),
        'blocked': (Fraction(13, 20), Fraction(41, 50), Fraction(1, 100), Fraction(17, 100), Fraction(2, 5)),
    }[weather]
    short_cost, detour_cost = (Fraction(1, 10), Fraction(1, 20)) if operating == 'low' else (Fraction(3, 25), Fraction(7, 100))
    return dict(id=f'v201_{weather}_{operating}_r{retry_cost.numerator}_{retry_cost.denominator}',
        weather=weather, operating=operating, retry_cost=retry_cost,
        short_success=parameters[0], detour_success=parameters[1], detour_failure=parameters[2],
        recovery_mass=parameters[3], retry_success=parameters[4], short_cost=short_cost, detour_cost=detour_cost)


def roster():
    return [context(weather, operating, retry) for weather in WEATHERS for operating in OPERATING for retry in RETRY_COSTS]


def route_rows(case, work=None):
    work = Counter() if work is None else work
    result = {state: {} for state in STATES}
    one, zero = Fraction(1), Fraction(0)
    result['START'] = {name: [(one, name+'_ENTRY', zero)] for name in ('SHORT', 'DETOUR', 'WAIT')}
    result['SHORT_ENTRY']['PASS'] = [(case['short_success'], 'DELIVERY', -case['short_cost']),
        (1-case['short_success'], 'LOST', -case['short_cost'])]
    result['DETOUR_ENTRY']['PASS'] = [(case['detour_success'], 'DELIVERY', -case['detour_cost']),
        (case['detour_failure'], 'LOST', -case['detour_cost']), (case['recovery_mass'], 'RECOVERY', -case['detour_cost'])]
    result['WAIT_ENTRY']['WAIT'] = [(one, 'ABORT', zero)]
    result['DELIVERY']['FINISH'] = [(one, 'WON', zero)]
    result['RECOVERY'] = {'RETURN': [(one, 'ABORT', zero)], 'RETRY': [
        (case['retry_success'], 'DELIVERY', -case['retry_cost']),
        (1-case['retry_success'], 'LOST', -case['retry_cost'])]}
    work.update(reconstructed_contexts=1, declared_states=9, declared_action_rows=9, declared_support_outcomes=13)
    return result


def value(vector, query):
    reward, failure, success = QUERIES[query]
    return reward*vector[0]-failure*vector[1]+success*vector[2]


def full_policy_vectors(case, work=None):
    work = Counter() if work is None else work
    mass = case['recovery_mass']
    work['closed_full_policy_vectors'] += 4
    return dict(WAIT=ZERO,
        SHORT=(-case['short_cost'], 1-case['short_success'], case['short_success']),
        DETOUR_RETURN=(-case['detour_cost'], case['detour_failure'], case['detour_success']),
        DETOUR_RETRY=(-case['detour_cost']-mass*case['retry_cost'],
            case['detour_failure']+mass*(1-case['retry_success']), case['detour_success']+mass*case['retry_success']))


def select(vectors, query):
    return min(vectors, key=lambda action: (-value(vectors[action], query), action))


def finite_actions(case, state, remaining, query, work=None):
    """Local closed formulas preserve the delivery delay and joint policy."""
    work = Counter() if work is None else work
    work['finite_formula_calls'] += 1
    if remaining == 0 or state in ('WON', 'LOST', 'ABORT'):
        return {}
    if state == 'DELIVERY':
        return {'FINISH': (Fraction(0), Fraction(0), Fraction(1))}
    if state == 'WAIT_ENTRY':
        return {'WAIT': ZERO}
    if state == 'RECOVERY':
        retry = (-case['retry_cost'], 1-case['retry_success'], case['retry_success'] if remaining >= 2 else Fraction(0))
        return {'RETURN': ZERO, 'RETRY': retry}
    if state == 'SHORT_ENTRY':
        return {'PASS': (-case['short_cost'], 1-case['short_success'], case['short_success'] if remaining >= 2 else Fraction(0))}
    if state == 'DETOUR_ENTRY':
        tail = ZERO
        if remaining >= 2:
            choices = finite_actions(case, 'RECOVERY', remaining-1, query, work)
            tail = choices[select(choices, query)]
        vector = (-case['detour_cost'], case['detour_failure'], case['detour_success'] if remaining >= 2 else Fraction(0))
        return {'PASS': tuple(vector[k]+case['recovery_mass']*tail[k] for k in range(3))}
    if state == 'START':
        vectors = {}
        for action in ('DETOUR', 'SHORT', 'WAIT'):
            choices = finite_actions(case, action+'_ENTRY', remaining-1, query, work)
            vectors[action] = choices[select(choices, query)] if choices else ZERO
        return vectors
    raise ValueError('unknown declared route state')


def replay(rows, policy, remaining=4, work=None, start='START'):
    """Evaluate the supplied continuation, independent of local optimal values."""
    work = Counter() if work is None else work
    cache = {}
    def visit(state, steps):
        key = state, steps
        if key in cache:
            return cache[key]
        work['policy_replay_states'] += 1
        if state in ('WON', 'LOST', 'ABORT'):
            result = (Fraction(0), Fraction(state == 'LOST'), Fraction(state == 'WON'))
        elif steps == 0:
            result = ZERO
        else:
            action = policy(state, steps)
            total = [Fraction(0), Fraction(0), Fraction(0)]
            work['policy_replay_action_rows'] += 1
            for probability, child, reward in rows[state][action]:
                continuation = visit(child, steps-1)
                total[0] += probability*(reward+continuation[0])
                total[1] += probability*continuation[1]
                total[2] += probability*continuation[2]
                work['policy_replay_outcomes'] += 1
            result = tuple(total)
        cache[key] = result
        return result
    return visit(start, remaining)


def pure_policy(name, rows):
    def choose(state, steps):
        if state == 'START':
            return 'DETOUR' if name.startswith('DETOUR_') else name
        if state == 'RECOVERY':
            return 'RETRY' if name == 'DETOUR_RETRY' else 'RETURN'
        return next(iter(rows[state]))
    return choose


def constrained_frontier(vectors, delta=DELTA, work=None):
    """Upper hull bounds all feasible mixtures; intersect only adjacent edges."""
    work = Counter() if work is None else work
    by_failure = {}
    for name, vector in vectors.items():
        point = (vector[1], value(vector, 'goal'), name)
        previous = by_failure.get(point[0])
        if previous is None or point[1] > previous[1] or (point[1] == previous[1] and name < previous[2]):
            by_failure[point[0]] = point
    hull = []
    for point in sorted(by_failure.values()):
        while len(hull) >= 2:
            a, b = hull[-2:]
            cross = (b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])
            work['frontier_orientation_checks'] += 1
            if cross < 0:
                break
            hull.pop()
        hull.append(point)
    candidates = [(point[1], [(point[2], Fraction(1))]) for point in hull if point[0] <= delta]
    for left, right in zip(hull, hull[1:]):
        work['frontier_edge_checks'] += 1
        if left[0] < delta < right[0]:
            right_weight = (delta-left[0])/(right[0]-left[0])
            candidates.append((left[1]*(1-right_weight)+right[1]*right_weight,
                [(left[2], 1-right_weight), (right[2], right_weight)]))
    optimum, mixture = max(candidates, key=lambda candidate: candidate[0])
    vector = tuple(sum((weight*vectors[name][k] for name, weight in mixture), Fraction(0)) for k in range(3))
    work['frontier_achievable_candidates'] += len(candidates)
    return dict(utility=optimum, mix=mixture, vector=vector, hull=hull)


def certify_mixture(saved, vectors, bound):
    mixture = [(row['policy'], Fraction(row['weight'])) for row in saved['mix']]
    if not mixture or any(name not in vectors or weight <= 0 for name, weight in mixture):
        return False
    if sum((weight for _, weight in mixture), Fraction(0)) != 1:
        return False
    vector = tuple(sum((weight*vectors[name][k] for name, weight in mixture), Fraction(0)) for k in range(3))
    return (Fraction(saved['delta']) == DELTA and vector == tuple(Fraction(x) for x in saved['vector'])
        and vector[1] <= DELTA and Fraction(saved['utility']) == value(vector, 'goal') == bound['utility'])


def finite_vector(case, state, remaining, query, work=None):
    if state in ('WON', 'LOST', 'ABORT'):
        return Fraction(0), Fraction(state == 'LOST'), Fraction(state == 'WON')
    choices = finite_actions(case, state, remaining, query, work)
    return choices[select(choices, query)] if choices else ZERO


def graph_delay(rows):
    reached = {'START': 0}
    frontier = ['START']
    while frontier:
        state = frontier.pop(0)
        for outcomes in rows[state].values():
            for probability, child, _ in outcomes:
                if probability > 0 and child not in reached:
                    reached[child] = reached[state]+1
                    frontier.append(child)
    return reached


def reconstruct(case, work=None):
    work = Counter() if work is None else work
    rows = route_rows(case, work)
    vectors = full_policy_vectors(case, work)
    ground_pure = {name: replay(rows, pure_policy(name, rows), 4, work) for name in PURE_NAMES}
    oracle, native_h2 = {}, {}
    for query in QUERIES:
        full_policy = lambda state, h: select(finite_actions(case, state, h, query, work), query)
        h2_policy = lambda state, h: select(finite_actions(case, state, min(2, h), query, work), query)
        actions = finite_actions(case, 'START', 4, query, work)
        root = select(actions, query)
        recovery = finite_actions(case, 'RECOVERY', 2, query, work)
        recovery_action = select(recovery, query)
        ordered_utilities = sorted((value(vector, query) for vector in actions.values()), reverse=True)
        oracle[query] = dict(vector=replay(rows, full_policy, 4, work), root_action=root,
            recovery_action=recovery_action, root_action_vectors=actions,
            root_margin=ordered_utilities[0]-ordered_utilities[1],
            recovery_margin=abs(value(recovery['RETRY'], query)-value(recovery['RETURN'], query)))
        native_h2[query] = dict(vector=replay(rows, h2_policy, 4, work),
            root_action=h2_policy('START', 4))
    return dict(case=case, rows=rows, pure_vectors=vectors, ground_pure_vectors=ground_pure,
        oracle=oracle, native_h2=native_h2, h1=finite_actions(case, 'START', 1, 'reward', work),
        hard=constrained_frontier(vectors, DELTA, work), delay=graph_delay(rows))


def qualifications(rebuilt):
    delayed = all(set(record['h1'].values()) == {ZERO} and record['delay']['WON'] == 3
        and record['delay']['LOST'] == 2 and {'RECOVERY', 'ABORT'} <= set(record['delay']) for record in rebuilt)
    changed, both_detour = [], []
    conflict, followup, planning, hard = True, True, True, True
    for record in rebuilt:
        oracle, h2, case = record['oracle'], record['native_h2'], record['case']
        conflict &= (all(oracle[q]['root_margin'] > 0 for q in QUERIES)
            and oracle['reward']['root_action'] == 'WAIT' and oracle['risk']['root_action'] == 'DETOUR')
        risk_gap = value(oracle['risk']['vector'], 'risk')-value(oracle['goal']['vector'], 'risk')
        conflict &= risk_gap > Fraction(1, 100)
        if oracle['goal']['root_action'] != oracle['risk']['root_action']:
            changed.append(case['id'])
        if oracle['goal']['root_action'] == oracle['risk']['root_action'] == 'DETOUR' and case['recovery_mass'] > 0:
            both_detour.append(case['id'])
        followup &= (oracle['goal']['recovery_action'] == 'RETRY' and oracle['risk']['recovery_action'] == 'RETURN'
            and min(oracle[q]['recovery_margin'] for q in ('goal', 'risk')) > Fraction(1, 100))
        planning &= all(h2[q]['root_action'] == 'WAIT' and value(oracle[q]['vector'], q)-value(h2[q]['vector'], q) > Fraction(1, 10)
            for q in ('goal', 'risk'))
        mixture = record['hard']
        best_pure = max(value(vector, 'goal') for vector in record['pure_vectors'].values() if vector[1] <= DELTA)
        hard &= (oracle['goal']['vector'][1] > DELTA and mixture['vector'][1] == DELTA
            and len(mixture['mix']) == 2 and all(weight > 0 for _, weight in mixture['mix'])
            and mixture['utility']-best_pure > Fraction(1, 100))
    conditions = dict(DELAYED_STRUCTURE=bool(delayed), OBJECTIVE_CONFLICT=bool(conflict and len(changed) >= 4),
        FOLLOWUP_CONTROL=bool(followup and len(both_detour) >= 4), PLANNING_NEEDED=bool(planning), HARD_CONSTRAINT=bool(hard))
    passed = len(rebuilt) == 12 and all(conditions.values())
    return dict(conditions=conditions, qualification_pass=passed,
        decision='TASK_QUALIFIED' if passed else 'TASK_NOT_QUALIFIED')


def serialized_rows(rows):
    return {state: {action: [[str(p), child, str(reward)] for p, child, reward in outcomes]
        for action, outcomes in actions.items()} for state, actions in rows.items()}


def check_query_record(case, rows, saved, expected, query, work):
    oracle = saved['oracle']
    if (tuple(Fraction(x) for x in oracle['vector']) != expected['oracle'][query]['vector']
            or oracle['root_action'] != expected['oracle'][query]['root_action']
            or oracle['recovery_action'] != expected['oracle'][query]['recovery_action']):
        return False
    if Fraction(oracle['utility']) != value(expected['oracle'][query]['vector'], query):
        return False
    vectors = {action: tuple(Fraction(x) for x in vector) for action, vector in oracle['root_action_vectors'].items()}
    if vectors != expected['oracle'][query]['root_action_vectors']:
        return False
    values = {(state, h): tuple(Fraction(x) for x in vector) for state, h, vector in oracle['values']}
    actions = {(state, h): {action: tuple(Fraction(x) for x in vector) for action, vector in choices.items()}
        for state, h, choices in oracle['action_vectors']}
    policy = {(state, h): action for state, h, action in oracle['policy']}
    keys = {(state, h) for state in STATES for h in range(5)}
    if set(values) != keys or set(actions) != keys:
        return False
    for state, h in sorted(keys):
        choices = finite_actions(case, state, h, query, work)
        if values[state, h] != finite_vector(case, state, h, query, work) or actions[state, h] != choices:
            return False
        if choices and policy.get((state, h)) != select(choices, query):
            return False
    if replay(rows, lambda state, h: policy[state, h], 4, work) != expected['oracle'][query]['vector']:
        return False
    short = saved['native_h2']
    if tuple(Fraction(x) for x in short['vector']) != expected['native_h2'][query]['vector'] or short['root_action'] != 'WAIT':
        return False
    if Fraction(short['utility']) != value(expected['native_h2'][query]['vector'], query):
        return False
    h2_policy = {(state, h): action for state, h, action in short['policy']}
    if any(action != select(finite_actions(case, state, min(2, h), query, work), query)
            for (state, h), action in h2_policy.items()):
        return False
    return replay(rows, lambda state, h: h2_policy[state, h], 4, work) == expected['native_h2'][query]['vector']


def analyze(directory=OUTPUT):
    directory = Path(directory)
    begun = perf_counter()
    work, checks = Counter(), []
    result = dict(schema='acfqp.structured_route_task.v201.analysis', complete=False, valid=False, checks=checks)
    def read(name):
        raw = (directory/name).read_bytes()
        work['retained_files_read'] += 1
        work['retained_bytes_read'] += len(raw)
        return json.loads(raw)
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
    try:
        run, cases = read('run.json'), read('cases.json')
        declared, records, summary = read('model_rows.json')['records'], read('results.json')['records'], read('summary.json')
        source_manifest = read('source_manifest.json')
        definitions = roster()
        expected_cases = [{key: str(case[key]) if key == 'retry_cost' else case[key] for key in ('id', 'weather', 'operating', 'retry_cost')}
            for case in definitions]
        check('fixed_roster', cases == expected_cases and [row['id'] for row in records] == [case['id'] for case in definitions])
        check('frozen_source_manifest', len(source_manifest) == 8 and all(set(row) == {'path'} for row in source_manifest))
        phases = run['phase_history']
        check('frozen_execution_and_zero_learning', run['status'] == 'complete' and
            [phase['phase'] for phase in phases] == ['protocol_frozen', 'roster_frozen', 'task_evaluated', 'complete']
            and all(phase['constructed_contexts'] == 0 for phase in phases[:2])
            and all(run[name] == 0 for name in ('sampled_interactions', 'new_fits', 'teacher_loads', 'learned_updates'))
            and (run['constructed_contexts'], run['support_rows'], run['support_outcomes']) == (12, 108, 156)
            and [row['id'] for row in run['costs']['contexts']] == [case['id'] for case in definitions])
        rebuilt = []
        for case, model, saved in zip(definitions, declared, records):
            independent = reconstruct(case, work)
            rebuilt.append(independent)
            rows, vectors = independent['rows'], independent['pure_vectors']
            check('model_semantics:'+case['id'], model['id'] == case['id'] and model['rows'] == serialized_rows(rows))
            pure_valid = independent['ground_pure_vectors'] == vectors
            for name, vector in vectors.items():
                retained = saved['pure_policies'][name]
                pure_valid &= tuple(Fraction(x) for x in retained['vector']) == vector
                pure_valid &= {q: Fraction(x) for q, x in retained['utilities'].items()} == {q: value(vector, q) for q in QUERIES}
            check('joint_pure_policies:'+case['id'], pure_valid)
            closure = all(check_query_record(case, rows, saved['queries'][q], independent, q, work) for q in QUERIES)
            closure &= {action: tuple(Fraction(x) for x in vector) for action, vector in saved['h1_first_step_action_vectors'].items()} == independent['h1']
            check('full_h2_h1_continuations:'+case['id'], closure)
            constrained = saved['hard_constraint']
            mixture_valid = certify_mixture(constrained, vectors, independent['hard'])
            mixture_valid &= tuple(Fraction(x) for x in constrained['replayed_mixture_vector']) == tuple(Fraction(x) for x in constrained['vector'])
            mixture_valid &= {name: tuple(Fraction(x) for x in vector) for name, vector in constrained['constituent_vectors'].items()} == vectors
            check('achievable_hard_optimum:'+case['id'], mixture_valid)
        expected = qualifications(rebuilt)
        check('five_qualification_conditions', all(summary[key] == value for key, value in expected.items()))
        result.update(complete=True, valid=all(row['passed'] for row in checks), **expected)
    except Exception as error:
        result['failure'] = dict(type=type(error).__name__, message=str(error))
    result.update(costs=dict(work), seconds=perf_counter()-begun)
    (directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=OUTPUT)
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], checks=len(result['checks']))), flush=True)
    raise SystemExit(0 if result['valid'] and result['complete'] else 1)


if __name__ == '__main__':
    main()

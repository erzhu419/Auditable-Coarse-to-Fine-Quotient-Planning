"""Independent rational audit of the retained H4 reference-abstraction pilot."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'acfqp.reference_feasibility.v199'
OUTPUT = ROOT/'reports/controlled_predictive_reference_feasibility_v199'
WIDTHS = (Fraction(0), Fraction(1, 256), Fraction(1, 64), Fraction(1, 16), Fraction(1, 4), Fraction(1))
EPSILON = Fraction(1, 10**12)
CASE_NAMES = ('v69_h4_00', 'v69_h4_01')
INPUT_NAMES = ('v69_manifest.json', 'v69_h4_00_FULL.model.json', 'v69_h4_00_portable_inputs.json',
               'v69_h4_01_FULL.model.json', 'v69_h4_01_portable_inputs.json')
PHASES = ('protocol_frozen', 'inputs_retained', 'profiles_frozen', 'curve_complete', 'complete')
ZERO_COUNTS = ('new_environment_samples', 'new_physical_samples', 'new_model_fits',
               'new_parameter_solves', 'new_native_weight_updates', 'new_teacher_tapes')


def read_kernel(payload, work=None):
    work = Counter() if work is None else work
    work['kernel_payloads_decoded'] += 1
    cells = {state: (layer, status) for state, layer, status in payload['cells']}
    work['kernel_cells_decoded'] += len(cells)
    transitions, actions = {}, defaultdict(list)
    for state, action, outcomes in payload['rows']:
        transitions[state, action] = [(Fraction(p, q), target, Fraction(r, s))
                                      for p, q, target, r, s in outcomes]
        actions[state].append(action)
        work['kernel_action_rows_decoded'] += 1
        work['kernel_outcomes_decoded'] += len(outcomes)
    return dict(cells=cells, rows=transitions, roots=tuple(payload['roots']),
                actions={state: tuple(sorted(names)) for state, names in actions.items()})


def disjoint_union(payloads, work=None):
    work = Counter() if work is None else work
    cells, rows, actions, roots, origins = {}, {}, {}, [], {}
    for name, payload in payloads.items():
        kernel = read_kernel(payload, work)
        remap = {state: len(cells)+index for index, state in enumerate(sorted(kernel['cells']))}
        for state, cell in kernel['cells'].items():
            cells[remap[state]] = cell
            origins[remap[state]] = dict(case=name, native_state=state)
        for (state, action), outcomes in kernel['rows'].items():
            rows[remap[state], action] = [(probability, remap[target], reward)
                                          for probability, target, reward in outcomes]
        actions.update({remap[state]: names for state, names in kernel['actions'].items()})
        roots.extend(remap[state] for state in kernel['roots'])
        work['union_states_remapped'] += len(kernel['cells'])
        work['union_action_rows_remapped'] += len(kernel['rows'])
        work['union_outcomes_remapped'] += sum(len(row) for row in kernel['rows'].values())
    return dict(cells=cells, rows=rows, actions=actions, roots=tuple(roots), origins=origins)


def query_value(vector, query):
    return (Fraction(str(query['reward_weight']))*vector[0]
            - Fraction(str(query['failure_penalty']))*vector[1]
            + Fraction(str(query['goal_bonus']))*vector[2])


def terminal_vector(status):
    return (Fraction(0), Fraction(status == 'LOST'), Fraction(status == 'WON'))


def exact_plan(kernel, query, work=None, prefix='oracle_'):
    """Backward induction retains the joint reward/failure/success action profile."""
    work = Counter() if work is None else work
    coefficients = tuple(Fraction(str(query[name])) for name in ('reward_weight', 'failure_penalty', 'goal_bonus'))
    work[prefix+'dp_calls'] += 1
    vectors, action_vectors, policy = {}, {}, {}
    for state in sorted(kernel['cells'], key=lambda s: (kernel['cells'][s][0], s)):
        _, status = kernel['cells'][state]
        work[prefix+'dp_states'] += 1
        if status != 'ACTIVE':
            vectors[state] = terminal_vector(status)
            work[prefix+'dp_terminal_states'] += 1
            continue
        work[prefix+'dp_active_states'] += 1
        winner, winner_value = None, None
        for action in kernel['actions'][state]:
            totals = [Fraction(0), Fraction(0), Fraction(0)]
            outcomes = kernel['rows'][state, action]
            work[prefix+'dp_action_rows'] += 1
            work[prefix+'dp_outcome_terms'] += len(outcomes)
            work[prefix+'dp_reward_additions'] += len(outcomes)
            work[prefix+'dp_component_products'] += 3*len(outcomes)
            work[prefix+'dp_component_additions'] += 3*len(outcomes)
            for probability, target, reward in outcomes:
                child = vectors[target]
                totals[0] += probability*(reward+child[0])
                totals[1] += probability*child[1]
                totals[2] += probability*child[2]
            action_vectors[state, action] = tuple(totals)
            value = coefficients[0]*totals[0]-coefficients[1]*totals[1]+coefficients[2]*totals[2]
            work[prefix+'dp_utility_evaluations'] += 1
            if winner is not None:
                work[prefix+'dp_choice_comparisons'] += 1
            if winner is None or value > winner_value+EPSILON:
                winner, winner_value = action, value
        policy[state] = winner
        vectors[state] = action_vectors[state, winner]
    return dict(policy=policy, vectors=vectors, action_vectors=action_vectors)


def group_states(kernel, plans, width, work=None):
    """Use signed floor bins, while always retaining layer/status/legal mask."""
    work = Counter() if work is None else work
    state_keys = {}
    for state in sorted(kernel['cells']):
        layer, status = kernel['cells'][state]
        legal = kernel['actions'].get(state, ())
        coordinates = []
        if status == 'ACTIVE':
            for name in sorted(plans):
                plan = plans[name]
                for action in legal:
                    coordinates.extend(plan['action_vectors'][state, action])
            work['profile_coordinate_reads'] += len(coordinates)
            if width:
                work['profile_floor_divisions'] += len(coordinates)
        key = (layer, status, legal, tuple(coordinates) if not width else tuple(value//width for value in coordinates))
        state_keys[state] = key
        work['profile_partition_states'] += 1
    partition = {key: index for index, key in enumerate(sorted(set(state_keys.values())))}
    mapping = {state: partition[key] for state, key in state_keys.items()}
    members = defaultdict(list)
    for state, cell in mapping.items():
        members[cell].append(state)
    return mapping, dict(members)


def compile_average(kernel, mapping, members, work=None):
    """Uniform-member averaging of immediate reward and successor-cell mass."""
    work = Counter() if work is None else work
    cells, rows, actions = {}, {}, {}
    statistics = {}
    for cell, states in members.items():
        exemplar = states[0]
        cells[cell] = kernel['cells'][exemplar]
        work['compiled_cells'] += 1
        legal = kernel['actions'].get(exemplar, ())
        if legal:
            actions[cell] = legal
        for action in legal:
            reward, rewards = Fraction(0), []
            mass, member_laws = defaultdict(Fraction), []
            for state in states:
                outcomes = kernel['rows'][state, action]
                member_reward, member_law = Fraction(0), defaultdict(Fraction)
                work['compiled_member_action_rows'] += 1
                work['compiled_member_outcome_terms'] += len(outcomes)
                work['compiled_expected_reward_products'] += len(outcomes)
                work['compiled_expected_reward_additions'] += len(outcomes)
                work['compiled_successor_additions'] += 2*len(outcomes)
                for probability, target, immediate in outcomes:
                    member_reward += probability*immediate
                    member_law[mapping[target]] += probability
                    mass[mapping[target]] += probability
                rewards.append(member_reward)
                member_laws.append(dict(member_law))
                reward += member_reward
                work['compiled_reward_member_additions'] += 1
            reward /= len(states)
            work['compiled_reward_mean_divisions'] += 1
            average_law = {target: probability/len(states) for target, probability in mass.items()}
            work['compiled_successor_mean_divisions'] += len(mass)
            rows[cell, action] = [(probability, target, reward)
                                  for target, probability in sorted(average_law.items())]
            work['compiled_action_rows'] += 1
            work['compiled_outcomes'] += len(rows[cell, action])
            tvs = []
            for law in member_laws:
                coordinates = sorted(set(law)|set(average_law))
                work['compiled_member_tv_coordinates'] += len(coordinates)
                work['compiled_tv_evaluations'] += 1
                tvs.append(sum((abs(law.get(target, Fraction(0))-average_law.get(target, Fraction(0)))
                                for target in coordinates), Fraction(0))/2)
            statistics[cell, action] = (max(rewards)-min(rewards), max(tvs))
    return dict(cells=cells, rows=rows, actions=actions,
                roots=tuple(mapping[root] for root in kernel['roots']), statistics=statistics)


def policy_replay(kernel, policy, work=None):
    """Evaluate the lifted policy recursively on every original kernel state."""
    work = Counter() if work is None else work
    work['replay_dp_calls'] += 1
    vectors = {}
    for state in sorted(kernel['cells'], key=lambda s: (kernel['cells'][s][0], s)):
        _, status = kernel['cells'][state]
        work['replay_dp_states'] += 1
        if status != 'ACTIVE':
            vectors[state] = terminal_vector(status)
            work['replay_dp_terminal_states'] += 1
            continue
        work['replay_dp_active_states'] += 1
        totals = [Fraction(0), Fraction(0), Fraction(0)]
        outcomes = kernel['rows'][state, policy[state]]
        work['replay_dp_action_rows'] += 1
        work['replay_dp_outcome_terms'] += len(outcomes)
        work['replay_dp_reward_additions'] += len(outcomes)
        work['replay_dp_component_products'] += 3*len(outcomes)
        work['replay_dp_component_additions'] += 3*len(outcomes)
        for probability, target, reward in outcomes:
            child = vectors[target]
            totals[0] += probability*(reward+child[0])
            totals[1] += probability*child[1]
            totals[2] += probability*child[2]
        vectors[state] = tuple(totals)
    return vectors


def serialized_size(payload):
    return len((json.dumps(payload, separators=(',', ':'))+'\n').encode())


def model_payload(kernel):
    return dict(schema=SCHEMA+'.model', cells=[[state, *kernel['cells'][state]] for state in sorted(kernel['cells'])],
        rows=[[state, action, [[p.numerator, p.denominator, target, r.numerator, r.denominator]
                              for p, target, r in kernel['rows'][state, action]]]
              for state, action in sorted(kernel['rows'])], roots=list(kernel['roots']))


def reference_record(kernel, plans, width, work):
    mapping, members = group_states(kernel, plans, width, work)
    averaged = compile_average(kernel, mapping, members, work)
    max_reward_spread = max((entry[0] for entry in averaged['statistics'].values()), default=Fraction(0))
    max_tv = max((entry[1] for entry in averaged['statistics'].values()), default=Fraction(0))
    payload = model_payload(averaged)
    mapping_records, member_records = [[state, cell] for state, cell in sorted(mapping.items())], [[cell, states] for cell, states in sorted(members.items())]
    metrics = dict(cells=len(averaged['cells']), active_cells=sum(status == 'ACTIVE' for _, status in averaged['cells'].values()),
        action_rows=len(averaged['rows']), outcomes=sum(len(row) for row in averaged['rows'].values()),
        serialized_bytes=serialized_size(payload), mapping_bytes=serialized_size(mapping_records), membership_bytes=serialized_size(member_records),
        max_reward_spread=float(max_reward_spread), max_successor_tv=float(max_tv))
    return dict(width=[width.numerator, width.denominator], model=payload, mapping=mapping_records,
                members=member_records, metrics=metrics), averaged, mapping


def reconstruct(payloads, queries):
    """Construct each shared model once and evaluate its own closed policies."""
    work = Counter()
    kernel = disjoint_union(payloads, work)
    bindings = [dict(case=kernel['origins'][root]['case'], original_root=kernel['origins'][root]['native_state'], union_root=root)
                for root in kernel['roots']]
    plans = {name: exact_plan(kernel, queries[name], work) for name in sorted(queries)}
    active = [state for state in sorted(kernel['cells']) if kernel['cells'][state][1] == 'ACTIVE']
    ground = dict(cells=len(kernel['cells']), active_cells=len(active), action_rows=len(kernel['rows']),
                  outcomes=sum(len(row) for row in kernel['rows'].values()))
    models, width_choices, curve = [], [], []
    positive_control_valid = True
    for width in WIDTHS:
        record, averaged, mapping = reference_record(kernel, plans, width, work)
        models.append(record)
        query_results, choice_records = [], []
        for name in sorted(queries):
            query, oracle = queries[name], plans[name]
            abstract = exact_plan(averaged, query, work, 'abstract_')
            lifted = {state: abstract['policy'][mapping[state]] for state in active}
            work['policy_lifts'] += len(active)
            actual = policy_replay(kernel, lifted, work)
            regrets = [query_value(oracle['vectors'][state], query)-query_value(actual[state], query) for state in active]
            if width == 0:
                positive_control_valid &= all(abs(regret) <= Fraction(1, 10**10) for regret in regrets)
            max_regret = max([Fraction(0), *regrets])
            errors = [max([Fraction(0), *(abs(actual[state][component]-abstract['vectors'][mapping[state]][component]) for state in active)])
                      for component in range(3)]
            work['evaluation_active_regret_states'] += len(active)
            work['evaluation_component_error_coordinates'] += 3*len(active)
            roots = []
            for binding in bindings:
                state, cell = binding['union_root'], mapping[binding['union_root']]
                oracle_utility, actual_utility = query_value(oracle['vectors'][state], query), query_value(actual[state], query)
                roots.append(dict(case=binding['case'], union_root=state, abstract_root=cell, action=lifted.get(state),
                    oracle_action=oracle['policy'].get(state), predicted_rfs=[float(value) for value in abstract['vectors'][cell]],
                    actual_rfs=[float(value) for value in actual[state]], oracle_rfs=[float(value) for value in oracle['vectors'][state]],
                    oracle_utility=float(oracle_utility), actual_utility=float(actual_utility), regret=float(oracle_utility-actual_utility)))
                work['evaluation_root_records'] += 1
            query_results.append(dict(query=name, root_records=roots, max_active_regret=float(max_regret),
                                      max_active_prediction_error=[float(value) for value in errors]))
            choice_records.append(dict(query=name, policy=[[cell, action] for cell, action in sorted(abstract['policy'].items())], root_records=roots))
        max_regret = max(row['max_active_regret'] for row in query_results)
        max_errors = [max(row['max_active_prediction_error'][component] for row in query_results) for component in range(3)]
        qualifies = (2*record['metrics']['active_cells'] <= ground['active_cells'] and 2*record['metrics']['action_rows'] <= ground['action_rows']
                     and max_regret <= .01 and max(max_errors) <= .01)
        curve.append(dict(width=record['width'], model=record['metrics'], queries=query_results,
                          max_active_regret=max_regret, max_active_prediction_error=max_errors, qualifies=qualifies))
        width_choices.append(dict(width=record['width'], queries=choice_records))
    qualifying = [row['width'] for row in curve if row['qualifies']]
    summary = dict(schema=SCHEMA+'.summary', complete=True, ground=ground, curve=curve,
        positive_control_valid=positive_control_valid and max(curve[0]['max_active_prediction_error']) <= 1e-10,
        routing=dict(qualifying_widths=qualifying, next_step='learn_reference_distinctions' if qualifying else 'reassess_reference_family'))
    return dict(compiled=dict(models=models, root_bindings=bindings), choices=dict(width_records=width_choices), summary=summary, costs=dict(work))


def same(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(same(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(same(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, float):
        return type(actual) in (int, float) and abs(actual-expected) <= 1e-10*(1+abs(expected))
    return type(actual) is type(expected) and actual == expected


def analyze(directory):
    begun = perf_counter()
    directory = Path(directory)
    checks, io = [], Counter()

    def read(relative):
        raw = (directory/relative).read_bytes()
        io.update(json_read_operations=1, json_bytes_read=len(raw))
        return json.loads(raw)

    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))

    run, manifest = read('run.json'), read('input_manifest.json')
    records = manifest['records']
    check('five_fixed_original_inputs_in_protocol_order', manifest['schema'] == SCHEMA+'.inputs' and
          [row['saved'] for row in records] == ['inputs/'+name for name in INPUT_NAMES])
    inherited = {}
    for row in records:
        saved = (directory/row['saved']).read_bytes()
        original = Path(row['original']).read_bytes()
        io.update(retained_input_byte_comparisons=1, comparison_bytes_read=len(saved)+len(original),
                  json_read_operations=1, json_bytes_read=len(saved))
        check('retained_input:'+row['saved'], saved == original and len(saved) == row['bytes'])
        inherited[Path(row['saved']).name] = json.loads(saved)
    previous = inherited['v69_manifest.json']
    portable = [inherited[name+'_portable_inputs.json'] for name in CASE_NAMES]
    payloads = {name: inherited[name+'_FULL.model.json'] for name in CASE_NAMES}
    check('complete_retained_V69_and_same_fourteen_original_queries', previous['status'] == 'complete' and
          len(portable[0]['queries']) == 14 and portable[0]['queries'] == portable[1]['queries'])
    check('two_retained_FULL_H4_roots_and_portable_root_bindings', all(payload['schema'] == 'acfqp-compositional-contract-v69' and
          payload['variant'] == 'FULL' and len(payload['roots']) == 1 and
          next(layer for state, layer, _ in payload['cells'] if state == payload['roots'][0]) == 4 and
          any(row['horizon'] == 4 and row['expected_full'] == payload['roots'][0] for row in observer['observations'])
          for payload, observer in zip(payloads.values(), portable)))
    expected = reconstruct(payloads, portable[0]['queries'])
    compiled, choices, summary = read('compiled.json'), read('choices.json'), read('summary.json')
    check('six_joint_profile_closed_rational_models_mappings_and_memberships', same(compiled, expected['compiled']))
    check('fourteen_own_quotient_policies_and_both_root_joint_vectors_per_width', same(choices, expected['choices']))
    check('all_ACTIVE_replay_regrets_three_component_errors_curve_and_routing', same(summary, expected['summary']))
    check('exact_width_positive_control_values_and_component_predictions', expected['summary']['positive_control_valid'] and summary['positive_control_valid'])
    for saved_record, rebuilt_record in zip(compiled['models'], expected['compiled']['models']):
        width = str(Fraction(*rebuilt_record['width']))
        check('native_model_and_membership_exact:'+width, saved_record['model'] == rebuilt_record['model'] and
              saved_record['mapping'] == rebuilt_record['mapping'] and saved_record['members'] == rebuilt_record['members'])
    costs = dict(expected['costs'], **{name: 0 for name in ZERO_COUNTS},
        input_files_read=5, input_files_retained=5, input_bytes_read=sum(row['bytes'] for row in records),
        input_bytes_retained=sum(row['bytes'] for row in records))
    check('all_retained_kernel_profile_compile_planning_replay_and_input_work', run['costs'] == costs)
    check('fixed_protocol_and_original_query_profiles_precede_six_model_curve',
          [(row['phase'], row['input_reads']) for row in run['phases']] ==
          [(phase, 0 if index == 0 else 5) for index, phase in enumerate(PHASES)])
    check('complete_without_new_physics_fits_solves_or_teacher_tapes', run['schema'] == SCHEMA+'.run' and
          run['status'] == 'complete' and run['complete'] and all(run['costs'][key] == 0 for key in ZERO_COUNTS))
    valid = all(row['passed'] for row in checks)
    complete = valid and expected['summary']['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete,
        checks=checks, total_checks=len(checks), passed_checks=sum(row['passed'] for row in checks), summary=expected['summary'],
        costs=dict(independent_numerical_counts=expected['costs'], reconstructed_original_counts=costs,
                   independent_input_counts=dict(io), new_environment_samples=0, new_physical_samples=0,
                   new_model_fits=0, new_parameter_solves=0, new_native_weight_updates=0, new_teacher_tapes=0,
                   inherited_input_refs=[row['original'] for row in records], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=OUTPUT)
    directory = parser.parse_args().directory
    result = analyze(directory)
    (directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'])))


if __name__ == '__main__':
    main()
